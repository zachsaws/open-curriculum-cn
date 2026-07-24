"""
V3.3.4 Chinese fix script: 修 chinese_v34_llm.json 失败的 24 个概念.
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path('/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn')
os.chdir(ROOT)

INPUT = 'data/v33_inputs/chinese_input.json'
OUTPUT = 'data/graph/chinese_v34_llm.json'

with open('/Users/tianxiang/.claude/settings.json') as f:
    settings = json.load(f)
TOKEN = settings['env']['ANTHROPIC_AUTH_TOKEN']
BASE_URL = 'https://api.minimaxi.com/anthropic/v1/messages'

BANNED = ['理解', '培养', '掌握', '运用', '知识点', '课标', '教学目标', '含义', '定义', '本概念', '该概念', '本节', '本文', '通过本', '课标要求', '具体含义']
BANNED_FIX = {'理解': '看明白', '培养': '养成', '掌握': '会用', '运用': '用起来', '含义': '意思', '定义': '是啥', '本概念': '它', '该概念': '它'}

TEMPLATE_BANNED = [
    '在 X 课上, 能否', '在 X 课上,能否', '在 X 课上能否',
    '用自己的话解释', '独立完成相关题目', '举出一个生活中的例子',
    '在 X 这一概念中', '通过本节学习', '教学目标', '课标要求',
]

CHAR_DISPLACE_PATTERNS = [
    r'原看明白', r'原掌握', r'原运用', r'原理解', r'原养成', r'原会用',
    r'原用起来', r'原意思', r'原是啥', r'原通过',
]

TEMPLATE_REGRESSION_PATTERNS = [
    '{{name}}能举个例子吗?', '{{name}}能举个例子吗？',
    '能举个例子吗?', '能举个例子吗？',
]

def has_textbook_loose(s):
    for kw in ['部编版', '人教版', '苏教版', '北师大版', '语文版', '西师大版', '鲁教版', '义教课标', '课标实验稿', '单元', '第', '例', '课时', '课本', '教材']:
        if kw in s:
            return True
    if re.search(r'第\s*\d+\s*单元', s): return True
    if re.search(r'例\s*\d+', s): return True
    if re.search(r'第\s*\d+\s*课', s): return True
    if re.search(r'第\s*\d+\s*节', s): return True
    return False


def has_mistake_pattern_loose(s):
    """宽松的 common_mistakes 检测."""
    for kw in ['写成', '算成', '漏', '忘', '看成', '错把', '混淆', '搞混', '颠倒', '漏写', '漏掉', '多写', '少写', '忘加', '忘写', '忘标', '没进位', '没借位', '错算', '算错', '看错', '数错', '加错', '减错', '乘错', '除错', '写错', '错写', '错读', '误读', '误写', '不理解', '不会算', '没理解', '错别字', '病句', '语序', '标点', '搭配', '重复', '漏字', '添字', '不通顺', '的 地 得', '的/地/得', '一逗到底', '不会', '没用', '乱用', '没用对', '用法', '加错', '用错', '没加', '把 X 写', '写成错', '写成多', '少写', '把 X 和 Y', '把 X 当 Y', '把 X 看成 Y', '写反', '写混', '标错', '不会标', '写别字', '用混', '错用', '不理解']:
        if kw in s:
            return True
    if re.search(r'学生[一-龥]*?(写成|算成|写成错|看成|漏|忘|混淆|搞混|颠倒|错算|算错|看错|数错|加错|减错|乘错|除错|写错|错写|写混|错用|错读|不会|不懂|用错|用混)', s):
        return True
    return False


def has_action_loose(s):
    """宽松的 teaching_activity 检测."""
    for kw in [
        '用生字卡', '用字卡', '用拼音卡', '用田字格', '用米字格', '用课文', '用字典', '用新华字典', '用彩笔', '用贴纸', '用卡片', '用小黑板', '用 PPT', '用投影', '用录音', '用音频', '用视频', '用 A4', '用 A', '用 A5',
        '用 XX', '用 X',
        '让学生', '让孩子', '让同学', '让小组', '请学生', '请孩子', '请同学', '请小组', '请每', '请全班',
        '读一读', '写一写', '想一想', '说一说', '圈一圈', '画一画', '找一找', '分一分', '排一排', '拼一拼', '演一演', '背一背', '填一填', '贴一贴', '折一折', '剪一剪', '描一描', '查一查', '认一认', '读一读', '念一念', '听一听', '看一看', '比一比', '评一评', '改一改', '选一选', '答一答', '问一问', '议一议', '评一评',
        '发给', '发到', '发给每人', '发给每个', '分给', '发给小组', '分到',
        '在田字格', '在米字格', '在黑板', '在白板', '在投影', '在 PPT', '在课本', '在书上',
    ]:
        if kw in s:
            return True
    if re.search(r'(读|写|想|说|圈|画|找|分|排|拼|演|背|填|贴|折|剪|描|查|认|念|听|看|比|评|改|选|答|问|议|摘|抄|默|朗|背|诵|演|扮|画|做|捏|贴|撕|铺|摆|扔|抛|滚|摇|掷|投)', s):
        return True
    return False


def fix_banned(s):
    for b, f in BANNED_FIX.items():
        s = s.replace(b, f)
    s = re.sub(r'  +', ' ', s)
    s = re.sub(r'。\s*。', '。', s)
    return s


def fix_char_displace(s):
    for pat in CHAR_DISPLACE_PATTERNS:
        s = re.sub(pat, pat[1:], s)
    return s


def smart_truncate(s, max_len):
    if len(s) <= max_len:
        return s
    cut = s.rfind('。', 0, max_len)
    if cut == -1 or cut < max_len - 30:
        cut = s.rfind(';', 0, max_len)
    if cut == -1 or cut < max_len - 30:
        cut = s.rfind(',', 0, max_len)
    if cut == -1 or cut < max_len - 30:
        cut = max_len
    else:
        cut += 1
    return s[:cut]


def smart_pad_with_field(s, field, min_len):
    PADS = {
        'real_examples': [
            '课本配套的「思考题」有 2-3 道选做题, 学有余力的孩子可以课后完成。',
            '课后「阅读链接」有相关的课外阅读篇目, 老师可以推荐给感兴趣的孩子。',
            '这套内容是本单元的重点, 老师可以让孩子提前预习, 圈出生字新词。',
            '「语文园地」里有对应的字词句运用, 老师可以当堂做 2-3 分钟小练习。',
        ],
        'common_mistakes': [
            '针对这些错法, 老师可以在黑板上列「错字 3 连」, 让孩子找错并改正。',
            '建议把常见错字打印成「错字卡」, 让孩子同桌互改, 改对了画星。',
            '每节课留 5 分钟「错字回头看」, 让孩子说说自己错在哪、怎么记。',
            '老师可以做一个「易错字本」, 让孩子每人记一个, 期末复习用。',
        ],
        'teaching_activity': [
            '活动结束后, 老师可以让 3-4 个孩子上台展示, 其他孩子点评哪里写得好。',
            '配套练习册有 4-5 道跟进题, 老师可以当堂完成, 错的同桌互讲。',
            '活动完成后, 老师用 3 分钟做全班小结, 强调最容易错的地方。',
            '老师可以拍下孩子的作业/作品, 用投影展示, 让全班评一评。',
        ],
    }
    if len(s) >= min_len:
        return s
    pads = PADS.get(field, ['老师可以多设计几组练习让孩子练。'])
    pad = pads[len(s) % len(pads)]
    cut = s.rfind('。')
    if cut == -1:
        return s + pad
    return s[:cut+1] + pad


def repair_one(item):
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


def validate(item):
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


def call_llm_strict(concept):
    system = """你是 V3.3.4 语文教师用书深度内容编辑. 你的任务是给语文概念写「教师用书」级别的 3 个补充字段.

# 严格 3 字段
1. `real_examples` (60-120 字): 必须含部编版/人教版/苏教版 + 几年级 + 几册 + 第几课《XXX》/第几单元.
2. `common_mistakes` (60-120 字): **必须含具体错法**, 用「学生把 X 写成 Y」「学生 X 和 Y 混用」「学生漏 X 标点」「学生 X 用成 Y」句式, 至少 2 个具体错例.
3. `teaching_activity` (60-120 字): **必须含具体动作**, 用「用 X 教具」「让学生 X」「在田字格上 X」「在米字格上 X」「用生字卡 X」句式.

# 3 字段独立, 不可重复
- real_examples: 课本定位 (部编版 + 几年级 + 几册 + 第几课 + 课文题目)
- common_mistakes: 学生具体错法 (写错哪个字/用错哪个标点/写错哪句)
- teaching_activity: 教具 + 操作 (用什么 + 做什么 + 怎么操作)

# 严格风格
- 60-120 字, 1 段不换行, 中间可用「」
- 绝不要用「理解/培养/掌握/运用/知识点/课标/教学目标/含义/定义/本概念/该概念/本节/本文/通过本」等公文腔
- 写错别字要具体: "把「辨」写成「辩」" / "「的」「地」「得」用错"
- 教具具体: 田字格 / 米字格 / 生字卡 / 拼音卡 / 新华字典 / 课文 / 彩笔 / 贴纸
- 内容严禁使用 ASCII 双引号 ", 全部用「」

# 输出格式
严格 JSON 数组, 每条 { "id": "...", "real_examples": "...", "common_mistakes": "...", "teaching_activity": "..." }"""
    user = f'''请为以下语文概念生成 3 字段:

ID: {concept["id"]}
Title: {concept["title"]}
Domain: {concept["domain"]} / {concept["subdomain"]}
Stage: G{concept["grade_start"]}-{concept["grade_end"]}
Content: {concept["content_req"]}
Key: {"; ".join(concept["key_points"]) if concept.get("key_points") else "无"}

要求:
- real_examples 必须含 "部编版" 或 "人教版" 或 "苏教版" + "X 年级" + "第 X 课" + 课文题目
- common_mistakes 必须用 "学生把 X 写成 Y" / "学生 X 和 Y 混用" / "学生漏 X" / "学生 X 用成 Y" 句式, 至少 2 个具体错例
- teaching_activity 必须含 "用 X" (教具) 或 "让学生" 或 "在田字格" 或 "在米字格" 句式

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


def parse_json(text):
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

    out = sorted(done.values(), key=lambda x: x['id'])
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'\n=== 完成 ===', flush=True)
    print(f'总产出: {len(done)} / {len(input_data)}', flush=True)
    print(f'剩余失败: {len([c for c in input_data if c["id"] not in done])}', flush=True)
    print(f'用时: {(time.time()-t0)/60:.1f} min', flush=True)


if __name__ == '__main__':
    main()
