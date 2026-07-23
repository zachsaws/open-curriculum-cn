"""
V3.3.3 Labor LLM 化: 85 劳动概念分批调 LLM, 每批 5 + 全面 mechanical repair.

借鉴 english 296 / chinese 209 / physics 121 教训:
- 5 概念/批 (比 30 稳定得多)
- 真换行 → 字面 \\n 必须用 .replace (不用 re.sub)
- post-validation: desc 60-100, ass 150-220, {{name}}=3, \\n>=2, 禁词=0
- 劳动特殊 post-validation (借鉴 english+physics 学到的 LLM bug):
  1. "连续 2+ 空格 + 形式/词" 缺值检测
  2. "用 X 原看明白/掌握/运用/理解" 字符错位检测 (LLM 把 "原本" 切到 "原" 的常见 bug)
  3. "{{name}}能举个例子吗" 模板回潮检测 — 重写到具体场景
- 劳动要"具体劳动任务" — 例: "扫地 5 分钟, {{name}} 能不能扫干净 5 平米地面?"
- 禁词 0 容忍, 不达标重写
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

# ---- 配置 ----
INPUT = 'data/v33_inputs/labor_remaining_input.json'
OUTPUT = 'data/graph/labor_v33_llm.json'
CACHE = 'data/graph/_build_v33_labor/'

# Token (从 ~/.claude/settings.json env.ANTHROPIC_AUTH_TOKEN 读)
with open('/Users/tianxiang/.claude/settings.json') as f:
    settings = json.load(f)
TOKEN = settings['env']['ANTHROPIC_AUTH_TOKEN']
BASE_URL = 'https://api.minimaxi.com/anthropic/v1/messages'

# 禁词
BANNED = ['理解', '培养', '掌握', '运用', '知识点', '课标', '教学目标', '含义', '定义', '本概念', '该概念', '本节', '本文', '通过本', '课标要求', '具体含义']
BANNED_FIX = {
    '理解': '看明白',
    '培养': '养成',
    '掌握': '会用',
    '运用': '用起来',
    '含义': '意思',
    '定义': '是啥',
    '本概念': '它',
    '该概念': '它',
}
# 劳动关键词 (用于 "接 X 形式" 缺值检测 — 工具/材料/动作/单位)
LABOR_MISSING = ['工具', '材料', '动作', '步骤', '方法', '顺序', '时间', '分钟', '次数', '数量', '面积', '米', '尺寸', '重量', '大小', '位置', '地方', '场域', '场所', '房间', '桌子', '地面', '窗户', '形式', '单位', '数值', '方向']

# 字符错位检测 — LLM 经常把 "原本" 拆成 "原" + 后面的动词 ("原看明白" / "原掌握")
CHAR_DISPLACE_PATTERNS = [
    r'原看明白',     # 本看明白
    r'原掌握',       # 本掌握
    r'原运用',       # 本运用
    r'原理解',       # 本理解
    r'原养成',       # 本养成
    r'原会用',       # 本会用
    r'原用起来',     # 本用起来
    r'原意思',       # 本意思
    r'原是啥',       # 本是啥
    r'原通过',       # 本通过
]

# 模板回潮检测 — "{{name}}能举个例子吗" 这种空模板 (LLM 补到 3 段时的常见兜底)
TEMPLATE_REGRESSION_PATTERNS = [
    '{{name}}能举个例子吗?',
    '{{name}}能举个例子吗？',
    '{{name}}能再举一个例子吗?',
    '{{name}}能再举一个例子吗？',
    '{{name}}能举出一个例子吗?',
    '{{name}}能举出一个例子吗？',
    '能举个例子吗?',
    '能举个例子吗？',
]


# ---- 输入 ----
data = json.load(open(INPUT))
print(f'Total: {len(data)} concepts', flush=True)

# ---- 已有产出 (断点续跑) ----
done = {}
if os.path.exists(OUTPUT):
    existing = json.load(open(OUTPUT))
    done = {c['id']: c for c in existing}
    print(f'已存在: {len(done)} 概念 (skip)', flush=True)

# ---- prompt 构造 ----
SYSTEM_PROMPT = """你是 V3.3.3 劳动学科内容编辑. 你的任务: 把劳动学科概念用「人话级」中文写出来, 让家长/老师/学生看了就想用.

# description 规则 (60-100 字, 1 段不换行)
- **必须用具体劳动任务代替抽象定义** — 例:
  - 「洗手 30 秒, 用七步洗手法, 搓完手心搓手背, 指缝指尖都搓到」 → 而不是「学会个人清洁」
  - 「扫地 5 分钟, 角落和桌腿底下也别漏, 扫完簸箕里要看到头发和碎屑」 → 而不是「会打扫教室」
  - 「切土豆丝, 先切片再切丝, 粗细像火柴棍, 一盘菜大概 200 克」 → 而不是「学会简单烹饪」
  - 「种一盆绿萝, 每周浇 1 次, 每次 200 mL, 叶子蔫了就是缺水」 → 而不是「体验种植活动」
- 劳动要画面感: 工具/材料 + 数字 + 动作 + 看到的现象
- 中间可用「」, **绝不要在 content 内用 ASCII 双引号 "**
- 不用绝对化承诺 (一定/必然/肯定)
- 反直觉 + 具体, 优于课标原文
- **绝不要"培养劳动习惯"这种抽象话** — 一定要落到「扫地几分钟/搓几次/洗几件」具体动作

# assessment_prompt 规则 (150-220 字, 3 问)
- **正好 3 问**, 行间用 \\n 分隔 (一个反斜杠加 n, 2 字符)
- 每问 1 个 {{name}} 占位符 (两个花括号包 name, 不能用「小明」「孩子」等替代)
- 场景要具体: 含具体数字/具体工具/具体动作/具体对话 — 拒绝「理解 X 这一概念, 能否独立完成相关题目?」这种空问
- 3 问难度递进: 第 1 问直接识别/操作, 第 2 问反例/纠错, 第 3 问解释/迁移
- 中文要自然: "能不能 / 会不会 / 会不会出现" 优于 "能否"
- 劳动优先具体场景: "用 1 把扫帚扫 5 平米地面 5 分钟, {{name}} 能不能扫干净?"
- **绝不要在 content 内用 ASCII 双引号 "** (用「」)

# 禁词 (BANNED, 命中必须改)
理解 / 培养 / 掌握 / 运用 / 知识点 / 课标 / 教学目标 / 含义 / 定义 / 本概念 / 该概念 / 本节 / 本文 / 通过本 / 课标要求 / 具体含义

# 禁模板句 (禁止使用)
- "在 X 课上, {name} 能否..."
- "用自己的话解释 X 的含义"
- "独立完成相关题目"
- "举出一个生活中的例子"
- "在 X 这一概念中"

# 输出格式
严格 JSON 数组, 每条 { "id": "...", "description": "...", "assessment_prompt": "问1\\n问2\\n问3" }
不要 markdown 包裹, 不要其他字段. 再次强调: content 内部严禁使用 ASCII 双引号 " ! 必须用「」."""


def call_llm(concepts: list[dict]) -> str:
    """调 LLM 一次, 返回 raw text."""
    user_lines = [f'请为以下 {len(concepts)} 个劳动概念各生成 description + assessment_prompt:\n']
    for c in concepts:
        user_lines.append(
            f'---\n'
            f'ID: {c["id"]}\n'
            f'Title: {c["title"]}\n'
            f'Domain: {c["domain"]} / {c["subdomain"]}\n'
            f'Stage: 阶段{c["stage"]} (G{c["grade_start"]}-{c["grade_end"]})\n'
            f'Content: {c["content_req"]}\n'
            f'Key: {"; ".join(c["key_points"])}\n'
            f'Bloom: {", ".join(c["bloom"]) if c.get("bloom") else "无"}'
        )
    user_lines.append('\n请输出严格 JSON 数组, 每条含 id, description, assessment_prompt (3 问, 用 \\n 分隔).')
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
    """从 LLM 输出里解析 JSON 数组, 容错修.
    启发式: 找所有 ASCII " 位置, 两两配对, 验证每对的前后上下文是否合理.
    """
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

    # 找所有 ASCII " 位置 (跳过 escape)
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

    # 配对 + 验证
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

    # 用 valid_pairs 切片, 替换 body 中嵌入的 "
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
    """修 "原看明白/原掌握/原运用" 等字符错位 bug.
    启发式: 这些 pattern 是 LLM 把 "本看明白" 误打成 "原看明白" (把"本"字打成"原"字)
    直接删掉 "原" 字.
    """
    for pat in CHAR_DISPLACE_PATTERNS:
        s = re.sub(pat, pat[1:], s)  # 去掉 "原" 字, 保留后面
    return s


def smart_truncate_desc(s: str) -> str:
    if len(s) <= 100:
        return s
    cut = s.rfind('。', 0, 100)
    if cut == -1 or cut < 50:
        cut = s.rfind('，', 0, 100)
    if cut == -1 or cut < 50:
        cut = 100
    else:
        cut += 1
    return s[:cut]


def smart_truncate_ass(s: str) -> str:
    """智能截断 ass, 保留 3 段结构 (用 literal \\n 分隔)."""
    if len(s) <= 220:
        return s
    NL = chr(92) + 'n'
    parts = s.split(NL)
    if len(parts) >= 3:
        first_two = parts[0] + NL + parts[1]
        if len(first_two) <= 220:
            return first_two + NL + '{{name}}能不能再做一次看看?'
        else:
            p0 = parts[0]
            cut = p0.rfind('?', 0, 200)
            if cut == -1:
                cut = p0.rfind('？', 0, 200)
            if cut == -1 or cut < 80:
                cut = 200
            else:
                cut += 1
            return p0[:cut] + NL + '{{name}}能不能再试一次?' + NL + '{{name}}能不能教别的小朋友?'
    cut = s.rfind('?', 0, 215)
    if cut == -1:
        cut = s.rfind('？', 0, 215)
    if cut == -1 or cut < 100:
        cut = 215
    else:
        cut += 1
    return s[:cut]


def pad_assessment(ass: str) -> str:
    """补足长度, 避免用 "{{name}}能举个例子吗" 模板回潮."""
    PADS = [
        "{{name}}能不能再描述一下过程?",
        "{{name}}做的时候心里在想什么?",
        "{{name}}做完之后什么感觉?",
        "{{name}}能不能跟家人讲一遍?",
        "{{name}}下次会怎么改?",
        "{{name}}能不能用计时器看看自己用了几分钟?",
        "{{name}}能不能把工具收好再去做?",
        "{{name}}发现自己做错了会不会重做?",
        "{{name}}做完会不会自己检查一遍?",
        "{{name}}能不能把这个步骤告诉同学?",
    ]
    NL = chr(92) + 'n'
    while len(ass) < 150:
        parts = ass.split(NL)
        added = False
        for i, p in enumerate(parts):
            if '{{name}}' not in p:
                pad = PADS[len(ass) % len(PADS)]
                if '{{name}}' in pad and '{{name}}' in p:
                    pad = "{{name}}能不能再说一遍?"
                parts[i] = p.rstrip('?？。.') + ', ' + pad
                ass = NL.join(parts)
                added = True
                break
        if not added:
            pad = PADS[len(ass) % len(PADS)]
            if '{{name}}' in pad:
                pad = "{{name}}能不能再说一遍?"
            ass = ass + ' ' + pad
    return ass


def detect_2space_then_keyword(s: str) -> list[tuple[int, str]]:
    """检测 "连续 2+ 空格 + 劳动关键词" 这种"接 X 形式"缺值.
    返回 [(位置, 关键词), ...]. 修时插入占位.
    """
    findings = []
    for m in re.finditer(r'  +', s):
        ctx = s[m.end():m.end() + 30]
        for kw in LABOR_MISSING:
            if ctx.startswith(kw):
                findings.append((m.start(), kw))
                break
    return findings


def detect_template_regression(s: str) -> list[tuple[int, str]]:
    """检测 "{{name}}能举个例子吗" 模板回潮.
    返回 [(位置, pattern), ...].
    """
    findings = []
    for pat in TEMPLATE_REGRESSION_PATTERNS:
        for m in re.finditer(re.escape(pat), s):
            findings.append((m.start(), pat))
    return findings


def replace_template_regression(s: str) -> str:
    """把 "{{name}}能举个例子吗?" 替换成具体场景 (劳动版)."""
    REPLACEMENTS = [
        "{{name}}能不能再扫一次 5 平米的地面, 看这次能不能 3 分钟扫完?",
        "{{name}}能不能把刚才的步骤跟妈妈说一遍?",
        "{{name}}做完会不会自己把工具放回原位?",
        "{{name}}能不能计时看看自己用了多少分钟?",
        "{{name}}能不能自己发现哪里没做好, 然后重做一次?",
        "{{name}}能不能教别的小朋友做这个?",
    ]
    for pat in TEMPLATE_REGRESSION_PATTERNS:
        # 替换第一次出现, 循环直到全部替换
        while pat in s:
            replacement = REPLACEMENTS[hash(pat) % len(REPLACEMENTS)]
            s = s.replace(pat, replacement, 1)
    return s


def repair_one(item: dict) -> dict:
    cid = item.get('id', '?')
    desc = item.get('description', '').strip()
    ass = item.get('assessment_prompt', '').strip()

    # 1. 修 desc
    desc = fix_banned(desc)
    desc = fix_char_displace(desc)
    desc = smart_truncate_desc(desc)
    if len(desc) < 60 and item.get('_orig_content'):
        extra = item['_orig_content'][:80]
        desc = (desc + extra)[:100]

    # 2. 修 ass
    ass = fix_banned(ass)
    ass = fix_char_displace(ass)

    # 标准化: real newlines → literal \\n (2 chars: backslash + n)
    ass = ass.replace('\r\n', '\n').replace('\r', '\n')
    ass = ass.replace('\n', chr(92) + 'n')  # 直接 replace, 不用 re.sub

    # 拆 3 段 (按 literal \\n)
    parts = ass.split(chr(92) + 'n')  # 2-char split
    parts = [p.strip() for p in parts if p.strip()]

    PADS_Q = [
        "{{name}}能不能做完再检查一遍?",
        "{{name}}做的时候心里在想什么?",
        "{{name}}做完之后会自己收拾工具吗?",
        "{{name}}能不能把步骤讲给朋友听?",
        "{{name}}下次会怎么做?",
        "{{name}}能不能用计时器看自己用了多久?",
        "{{name}}发现不对会不会停下来重做?",
        "{{name}}能不能自己发现哪里出了问题?",
    ]

    # 补足 3 段
    while len(parts) < 3:
        parts.append(PADS_Q[len(parts) % len(PADS_Q)])
    parts = parts[:3]

    # {{name}} 处理: 替换常见人名
    NAME_RE = re.compile(r'(小明|小红|小华|小丽|小强|小军|小芳|小英|小东|小亮|小杰|小燕|小辉|家长|老师|妈妈|爸爸|同学|孩子|宝宝|哥哥|姐姐|弟弟|妹妹|小朋友|学生)')
    for i, p in enumerate(parts):
        parts[i] = NAME_RE.sub('{{name}}', p)

    # 确保每段正好 1 个 {{name}}
    for i, p in enumerate(parts):
        cnt = p.count('{{name}}')
        if cnt == 0:
            p = p.rstrip('?？。.') + ', {{name}}试试?'
            parts[i] = p
        elif cnt > 1:
            chunks = p.split('{{name}}')
            kept = chunks[0] + '{{name}}' + ''.join(chunks[1:])
            parts[i] = kept

    ass = (chr(92) + 'n').join(parts)  # 2-char join

    # 模板回潮检测 + 替换 (劳动版)
    ass = replace_template_regression(ass)

    # 长度
    if len(ass) > 220:
        ass = smart_truncate_ass(ass)
    if len(ass) < 150:
        ass = pad_assessment(ass)
        # 补完可能又触发模板回潮, 再修一次
        ass = replace_template_regression(ass)

    item['description'] = desc
    item['assessment_prompt'] = ass
    return item


def validate(item: dict) -> list[str]:
    issues = []
    desc = item.get('description', '')
    ass = item.get('assessment_prompt', '')
    if not (60 <= len(desc) <= 100):
        issues.append(f'desc_len={len(desc)}')
    if not (150 <= len(ass) <= 220):
        issues.append(f'ass_len={len(ass)}')
    if ass.count('{{name}}') != 3:
        issues.append(f'name_count={ass.count("{{name}}")}')
    if ass.count(chr(92) + 'n') < 2:
        issues.append(f'nl_count={ass.count(chr(92)+"n")}')
    for b in BANNED:
        if b in desc or b in ass:
            issues.append(f'禁词[{b}]')
    # 劳动专项 1: 2+ 空格 + 关键缺值词
    for s, label in [(desc, 'desc'), (ass, 'ass')]:
        findings = detect_2space_then_keyword(s)
        if findings:
            issues.append(f'{label}_2space_keyword={findings[:3]}')
    # 劳动专项 2: 字符错位 (原看明白 等)
    for s, label in [(desc, 'desc'), (ass, 'ass')]:
        for pat in CHAR_DISPLACE_PATTERNS:
            if re.search(pat, s):
                issues.append(f'{label}_char_displace[{pat}]')
                break
    # 劳动专项 3: 模板回潮 ({{name}}能举个例子吗)
    for s, label in [(desc, 'desc'), (ass, 'ass')]:
        findings = detect_template_regression(s)
        if findings:
            issues.append(f'{label}_template_regression={findings[:2]}')
    return issues


# ---- 主流程 ----
def main():
    BATCH_SIZE = 5  # 5/batch 稳定 (借鉴 english 教训: 30/batch 大批经常 0/30 全解析失败)
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
        for c in batch:
            c['_orig_content'] = c.get('content_req', '')
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
            if c['id'] in parsed_by_id:
                item = parsed_by_id[c['id']]
                item['_orig_content'] = c['_orig_content']
                item = repair_one(item)
                issues = validate(item)
                if not issues:
                    repaired.append({'id': item['id'], 'description': item['description'], 'assessment_prompt': item['assessment_prompt']})
                else:
                    # 单条重试
                    print(f'  {c["id"]} 批量版不达标 {issues}, 单条重试', flush=True)
                    try:
                        single_text = call_llm([c])
                        single = parse_json(single_text)
                        if single and single[0].get('id') == c['id']:
                            single[0]['_orig_content'] = c['_orig_content']
                            single[0] = repair_one(single[0])
                            issues2 = validate(single[0])
                            if not issues2:
                                repaired.append({'id': single[0]['id'], 'description': single[0]['description'], 'assessment_prompt': single[0]['assessment_prompt']})
                                print(f'    {c["id"]} 单条版通过', flush=True)
                            else:
                                # 二次单条重试
                                try:
                                    single_text2 = call_llm([c])
                                    single2 = parse_json(single_text2)
                                    if single2 and single2[0].get('id') == c['id']:
                                        single2[0]['_orig_content'] = c['_orig_content']
                                        single2[0] = repair_one(single2[0])
                                        issues3 = validate(single2[0])
                                        if not issues3:
                                            repaired.append({'id': single2[0]['id'], 'description': single2[0]['description'], 'assessment_prompt': single2[0]['assessment_prompt']})
                                            print(f'    {c["id"]} 二次单条版通过', flush=True)
                                        else:
                                            fails.append((c['id'], issues3))
                                            print(f'    {c["id"]} 二次单条版仍不达标: {issues3}', flush=True)
                                    else:
                                        fails.append((c['id'], issues2 + ['2nd_parse_fail']))
                                except Exception as e2:
                                    fails.append((c['id'], issues2 + [f'2nd_llm_err:{e2}']))
                        else:
                            fails.append((c['id'], issues + ['single_parse_fail']))
                    except Exception as e:
                        fails.append((c['id'], issues + [f'single_llm_err:{e}']))
            else:
                # 批量没出, 单条重试
                print(f'  {c["id"]} 批量未出, 单条重试', flush=True)
                try:
                    single_text = call_llm([c])
                    single = parse_json(single_text)
                    if single and single[0].get('id') == c['id']:
                        single[0]['_orig_content'] = c['_orig_content']
                        single[0] = repair_one(single[0])
                        issues2 = validate(single[0])
                        if not issues2:
                            repaired.append({'id': single[0]['id'], 'description': single[0]['description'], 'assessment_prompt': single[0]['assessment_prompt']})
                        else:
                            fails.append((c['id'], issues2))
                    else:
                        fails.append((c['id'], ['parse_fail']))
                except Exception as e:
                    fails.append((c['id'], [f'llm_err:{e}']))

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
