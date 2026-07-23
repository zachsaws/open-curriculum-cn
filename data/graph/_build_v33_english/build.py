"""
V3.3.2 English LLM 化: 296 概念分批调 LLM, 每批 30 + mechanical repair.
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
INPUT = 'data/v33_inputs/english_remaining_input.json'
OUTPUT = 'data/graph/english_v33_llm.json'
CACHE = 'data/graph/_build_v33_english/'

# Token
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
SYSTEM_PROMPT = """你是英语学科内容编辑. 你的任务: 把英语学科的概念用「人话级」中文表达出来, 让家长/老师看了就想用.

## description 规则 (60-100 字)
- 1 段中文, 不换行
- 必须用**具体场景**代替抽象定义 — 写"用 apple 当水果举例子, 比背词汇表记 10 遍还牢" 而非"理解词汇的概念"
- **英语场景用对话/单词卡/角色扮演** — 例: 问"apple 怎么用? 写出 3 个句子", 避免"掌握词汇"这种空话
- 中间可用「」 (中文方头括号), **绝不要在 content 内用 ASCII 双引号 "**
- 不要用绝对化承诺 (一定/必然/肯定)
- 要反直觉, 要画面感

## assessment_prompt 规则 (150-220 字, 3 问)
- **正好 3 问**, 行间用 \\n 分隔 (一个反斜杠加 n)
- 每问 1 个 {{name}} 占位符 (1 个, 不能多, 不能少)
- 场景要具体: 含具体数字/具体物品/具体对话 — 拒绝"理解 X 这一概念, 能否独立完成相关题目?" 这种空问
- 3 问难度递进: 第 1 问直接识别, 第 2 问操作/反例, 第 3 问解释/迁移
- 中文要自然: "能不能 / 会不会 / 会不会出现" 优于 "能否"
- **绝不要在 content 内用 ASCII 双引号 "** (用「」)

## 禁词 (BANNED, 命中必须改)
- 理解 / 培养 / 掌握 / 运用 / 知识点 / 课标 / 教学目标 / 含义 / 定义 / 本概念 / 该概念 / 本节 / 本文 / 通过本 / 课标要求 / 具体含义

## 输出格式
严格 JSON 数组, 每条 { "id": "...", "description": "...", "assessment_prompt": "问1\\n问2\\n问3" }
不要 markdown 包裹, 不要其他字段. 再次强调: content 内部严禁使用 ASCII 双引号 " ! 必须用「」."""


def call_llm(concepts: list[dict]) -> str:
    """调 LLM 一次, 返回 raw text."""
    user_lines = [f'请为以下 {len(concepts)} 个英语概念各生成 description + assessment_prompt:\n']
    for c in concepts:
        user_lines.append(f'---\nID: {c["id"]}\nTitle: {c["title"]}\nDomain: {c["domain"]} / {c["subdomain"]}\nStage: 阶段{c["stage"]} (G{c["grade_start"]}-{c["grade_end"]})\nContent: {c["content_req"]}\nKey: {"; ".join(c["key_points"])}')
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
    LLM 输出应该是标准 JSON, 所以配对应该基本正确.
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

        # open 之前: [ , { , : 或 起始
        prev_ok = op == 0
        if not prev_ok:
            j = op - 1
            while j >= 0 and raw[j] in ' \t\n\r':
                j -= 1
            if j < 0 or raw[j] in '[{,:':
                prev_ok = True

        # close 之后: , } ] 或 结尾
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
    # 如果正好 3 段, 优先保留 2 段并加 pad
    if len(parts) >= 3:
        # 尝试保留前 2 段 (如果总长 > 220, 加上 1 pad)
        first_two = parts[0] + NL + parts[1]
        if len(first_two) <= 220:
            return first_two + NL + '{{name}}能举个例子吗?'
        else:
            # 第一段都超 220, 截第一段
            p0 = parts[0]
            cut = p0.rfind('?', 0, 200)
            if cut == -1:
                cut = p0.rfind('？', 0, 200)
            if cut == -1 or cut < 80:
                cut = 200
            else:
                cut += 1
            return p0[:cut] + NL + '{{name}}能再举一个例子吗?' + NL + '{{name}}能不能讲给朋友听?'
    # 否则直接找 ? 截断
    cut = s.rfind('?', 0, 215)
    if cut == -1:
        cut = s.rfind('？', 0, 215)
    if cut == -1 or cut < 100:
        cut = 215
    else:
        cut += 1
    return s[:cut]


def pad_assessment(ass: str) -> str:
    PADS = [
        "再说说为什么?",
        "然后呢?",
        "这一步怎么想?",
        "能换一种说法吗?",
        "对比上次, 进步在哪?",
        "换成你朋友能懂的话怎么说?",
        "如果{{name}}答不上来, 怎么提示?",
        "在什么场景下会用上?",
        "能举个例子吗?",
        "{{name}}会不会自己编一个?",
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


def repair_one(item: dict) -> dict:
    cid = item.get('id', '?')
    desc = item.get('description', '').strip()
    ass = item.get('assessment_prompt', '').strip()

    # 1. 修 desc
    desc = fix_banned(desc)
    desc = smart_truncate_desc(desc)
    if len(desc) < 60 and item.get('_orig_content'):
        # 用 content_req 补一句
        extra = item['_orig_content'][:80]
        desc = (desc + extra)[:100]

    # 2. 修 ass
    ass = fix_banned(ass)

    # 标准化: real newlines → literal \\n (2 chars: backslash + n)
    ass = ass.replace('\r\n', '\n').replace('\r', '\n')
    ass = ass.replace('\n', chr(92) + 'n')  # 直接 replace, 不用 re.sub

    # 拆 3 段 (按 literal \\n)
    parts = ass.split(chr(92) + 'n')  # 2-char split
    parts = [p.strip() for p in parts if p.strip()]

    PADS_Q = [
        "{{name}}能不能举出一个例子?",
        "如果{{name}}答不上来, 怎么提示?",
        "{{name}}能不能换一种说法解释?",
        "{{name}}会不会主动问为什么?",
        "{{name}}在什么场景下会用上?",
        "{{name}}能不能跟朋友讲清楚?",
        "{{name}}做错了, 怎么自己发现?",
        "{{name}}能不能反过来给别人出题?",
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

    # 长度
    if len(ass) > 220:
        ass = smart_truncate_ass(ass)
    if len(ass) < 150:
        ass = pad_assessment(ass)

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
    if ass.count('\\n') < 2:
        issues.append(f'nl_count={ass.count(chr(92)+"n")}')
    for b in BANNED:
        if b in desc or b in ass:
            issues.append(f'禁词[{b}]')
    return issues


# ---- 主流程 ----
def main():
    BATCH_SIZE = 30
    all_results = dict(done)
    all_to_process = [c for c in data if c['id'] not in all_results]
    print(f'待处理: {len(all_to_process)} 概念', flush=True)

    batches = []
    for i in range(0, len(all_to_process), BATCH_SIZE):
        batches.append(all_to_process[i:i+BATCH_SIZE])
    print(f'分 {len(batches)} 批', flush=True)

    t0 = time.time()
    for bi, batch in enumerate(batches):
        print(f'\n=== Batch {bi+1}/{len(batches)} ({len(batch)} 概念) ===', flush=True)
        for c in batch:
            c['_orig_content'] = c.get('content_req', '')
        bt = time.time()
        text = call_llm(batch)
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
                    single_text = call_llm([c])
                    single = parse_json(single_text)
                    if single and single[0].get('id') == c['id']:
                        single[0]['_orig_content'] = c['_orig_content']
                        single[0] = repair_one(single[0])
                        issues = validate(single[0])
                        if not issues:
                            repaired.append({'id': single[0]['id'], 'description': single[0]['description'], 'assessment_prompt': single[0]['assessment_prompt']})
                        else:
                            fails.append((c['id'], issues))
                    else:
                        fails.append((c['id'], ['parse fail'] + issues))
            else:
                fails.append((c['id'], ['not in LLM output']))

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
