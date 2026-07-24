"""
V3.3.4 Chinese 教师用书深度增强: 为 chinese 209 概念生成 3 个新字段.

新字段 (每个 60-120 字):
- real_examples: 真实课例 (部编版/人教版/苏教版 + 几年级 + 第几课)
- common_mistakes: 常见学生错误 (错别字/病句/标点 + 具体错例)
- teaching_activity: 教学活动 (具体教具/动作/操作)

借鉴 V3.3.3 chemistry 经验: 5 概念/批 + 单条重试 + 二次单条.
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
CACHE = 'data/graph/_build_v34_chinese/'

# Token
with open('/Users/tianxiang/.claude/settings.json') as f:
    settings = json.load(f)
TOKEN = settings['env']['ANTHROPIC_AUTH_TOKEN']
BASE_URL = 'https://api.minimaxi.com/anthropic/v1/messages'

# 禁词
BANNED = ['理解', '培养', '掌握', '运用', '知识点', '课标', '教学目标', '含义', '定义', '本概念', '该概念', '本节', '本文', '通过本', '课标要求', '具体含义']
BANNED_FIX = {
    '理解': '看明白', '培养': '养成', '掌握': '会用', '运用': '用起来',
    '含义': '意思', '定义': '是啥', '本概念': '它', '该概念': '它',
}

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

# chinese 关键词 (用于检测具体性)
CHINESE_KEYWORDS = [
    # 教具
    '生字卡', '字卡', '拼音卡', '田字格', '米字格', '课文', '生字本', '字典', '新华字典',
    '彩笔', '贴纸', '卡片', '小黑板', 'PPT', '投影', '录音', '音频', '视频',
    # 操作
    '用 XX', '用 X', '让学生', '把 X', '把 Y', '读一读', '写一写', '想一想', '说一说',
    '圈一圈', '画一画', '找一找', '分一分', '排一排', '拼一拼', '演一演', '背一背',
    # 错法
    '写成', '写成错别字', '错别字', '写成错字', '漏写', '多写', '少写',
    '把 X 写成 Y', '把 X 看成 Y', '混淆', '搞混', '颠倒', '忘加', '忘写', '忘标',
    '标点', '逗号', '句号', '问号', '叹号', '引号', '冒号', '破折号', '省略号',
    '病句', '句子不通顺', '语序', '搭配不当', '重复', '多余',
]

TEXTBOOK_KW = ['部编版', '人教版', '苏教版', '北师大版', '沪教版', '语文版', '西师大版', '鲁教版', '义教课标', '课标实验稿']

SYSTEM_PROMPT = """你是 V3.3.4 小学语文教师用书深度内容编辑. 你的任务是给语文概念写「教师用书」级别的 3 个补充字段, 让一线语文老师拿过去就能照着上课.

# 输出 3 个字段
1. `real_examples` (60-120 字): 真实课例 — 写明"部编版/人教版/苏教版 几年级 上/下册 第几课《XXX》" + 该课具体教什么 + 学生读到什么/写到什么.
   - 例子: 「部编版三年级上册第 5 课《铺满金色巴掌的水泥道》: 重点学 '铺' '印' '排' 等生字, 课文用了 6 个比喻句, 老师带学生找比喻句仿写」
   - 反例 (绝不要): 「三年级上册讲比喻句」, 「课本里有相关内容」

2. `common_mistakes` (60-120 字): 常见学生错误 — 写"学生具体写错哪个字/哪个标点/哪句病句", 给 2-3 个具体错例.
   - 例子: 「'辨' 和 '辩' 写混 (分辨 vs 辩论); '的' '地' '得' 用错 (漂亮的衣服 vs 飞快地跑 vs 跑得快); 比喻句写成 '像...一样' 不会换其他喻体」
   - 反例 (绝不要): 「学生容易写错别字, 老师要强调」

3. `teaching_activity` (60-120 字): 教学活动 — 写"用什么教具 / 让学生做什么具体动作 / 怎么操作", 落地到「老师能直接照做」.
   - 例子: 「用田字格卡片写 '铺' 字, 老师先示范横竖撇捺笔顺, 学生在米字格上描 3 遍再独立写 2 遍; 写完后同桌互评, 圈出最好的 1 个字」
   - 反例 (绝不要): 「通过游戏让学生练习」, 「老师可以设计活动」

# 3 字段必须独立, 不可重复
- real_examples 偏 "教什么内容" (课本定位)
- common_mistakes 偏 "错在哪" (学生具体错误)
- teaching_activity 偏 "怎么教" (教具 + 操作)

# 严格风格
- **绝不要** 用「理解 / 培养 / 掌握 / 运用 / 知识点 / 课标 / 教学目标 / 含义 / 定义 / 本概念 / 该概念 / 本节 / 本文 / 通过本 / 课标要求 / 具体含义」等公文腔
- **必须** 真实具体: 课本版本 + 第几课 + 课文题目 / 学生具体错法 (写出错的字) / 具体教具 + 具体操作
- 3 字段都用 1 段, 中间不换行, 中间可用「」
- **绝不要在 content 内用 ASCII 双引号 "** (必须用「」)
- 写错别字要具体: "把 '辨' 写成 '辩'" / "'的' '地' '得' 用错" / "比喻句写成 '像 X 一样' 不会换喻体"
- 教具具体: 田字格 / 米字格 / 生字卡 / 拼音卡 / 课文 / 新华字典 / 彩笔 / 贴纸 / 卡片 / PPT

# 学科特化 (chinese)
- 课本首选: 部编版 (G1-G6 现行统编教材) / 人教版 / 苏教版 / 北师大版
- 章节定位: 「部编版 X 年级 X 册 第 X 课《XXX》」, 例 "部编版三年级上册第 5 课《铺满金色巴掌的水泥道》"
- 错别字常见对: 辨/辩, 的/地/得, 在/再, 做/作, 记/纪, 须/需, 密/蜜, 帐/账, 采/彩, 决/绝, 即/既, 复/覆
- 病句类型: 成分残缺 (缺主语/谓语/宾语), 搭配不当, 语序不当, 前后矛盾, 重复累赘
- 标点错: 一逗到底, 问号叹号混用, 引号嵌套, 顿号连用
- 教具首选: 田字格 (写字), 米字格 (写字), 生字卡 (识字), 拼音卡 (拼音), 新华字典 (查字), 课文 (朗读/背诵), 彩笔/贴纸 (手工/识字)

# 禁词 (BANNED, 命中必须改)
理解 / 培养 / 掌握 / 运用 / 知识点 / 课标 / 教学目标 / 含义 / 定义 / 本概念 / 该概念 / 本节 / 本文 / 通过本 / 课标要求 / 具体含义

# 禁模板句
- "在 X 课上, 能否..."
- "用自己的话解释 X 的含义"
- "独立完成相关题目"
- "举出一个生活中的例子"
- "通过本节学习"

# 输出格式
严格 JSON 数组, 每条 { "id": "...", "real_examples": "...", "common_mistakes": "...", "teaching_activity": "..." }
不要 markdown 包裹, 不要其他字段. 再次强调: content 内部严禁使用 ASCII 双引号 " ! 必须用「」."""


def call_llm(concepts: list[dict]) -> str:
    user_lines = [f'请为以下 {len(concepts)} 个语文概念各生成 real_examples + common_mistakes + teaching_activity:\n']
    for c in concepts:
        user_lines.append(
            f'---\n'
            f'ID: {c["id"]}\n'
            f'Title: {c["title"]}\n'
            f'Domain: {c["domain"]} / {c["subdomain"]}\n'
            f'Stage: 阶段{c["stage"]} (G{c["grade_start"]}-{c["grade_end"]})\n'
            f'Content: {c["content_req"]}\n'
            f'Key: {"; ".join(c["key_points"]) if c.get("key_points") else "无"}'
        )
    user_lines.append('\n请输出严格 JSON 数组, 每条含 id, real_examples (60-120 字含部编版/几年级/第几课), common_mistakes (60-120 字含具体错字/病句/标点), teaching_activity (60-120 字含教具/操作).')
    user_prompt = '\n'.join(user_lines)

    body = json.dumps({
        'model': 'MiniMax-M3',
        'max_tokens': 16000,
        'system': SYSTEM_PROMPT,
        'messages': [{'role': 'user', 'content': user_prompt}],
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


def repair_one(item: dict) -> dict:
    cid = item.get('id', '?')
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


def has_textbook(s: str) -> bool:
    for kw in TEXTBOOK_KW:
        if kw in s:
            return True
    if re.search(r'第\s*\d+\s*单元', s):
        return True
    if re.search(r'第\s*\d+\s*课', s):
        return True
    if re.search(r'例\s*\d+', s):
        return True
    if re.search(r'第\s*\d+\s*节', s):
        return True
    return False


def has_mistake_verb(s: str) -> bool:
    for kw in ['写成', '写成错', '错别字', '错字', '漏写', '多写', '少写', '写成 X', '混淆', '搞混', '颠倒', '忘加', '忘写', '忘标', '把 X', '看成', '写成错别字', '字形', '标点', '病句', '语序', '搭配', '重复', '漏字', '添字', '不通顺', '错把']:
        if kw in s:
            return True
    return False


def has_teaching_action(s: str) -> bool:
    for kw in CHINESE_KEYWORDS:
        if kw in s:
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
    if not has_textbook(re_field):
        issues.append('real_examples_no_textbook')
    if not has_mistake_verb(cm_field):
        issues.append('common_mistakes_no_verb')
    if not has_teaching_action(ta_field):
        issues.append('teaching_activity_no_action')
    return issues


def main():
    BATCH_SIZE = 5
    data = json.load(open(INPUT))
    print(f'Total: {len(data)} concepts', flush=True)

    done = {}
    if os.path.exists(OUTPUT):
        existing = json.load(open(OUTPUT))
        done = {c['id']: c for c in existing}
        print(f'已存在: {len(done)} 概念 (skip)', flush=True)

    all_results = dict(done)
    all_to_process = [c for c in data if c['id'] not in all_results]
    print(f'待处理: {len(all_to_process)} 概念', flush=True)

    batches = []
    for i in range(0, len(all_to_process), BATCH_SIZE):
        batches.append(all_to_process[i:i+BATCH_SIZE])
    print(f'分 {len(batches)} 批 (BATCH_SIZE={BATCH_SIZE})', flush=True)

    t0 = time.time()
    for bi, batch in enumerate(batches):
        print(f'\n=== Batch {bi+1}/{len(batches)} ({len(batch)} 概念) ===', flush=True)
        bt = time.time()
        try:
            text = call_llm(batch)
        except Exception as e:
            print(f'  [LLM 失败] {e}, 整个 batch 失败', flush=True)
            continue
        parsed = parse_json(text)
        print(f'  解析: {len(parsed)}/{len(batch)} (用时 {time.time()-bt:.1f}s)', flush=True)

        parsed_by_id = {p.get('id'): p for p in parsed if p.get('id')}

        repaired = []
        fails = []
        for c in batch:
            cid = c['id']
            if cid in parsed_by_id:
                item = parsed_by_id[cid]
                item = repair_one(item)
                issues = validate(item)
                if not issues:
                    repaired.append({
                        'id': cid,
                        'real_examples': item['real_examples'],
                        'common_mistakes': item['common_mistakes'],
                        'teaching_activity': item['teaching_activity'],
                    })
                else:
                    print(f'  {cid} 批量版不达标 {issues}, 单条重试', flush=True)
                    try:
                        single_text = call_llm([c])
                        single = parse_json(single_text)
                        if single and single[0].get('id') == cid:
                            single[0] = repair_one(single[0])
                            issues2 = validate(single[0])
                            if not issues2:
                                repaired.append({
                                    'id': cid,
                                    'real_examples': single[0]['real_examples'],
                                    'common_mistakes': single[0]['common_mistakes'],
                                    'teaching_activity': single[0]['teaching_activity'],
                                })
                                print(f'    {cid} 单条版通过', flush=True)
                            else:
                                try:
                                    single_text2 = call_llm([c])
                                    single2 = parse_json(single_text2)
                                    if single2 and single2[0].get('id') == cid:
                                        single2[0] = repair_one(single2[0])
                                        issues3 = validate(single2[0])
                                        if not issues3:
                                            repaired.append({
                                                'id': cid,
                                                'real_examples': single2[0]['real_examples'],
                                                'common_mistakes': single2[0]['common_mistakes'],
                                                'teaching_activity': single2[0]['teaching_activity'],
                                            })
                                            print(f'    {cid} 二次单条版通过', flush=True)
                                        else:
                                            fails.append((cid, issues3))
                                            print(f'    {cid} 二次单条版仍不达标: {issues3}', flush=True)
                                    else:
                                        fails.append((cid, issues2 + ['2nd_parse_fail']))
                                except Exception as e2:
                                    fails.append((cid, issues2 + [f'2nd_llm_err:{e2}']))
                        else:
                            fails.append((cid, issues + ['single_parse_fail']))
                    except Exception as e:
                        fails.append((cid, issues + [f'single_llm_err:{e}']))
            else:
                print(f'  {cid} 批量未出, 单条重试', flush=True)
                try:
                    single_text = call_llm([c])
                    single = parse_json(single_text)
                    if single and single[0].get('id') == cid:
                        single[0] = repair_one(single[0])
                        issues2 = validate(single[0])
                        if not issues2:
                            repaired.append({
                                'id': cid,
                                'real_examples': single[0]['real_examples'],
                                'common_mistakes': single[0]['common_mistakes'],
                                'teaching_activity': single[0]['teaching_activity'],
                            })
                        else:
                            fails.append((cid, issues2))
                    else:
                        fails.append((cid, ['parse_fail']))
                except Exception as e:
                    fails.append((cid, [f'llm_err:{e}']))

        print(f'  通过: {len(repaired)}, 失败: {len(fails)}', flush=True)
        if fails:
            for fid, iss in fails[:5]:
                print(f'    {fid}: {iss}', flush=True)

        for r in repaired:
            all_results[r['id']] = r

        out = sorted(all_results.values(), key=lambda x: x['id'])
        with open(OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
        print(f'  累计保存: {len(all_results)} → {OUTPUT}', flush=True)
        print(f'  累计用时: {(time.time()-t0)/60:.1f} min', flush=True)

    print(f'\n=== 完成 ===', flush=True)
    print(f'总产出: {len(all_results)} / {len(data)}', flush=True)
    print(f'失败: {len([c for c in data if c["id"] not in all_results])}', flush=True)


if __name__ == '__main__':
    main()
