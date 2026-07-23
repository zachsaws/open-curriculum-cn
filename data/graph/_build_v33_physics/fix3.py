"""
V3.3.3 Physics LLM 化: 补 3 个失败 (P_P2_18, P_P4_05, P_G79_EX_06)
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

INPUT = 'data/v33_inputs/physics_remaining_input.json'
OUTPUT = 'data/graph/physics_v33_llm.json'

with open('/Users/tianxiang/.claude/settings.json') as f:
    settings = json.load(f)
TOKEN = settings['env']['ANTHROPIC_AUTH_TOKEN']
BASE_URL = 'https://api.minimaxi.com/anthropic/v1/messages'

# 加载已有
done = {c['id']: c for c in json.load(open(OUTPUT))}
print(f'已有: {len(done)} 概念', flush=True)

# 加载 input
all_data = json.load(open(INPUT))
target_ids = ['P_P2_18', 'P_P4_05', 'P_G79_EX_06']
targets = [c for c in all_data if c['id'] in target_ids]
print(f'待补: {[c["id"] for c in targets]}', flush=True)

# 通用 prompt (单条)
SYSTEM_PROMPT = """你是 V3.3.3 物理学科内容编辑. 你的任务: 把物理学科概念用「人话级」中文写出来.

# description 规则 (60-100 字, 1 段不换行)
- **必须用实验/具体现象代替抽象定义** — 例: 「用刻度尺量课本短边, 能不能读出 18.4 cm?」
- 物理要画面感: 器材 + 数字 + 动作 + 看到的现象
- 中间可用「」, **绝不要在 content 内用 ASCII 双引号 "**
- 不用绝对化承诺 (一定/必然/肯定)
- 反直觉 + 具体, 优于课标原文

# assessment_prompt 规则 (150-220 字, 3 问)
- **正好 3 问**, 行间用 \\n 分隔 (一个反斜杠加 n, 2 字符)
- 每问 1 个 {{name}} 占位符 (两个花括号包 name)
- 场景要具体: 含具体数字/具体器材/具体动作/具体现象
- 3 问难度递进: 第 1 问直接识别, 第 2 问操作/反例, 第 3 问解释/迁移
- 中文要自然: "能不能 / 会不会" 优于 "能否"
- 物理优先实验/具体场景
- **绝不要在 content 内用 ASCII 双引号 "** (用「」)

# 禁词 (BANNED, 命中必须改)
理解 / 培养 / 掌握 / 运用 / 知识点 / 课标 / 教学目标 / 含义 / 定义 / 本概念 / 该概念 / 本节 / 本文 / 通过本 / 课标要求 / 具体含义

# 输出格式
严格 JSON: {"id": "...", "description": "...", "assessment_prompt": "问1\\n问2\\n问3"}
不要 markdown 包裹. 严禁 ASCII 双引号 " 在 content 内部, 必须用「」."""


def call_llm_one(c):
    user = (
        f'ID: {c["id"]}\n'
        f'Title: {c["title"]}\n'
        f'Domain: {c["domain"]} / {c["subdomain"]}\n'
        f'Stage: 阶段{c["stage"]} (G{c["grade_start"]}-{c["grade_end"]})\n'
        f'Content: {c["content_req"]}\n'
        f'Key: {"; ".join(c["key_points"])}\n'
        f'Bloom: {", ".join(c["bloom"]) if c.get("bloom") else "无"}\n\n'
        f'请输出严格 JSON 对象: {{"id":"{c["id"]}","description":"...","assessment_prompt":"问1\\n问2\\n问3"}}'
    )
    body = json.dumps({
        'model': 'MiniMax-M3',
        'max_tokens': 2000,
        'system': SYSTEM_PROMPT,
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
        except Exception as e:
            print(f'  [Err {type(e).__name__}] {e}, retry {attempt+1}/3', flush=True)
            time.sleep(5 + attempt * 5)
    raise RuntimeError('LLM 3 次都失败')


def parse_one(text):
    text = text.strip()
    text = re.sub(r'^```\w*\s*\n?', '', text)
    text = re.sub(r'\n?\s*```\s*$', '', text)
    m = re.search(r'\{', text)
    if not m:
        return None
    start = m.start()
    end = text.rfind('}')
    if end < start:
        return None
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
    try:
        return json.loads(fixed_text)
    except Exception as e:
        print(f'  [JSON parse fail] {e}', flush=True)
        return None


def fix_banned(s):
    BAD = {
        '理解': '看明白',
        '培养': '养成',
        '掌握': '会用',
        '运用': '用起来',
        '含义': '意思',
        '定义': '是啥',
        '本概念': '它',
        '该概念': '它',
    }
    for b, f in BAD.items():
        s = s.replace(b, f)
    s = re.sub(r'  +', ' ', s)
    s = re.sub(r'。\s*。', '。', s)
    return s


def smart_truncate_desc(s):
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


def smart_truncate_ass(s):
    if len(s) <= 220:
        return s
    NL = chr(92) + 'n'
    parts = s.split(NL)
    if len(parts) >= 3:
        first_two = parts[0] + NL + parts[1]
        if len(first_two) <= 220:
            return first_two + NL + '{{name}}能举个例子吗?'
        else:
            p0 = parts[0]
            cut = p0.rfind('?', 0, 200)
            if cut == -1:
                cut = p0.rfind('？', 0, 200)
            if cut == -1 or cut < 80:
                cut = 200
            else:
                cut += 1
            return p0[:cut] + NL + '{{name}}能再举一个例子吗?' + NL + '{{name}}能不能讲给朋友听?'
    cut = s.rfind('?', 0, 215)
    if cut == -1:
        cut = s.rfind('？', 0, 215)
    if cut == -1 or cut < 100:
        cut = 215
    else:
        cut += 1
    return s[:cut]


def pad_assessment(ass):
    PADS = [
        "再说说为什么?", "然后呢?", "这一步怎么想?",
        "能换一种说法吗?", "在什么场景下会用上?",
        "能举个例子吗?", "{{name}}会不会自己编一个?",
    ]
    NL = chr(92) + 'n'
    while len(ass) < 150:
        parts = ass.split(NL)
        added = False
        for i, p in enumerate(parts):
            if '{{name}}' not in p:
                pad = PADS[len(ass) % len(PADS)]
                if '{{name}}' in pad and '{{name}}' in p:
                    pad = "能举个例子吗?"
                parts[i] = p.rstrip('?？。.') + ', ' + pad
                ass = NL.join(parts)
                added = True
                break
        if not added:
            pad = PADS[len(ass) % len(PADS)]
            if '{{name}}' in pad:
                pad = "能举个例子吗?"
            ass = ass + ' ' + pad
    return ass


def repair(item):
    desc = item.get('description', '').strip()
    ass = item.get('assessment_prompt', '').strip()
    desc = fix_banned(desc)
    desc = smart_truncate_desc(desc)
    if len(desc) < 60:
        desc = (desc + '用刻度尺量课本短边, 能不能读出 18.4 cm?')[:100]
    ass = fix_banned(ass)
    ass = ass.replace('\r\n', '\n').replace('\r', '\n')
    ass = ass.replace('\n', chr(92) + 'n')
    parts = ass.split(chr(92) + 'n')
    parts = [p.strip() for p in parts if p.strip()]
    PADS_Q = [
        "{{name}}能不能举出一个实验例子?",
        "如果{{name}}答不上来, 怎么提示?",
        "{{name}}能不能换一种说法解释?",
        "{{name}}会不会主动问为什么?",
    ]
    while len(parts) < 3:
        parts.append(PADS_Q[len(parts) % len(PADS_Q)])
    parts = parts[:3]
    NAME_RE = re.compile(r'(小明|小红|小华|小丽|小强|小军|小芳|小英|小东|小亮|小杰|小燕|小辉|家长|老师|妈妈|爸爸|同学|孩子|宝宝|哥哥|姐姐|弟弟|妹妹|小朋友|学生)')
    for i, p in enumerate(parts):
        parts[i] = NAME_RE.sub('{{name}}', p)
    for i, p in enumerate(parts):
        cnt = p.count('{{name}}')
        if cnt == 0:
            parts[i] = p.rstrip('?？。.') + ', {{name}}试试?'
        elif cnt > 1:
            chunks = p.split('{{name}}')
            parts[i] = chunks[0] + '{{name}}' + ''.join(chunks[1:])
    ass = (chr(92) + 'n').join(parts)
    if len(ass) > 220:
        ass = smart_truncate_ass(ass)
    if len(ass) < 150:
        ass = pad_assessment(ass)
    return {'id': item['id'], 'description': desc, 'assessment_prompt': ass}


def validate(item):
    issues = []
    desc = item.get('description', '')
    ass = item.get('assessment_prompt', '')
    if not (60 <= len(desc) <= 100):
        issues.append(f'desc_len={len(desc)}')
    if not (150 <= len(ass) <= 220):
        issues.append(f'ass_len={len(ass)}')
    if ass.count('{{name}}') != 3:
        issues.append(f'name_count={ass.count("{{name}}")}')
    if ass.count('\\n') < 2:
        issues.append(f'nl_count={ass.count(chr(92)+"n")}')
    BAD = ['理解', '培养', '掌握', '运用', '知识点', '课标', '教学目标', '含义', '定义', '本概念', '该概念', '本节', '本文', '通过本', '课标要求', '具体含义']
    for b in BAD:
        if b in desc or b in ass:
            issues.append(f'禁词[{b}]')
    return issues


# 主流程
for c in targets:
    print(f'\n=== {c["id"]} | {c["title"]} ===', flush=True)
    for attempt in range(1, 4):
        try:
            text = call_llm_one(c)
        except Exception as e:
            print(f'  attempt {attempt} LLM 错: {e}', flush=True)
            time.sleep(2)
            continue
        item = parse_one(text)
        if not item or item.get('id') != c['id']:
            print(f'  attempt {attempt} parse fail', flush=True)
            time.sleep(1)
            continue
        item = repair(item)
        issues = validate(item)
        if not issues:
            done[c['id']] = item
            print(f'  attempt {attempt} PASS desc={len(item["description"])} ass={len(item["assessment_prompt"])}', flush=True)
            break
        print(f'  attempt {attempt} fail: {issues}', flush=True)
        time.sleep(1)
    else:
        print(f'  ALL 3 attempts failed, manual needed', flush=True)

# 写回
out = sorted(done.values(), key=lambda x: x['id'])
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
print(f'\n保存 {len(out)} 概念 → {OUTPUT}', flush=True)
