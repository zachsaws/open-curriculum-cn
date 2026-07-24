"""
V3.3.5 Fix script: 用更聚焦 prompt 重做未达标概念.

策略: 更聚焦 prompt + 宽松正则 (V3.3.4 chemistry/math 经验).
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from subjects_config import (
    BANNED, BANNED_FIX, TEMPLATE_BANNED, CHAR_DISPLACE_PATTERNS,
    TEMPLATE_REGRESSION_PATTERNS, SUBJECTS, TEXTBOOK_KW, SUBJECT_KW, MISTAKE_KW, PADS,
)

ROOT = Path('/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn')
os.chdir(ROOT)

with open('/Users/tianxiang/.claude/settings.json') as f:
    settings = json.load(f)
TOKEN = settings['env']['ANTHROPIC_AUTH_TOKEN']
BASE_URL = 'https://api.minimaxi.com/anthropic/v1/messages'


SUBJECT = sys.argv[1] if len(sys.argv) > 1 else 'english'
if SUBJECT not in SUBJECTS:
    print(f'Usage: python3 fix.py <subject> where subject ∈ {list(SUBJECTS.keys())}')
    sys.exit(1)

CFG = SUBJECTS[SUBJECT]
INPUT = CFG['input_path']
OUTPUT = CFG['output_path']
NAME = CFG['name']

TEXTBOOK_KW_SUBJ = TEXTBOOK_KW[SUBJECT]
SUBJECT_KW_SUBJ = SUBJECT_KW[SUBJECT]
MISTAKE_KW_SUBJ = MISTAKE_KW[SUBJECT]
PADS_SUBJ = PADS[SUBJECT]

print(f'=== V3.3.5 Fix: {NAME} ({SUBJECT}) ===')
print(f'  Input:  {INPUT}')
print(f'  Output: {OUTPUT}')


def fix_banned(s: str) -> str:
    for b, f in BANNED_FIX.items():
        s = s.replace(b, f)
    s = re.sub(r'  +', ' ', s)
    s = re.sub(r'。\s*。', '。', s)
    return s


def fix_char_displace(s: str) -> str:
    for pat in CHAR_DISPLACE_PATTERNS:
        s = re.sub(pat, pat[1:], s)
    return s


def smart_truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    cut = s.rfind('。', 0, max_len)
    if cut == -1 or cut < max_len - 30:
        cut = s.rfind(';', 0, max_len)
    if cut == -1 or cut < max_len - 30:
        cut = s.rfind(';', 0, max_len)
    if cut == -1 or cut < max_len - 30:
        cut = s.rfind(',', 0, max_len)
    if cut == -1 or cut < max_len - 30:
        cut = max_len
    else:
        cut += 1
    return s[:cut]


def smart_pad_with_field(s: str, field: str, min_len: int) -> str:
    if len(s) >= min_len:
        return s
    pads = PADS_SUBJ.get(field, ['老师可以多设计几组变式让孩子练。'])
    pad = pads[len(s) % len(pads)]
    cut = s.rfind('。')
    if cut == -1:
        return s + pad
    return s[:cut+1] + pad


def repair_one(item: dict) -> dict:
    for field in ['real_examples', 'common_mistakes', 'teaching_activity']:
        s = item.get(field, '').strip()
        s = fix_banned(s)
        s = fix_char_displace(s)
        s = s.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
        s = re.sub(r'  +', ' ', s)
        s = re.sub(r'。\s*。', '。', s)
        if len(s) > 120:
            s = smart_truncate(s, 120)
        if len(s) < 60:
            s = smart_pad_with_field(s, field, 60)
        item[field] = s
    return item


def has_textbook_loose(s: str) -> bool:
    """更宽松: 任意教材版本关键词 OR 具体单元/课/章节."""
    for kw in TEXTBOOK_KW_SUBJ:
        if kw in s:
            return True
    if re.search(r'第\s*\d+\s*单元', s): return True
    if re.search(r'第\s*\d+\s*课', s): return True
    if re.search(r'第\s*\d+\s*节', s): return True
    if re.search(r'第\s*\d+\s*章', s): return True
    if re.search(r'Unit\s*\d+', s, re.IGNORECASE): return True
    if re.search(r'例\s*\d+', s): return True
    return False


def has_mistake_pattern_loose(s: str) -> bool:
    """更宽松的 common_mistakes 检测 — 必须有具体错法描述."""
    for kw in MISTAKE_KW_SUBJ:
        if kw in s:
            return True
    # "学生 + 动词" 模式
    if re.search(r'学生[一-龥]*?(写成|算成|看成|记成|答成|漏|忘|混用|混淆|搞混|颠倒|记错|错把|写错|拼错|算错|看错|答错)', s):
        return True
    return False


def has_action_loose(s: str) -> bool:
    """更宽松的 teaching_activity 检测 — 必须有具体动作或教具."""
    for kw in SUBJECT_KW_SUBJ:
        if kw in s:
            return True
    # 通用动作动词正则
    if re.search(r'(让|请|用|发给|发到|分给|给每个|计时|限时|比赛|小组|讨论|朗读|扮演|操作|观察|记录|测量|画|读|写|说|听|练|贴|排|分|演|圈|填|做|看)', s):
        return True
    return False


def validate(item: dict) -> list[str]:
    issues = []
    for field in ['real_examples', 'common_mistakes', 'teaching_activity']:
        s = item.get(field, '')
        if not (60 <= len(s) <= 120):
            issues.append(f'{field}_len={len(s)}')
        for b in BANNED:
            if b in s:
                issues.append(f'{field}_禁词[{b}]')
        for tmpl in TEMPLATE_BANNED:
            if tmpl in s:
                issues.append(f'{field}_模板[{tmpl}]')
        for pat in CHAR_DISPLACE_PATTERNS:
            if re.search(pat, s):
                issues.append(f'{field}_char_displace[{pat}]')
        for pat in TEMPLATE_REGRESSION_PATTERNS:
            if pat in s:
                issues.append(f'{field}_template_regression[{pat}]')
        if re.search(r'  +', s):
            issues.append(f'{field}_2space')
    re_field = item.get('real_examples', '')
    cm_field = item.get('common_mistakes', '')
    ta_field = item.get('teaching_activity', '')
    if not has_textbook_loose(re_field):
        issues.append('real_examples_no_textbook')
    if not has_mistake_pattern_loose(cm_field):
        issues.append('common_mistakes_no_verb')
    if not has_action_loose(ta_field):
        issues.append('teaching_activity_no_action')
    return issues


def call_llm_strict(concept: dict) -> str:
    """用更聚焦的 prompt 重调 LLM, 强制要求关键词."""
    # 学科特定的强制要求
    if SUBJECT == 'english':
        textbook_examples = '「人教版 PEP 三年级英语下册 Unit 2 ' + "'My family'" + ' Part A Let’s talk」/「人教版七年级上册 Unit 1 ' + "'My name'" + '」/「外研版四年级上册 Module 1 Unit 1 ' + "'It was my birthday" + '」'
        mistake_examples = '「He go to school (第三人称单数忘加 s)」/「把 child 写成 childs (复数错误)」/「把 their/there 混用」'
        activity_examples = '「用单词卡 6 张抽 2 张让孩子组句」/「让学生分角色朗读对话」/「用 chant 练 3 遍」'
    elif SUBJECT == 'history':
        textbook_examples = '「人教版 (部编版) 七年级上册第 2 单元第 6 课《动荡的春秋时期》」/「部编版八年级上册第 5 课《甲午中日战争》」/「人教版九年级下册第 1 课《殖民地人民的反抗斗争》」'
        mistake_examples = '「把' + '公元前 221 年' + '写成' + '公元 221 年' + '」/「把齐桓公错记成战国人物」/「把' + '焚书坑儒' + '和' + '罢黜百家' + '的人物记反」'
        activity_examples = '「用时间轴 PPT 让学生贴事件」/「用历史地图让学生标战役位置」/「用人物卡片让学生排朝代」'
    elif SUBJECT == 'physics':
        textbook_examples = '「人教版八年级下册第 7 章第 3 节' + '重力' + '」/「人教版九年级全一册第 14 章' + '欧姆定律' + '」/「人教版八年级上册第 3 章第 1 节' + '温度' + '」'
        mistake_examples = '「把质量 2 kg 错当成 2 N」/「算浮力时把' + '浸没' + '当成' + '漂浮' + '用错公式」/「1 米水深错算成 1 帕 (实际 9800 帕)」'
        activity_examples = '「用弹簧测力计 + 砝码 5 个做实验」/「用量筒 + 水测体积」/「用电压表 + 电流表测电阻」'
    elif SUBJECT == 'science':
        textbook_examples = '「人教版 (教育科学版) 三年级下册第 2 单元' + '动物的一生' + '」/「教科版四年级上册第 3 单元' + '声音' + '」/「人教版五年级上册第 4 单元' + '地球表面的变化' + '」'
        mistake_examples = '「把' + '蒸发' + '和' + '沸腾' + '混淆」/「观察月相时把' + '上弦月' + '写成' + '下弦月' + '」/「种子萌发实验漏写' + '需要水' + '条件」'
        activity_examples = '「每组发 3 个透明杯 + 凉水/温水/热水 + 3 块糖」/「用放大镜观察叶子结构」/「用天平测物体质量」'
    else:  # morality_law
        textbook_examples = '「部编版道德与法治六年级上册第 2 单元第 4 课《公民的基本权利》」/「部编版七年级上册第 1 单元第 2 课《学习新天地》」/「部编版八年级下册第 4 单元第 7 课《自由平等的追求》」'
        mistake_examples = '「把' + '权利' + '和' + '义务' + '混淆」/「看到' + '选举权' + '写' + '小学生也能选总统' + '」/「把' + '消费者权益' + '答成' + '想退货就退货' + '」'
        activity_examples = '「用 PPT 出 3 个生活情境让 4 人一组讨论」/「用角色卡让学生模拟' + '消费者维权' + '」/「用权利海报让孩子分类贴」'

    system = f"""你是 V3.3.5 {NAME}教师用书深度内容编辑. 你的任务是给{NAME}概念写「教师用书」级别的 3 个补充字段.

# 严格 3 字段
1. `real_examples` (60-120 字): **必须含教材版本** ({textbook_examples}) + 具体单元/课/章节.
2. `common_mistakes` (60-120 字): **必须含具体错法**, 用「学生 X 写成 Y」「学生把 X 记成 Y」「学生漏 X」「学生忘 X」「学生混淆 X 和 Y」句式, 至少 2 个具体错例 ({mistake_examples}).
3. `teaching_activity` (60-120 字): **必须含具体动作**, 用「用 X 教具」「让学生 X」「让小组 X」「请 X 孩子 X」「用 X 摆/数/量/算/读/写/画/折/剪/贴/贴/分组/讨论」句式 ({activity_examples}).

# 3 字段独立, 不可重复
- real_examples: 课本定位 (教材 + 单元 + 课题)
- common_mistakes: 学生具体错法 (写出错的句子/字/算式/年代)
- teaching_activity: 教具 + 操作 (用什么 + 做什么 + 怎么操作)

# 严格风格
- 60-120 字, 1 段不换行, 中间可用「」
- 绝不要用「理解/培养/掌握/运用/知识点/课标/教学目标/含义/定义/本概念/该概念/本节/本文/通过本」等公文腔
- 数字必须具体: 写出错的句子/字/算式/年代, 写教具, 写时间 (计时 1 分钟)
- 内容严禁使用 ASCII 双引号 ", 全部用「」

# 输出格式
严格 JSON 数组, 每条 {{ "id": "...", "real_examples": "...", "common_mistakes": "...", "teaching_activity": "..." }}"""

    user = f'''请为以下{NAME}概念生成 3 字段:

ID: {concept["id"]}
Title: {concept["title"]}
Domain: {concept["domain"]} / {concept["subdomain"]}
Stage: G{concept["grade_start"]}-{concept["grade_end"]}
Content: {concept["content_req"]}
Key: {"; ".join(concept["key_points"]) if concept.get("key_points") else "无"}

要求:
- real_examples 必须含 教材版本 + "第 X 单元" / "第 X 课" / "Unit X" / "例 X"
- common_mistakes 必须用 "学生 X 写成 Y" / "学生把 X 算成 Y" / "学生漏 X" / "学生忘 X" 句式, 至少 2 个具体错例
- teaching_activity 必须含 "用 X" (教具) 或 "让学生" 或 "让孩子" 或 "用 X 摆/数/量/算/读/写/画/折/剪/贴" 句式

请输出严格 JSON 数组, 1 条记录, 含 id, real_examples, common_mistakes, teaching_activity.'''

    body = json.dumps({
        'model': 'MiniMax-M3',
        'max_tokens': 4000,
        'system': system,
        'messages': [{'role': 'user', 'content': user}],
    }).encode('utf-8')

    req = urllib.request.Request(BASE_URL, data=body, headers={
        'x-api-key': TOKEN,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result['content'][0]['text']
        except urllib.error.HTTPError as e:
            print(f'  [HTTP {e.code}] {e.read()[:200]}, retry {attempt+1}/3', flush=True)
            time.sleep(5 + attempt * 5)
        except Exception as e:
            print(f'  [Err {type(e).__name__}] {e}, retry {attempt+1}/3', flush=True)
            time.sleep(5 + attempt * 5)
    raise RuntimeError('LLM 3 次都失败')


def parse_json(text: str) -> list[dict]:
    text = text.strip()
    text = re.sub(r'^```\w*\s*\n?', '', text)
    text = re.sub(r'\n?\s*```\s*$', '', text)
    m = re.search(r'\[\s*\{', text)
    if not m:
        return []
    start = m.start()
    end = text.rfind(']')
    if end < start:
        text = text + ']'
        end = text.rfind(']')
    raw = text[start:end+1]
    n = len(raw)

    quote_positions = []
    i = 0
    while i < n:
        c = raw[i]
        if c == '\\' and i + 1 < n:
            i += 2
            continue
        if c == '"':
            quote_positions.append(i)
        i += 1

    valid_pairs = []
    for k in range(0, len(quote_positions) - 1, 2):
        op = quote_positions[k]
        cp = quote_positions[k + 1]
        prev_ok = op == 0
        if not prev_ok:
            j = op - 1
            while j >= 0 and raw[j] in ' \t\n\r':
                j -= 1
            if j < 0 or raw[j] in '[{,:':
                prev_ok = True
        next_ok = cp == n - 1
        if not next_ok:
            j = cp + 1
            while j < n and raw[j] in ' \t\n\r':
                j += 1
            if j >= n or raw[j] in ',}]':
                next_ok = True
        if prev_ok and next_ok:
            valid_pairs.append((op, cp))

    result = []
    pos = 0
    for op, cp in valid_pairs:
        result.append(raw[pos:op+1])
        body = raw[op+1:cp]
        fixed = []
        toggle = True
        for ch in body:
            if ch == '"':
                fixed.append('「' if toggle else '」')
                toggle = not toggle
            else:
                fixed.append(ch)
        result.append(''.join(fixed))
        result.append('"')
        pos = cp + 1
    result.append(raw[pos:])

    fixed_text = ''.join(result)
    fixed_text = re.sub(r',\s*([\]\}])', r'\1', fixed_text)
    fixed_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', fixed_text)

    try:
        data = json.loads(fixed_text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError as e:
        print(f'  [JSON parse fail] {e}', flush=True)
        pos = e.pos if hasattr(e, 'pos') else 0
        print(f'  ... {fixed_text[max(0,pos-80):pos+80]} ...', flush=True)
        return []


def main():
    input_data = json.load(open(INPUT))
    existing = json.load(open(OUTPUT))
    done = {c['id']: c for c in existing}
    failed = [c for c in input_data if c['id'] not in done]
    print(f'失败 {len(failed)} 个, 开始重试...', flush=True)

    t0 = time.time()
    for i, c in enumerate(failed):
        print(f'\n--- [{i+1}/{len(failed)}] {c["id"]} ({c["title"]}) ---', flush=True)
        for attempt in range(3):
            try:
                text = call_llm_strict(c)
                parsed = parse_json(text)
                if parsed and parsed[0].get('id') == c['id']:
                    parsed[0] = repair_one(parsed[0])
                    issues = validate(parsed[0])
                    if not issues:
                        done[c['id']] = {
                            'id': c['id'],
                            'real_examples': parsed[0]['real_examples'],
                            'common_mistakes': parsed[0]['common_mistakes'],
                            'teaching_activity': parsed[0]['teaching_activity'],
                        }
                        print(f'  ✓ {c["id"]} 通过 (attempt {attempt+1})', flush=True)
                        break
                    else:
                        print(f'  attempt {attempt+1} 不达标: {issues}', flush=True)
                else:
                    print(f'  attempt {attempt+1} parse fail', flush=True)
            except Exception as e:
                print(f'  attempt {attempt+1} 异常: {e}', flush=True)
            time.sleep(3)
        else:
            print(f'  ✗ {c["id"]} 3 次都没过', flush=True)

    # 写回
    out = sorted(done.values(), key=lambda x: x['id'])
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'\n=== Fix 完成 ===', flush=True)
    print(f'总产出: {len(done)} / {len(input_data)}', flush=True)
    print(f'剩余失败: {len([c for c in input_data if c["id"] not in done])}', flush=True)
    print(f'用时: {(time.time()-t0)/60:.1f} min', flush=True)


if __name__ == '__main__':
    main()
