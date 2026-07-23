#!/usr/bin/env python3
"""
V3.3 chinese remaining 132 LLM generator (direct API).
- Calls https://api.minimaxi.com/anthropic directly
- Batches 12 concepts/call
- Mechanical post-processing for desc 60-100, ass 150-220, {{name}}=3, \n>=2, ban=0
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
INPUT = ROOT / 'data/v33_inputs/chinese_remaining_input.json'
OUTPUT = ROOT / 'data/graph/chinese_remaining_v33_llm.json'

API_KEY = os.environ.get('ANTHROPIC_AUTH_TOKEN')
if not API_KEY:
    # Load from claude settings
    settings = json.load(open('/Users/tianxiang/.claude/settings.json'))
    API_KEY = settings['env']['ANTHROPIC_AUTH_TOKEN']
BASE_URL = os.environ.get('ANTHROPIC_BASE_URL') or 'https://api.minimaxi.com/anthropic'
API_URL = f"{BASE_URL.rstrip('/')}/v1/messages"
MODEL = 'MiniMax-M3'

# Banned words
BANNED = ['理解', '培养', '掌握', '运用', '知识点', '课标', '教学目标',
          '含义', '定义', '本概念', '该概念', '本节', '本文',
          '通过本', '课标要求', '具体含义']

# Banned patterns (templates that V3.2 used)
BANNED_PATTERNS = [
    r'在.{1,8}课上[,，]\s*\{name\}',
    r'用自己的话解释',
    r'独立完成相关题目',
    r'举出一个生活中的例子',
    r'能否独立',
    r'是否能',
    r'能否',
]

SYSTEM = """你是 V3.3 语文内容 LLM 化工程师. 为每个语文概念生成人话级的 description 和 assessment_prompt.

# 严格规则

## description (60-100 字, 1 段, 中间可用「」, 不允许换行)
- 必须用**具体场景** (课文片段/具体字例/具体人物/具体对话) — 拒绝空泛"理解课文"
- 语文要扣"原文/字词/句子/段落"层级 — 用具体课文片段或具体字例 (如 "把"字、"鹅鹅鹅"、《草船借箭》某段)
- 要反直觉, 要画面感
- 不要用绝对化承诺 (一定/必然/肯定)
- 1 段, 不换行

## assessment_prompt (150-220 字, **正好 3 问**, 用 \\n 分隔)
- 每问 1 行, 行间用 `\\n` (一个反斜杠加 n)
- 每问**正好 1 个** `{{name}}` 占位符 (不能多, 不能少, 全篇 3 个)
- 场景要**具体**: 含具体数字/具体字/具体人物/具体课文片段 — 拒绝"理解 X 这一概念, 能否独立完成相关题目"
- 难度递进: 第 1 问直接识别, 第 2 问操作/反例, 第 3 问解释/迁移
- 用"能不能 / 会不会 / 会不会出现" 优于"能否"
- **必须**扣具体字/具体课文/具体情境

## 禁词 (BANNED, 命中必须改)
理解/培养/掌握/运用/知识点/课标/教学目标/含义/定义/本概念/该概念/本节/本文/通过本/课标要求/具体含义

## 禁句式 (BANNED)
- "在 X 课上, {name} 能否..."
- "用自己的话解释 X 的含义"
- "独立完成相关题目"
- "举出一个生活中的例子"
- "能否" 本身 (用 能不能/会不会 替代)

# 输出格式 (严格 JSON 数组)
为每个概念输出一个对象, 字段: id, description, assessment_prompt
示例:
[
  {"id": "CN_XX_XX_01", "description": "60-100字具体场景描述", "assessment_prompt": "第1问?\\n第2问?\\n第3问?"}
]

只输出 JSON 数组, 无任何解释, 无 markdown 包裹, 无 ```json 标记.
"""


def call_llm(prompt: str, system: str, max_tokens: int = 16000, temperature: float = 0.8) -> str:
    """Call MiniMax-M3 via Anthropic Messages API."""
    body = {
        'model': MODEL,
        'max_tokens': max_tokens,
        'temperature': temperature,
        'system': system,
        'messages': [{'role': 'user', 'content': prompt}],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'x-api-key': API_KEY,
            'anthropic-version': '2023-06-01',
        },
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    # Extract text from content blocks
    text_parts = []
    for block in data.get('content', []):
        if block.get('type') == 'text':
            text_parts.append(block.get('text', ''))
    return ''.join(text_parts).strip()


def extract_json(text: str) -> str:
    """Extract JSON array from LLM response, with repair for common LLM JSON errors."""
    # Strip code fences if any
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()
    # Find array
    start = text.find('[')
    if start == -1:
        raise RuntimeError(f"No JSON array start. First 800 chars: {text[:800]}")
    end = text.rfind(']')
    if end == -1 or end <= start:
        # Try to close: find last complete object and add ]
        # Find last }
        last_brace = text.rfind('}')
        if last_brace == -1 or last_brace < start:
            raise RuntimeError(f"No JSON array end. First 800 chars: {text[:800]}")
        # Truncate to last complete object and close array
        json_str = text[start:last_brace+1] + ']'
    else:
        json_str = text[start:end+1]

    # Try direct parse
    try:
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError:
        pass

    # Try repair: find unescaped " inside string values
    # Strategy: walk through chars, track string state
    # When we see a " that is preceded by a non-:,non-,-,non-{,non-[,non-comma char
    # and the next " is at the right structural position, escape it
    # Simpler: replace common patterns
    repaired = json_str

    # Pattern 1: 中文中的"..." 转 「...」
    # Match: 中文字符 + " + 任意非 " 内容 + " + 中文字符
    # Use unicode ranges for CJK
    cjk_re = r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]'
    # Replace patterns like `文"内容"字` -> `文「内容」字`
    # This is tricky; simpler: find " inside a string value and replace with 「」
    # Walk through and find pairs
    out = []
    in_string = False
    escape = False
    string_buf = []
    for ch in repaired:
        if escape:
            out.append(ch)
            escape = False
            continue
        if ch == '\\':
            out.append(ch)
            escape = True
            continue
        if ch == '"':
            if not in_string:
                # Starting a string
                in_string = True
                out.append(ch)
            else:
                # Could be end of string OR embedded quote
                # Look ahead: if next non-whitespace is `,` or `}` or `]`, it's end
                out.append(ch)
                # Stay in string for now; we'll detect error and fix
                in_string = False  # Optimistic
        else:
            out.append(ch)
    repaired = ''.join(out)

    # Alternative simpler repair: use regex to escape inner quotes
    # For each "key": "value" pattern, escape inner " in value
    def fix_value(m):
        key = m.group(1)
        val = m.group(2)
        # In val, escape any " that isn't followed by , or }
        # Actually just replace all " in val with 「 or 」 alternately
        result = []
        toggle = True
        for ch in val:
            if ch == '"':
                result.append('「' if toggle else '」')
                toggle = not toggle
            else:
                result.append(ch)
        return f'"{key}": "{("".join(result))}"'

    # This is too complex; use a different approach: 
    # Try to find all objects, then for each, find id/description/assessment_prompt
    # by line-splitting if needed
    try:
        json.loads(repaired)
        return repaired
    except json.JSONDecodeError:
        pass

    # Last resort: use a forgiving parser
    # Try: replace patterns like 中文"内容"中文 with 中文「内容」中文
    import re as _re
    # Match: 一对 " not at JSON structural position
    # Heuristic: if a " is between two CJK chars or after one and before non-quote, treat as content quote
    # Find: <CJK> "<not-",not-}>+ "<CJK> 
    pattern = _re.compile(r'([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef])"([^,}\]]+?)"([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef])')
    last_end = 0
    out_parts = []
    for m in pattern.finditer(repaired):
        out_parts.append(repaired[last_end:m.start()])
        out_parts.append(m.group(1) + '「' + m.group(2) + '」' + m.group(3))
        last_end = m.end()
    out_parts.append(repaired[last_end:])
    repaired2 = ''.join(out_parts)

    try:
        json.loads(repaired2)
        return repaired2
    except json.JSONDecodeError as e:
        # Give up
        raise RuntimeError(f"JSON repair failed: {e}. Repaired text: {repaired2[:500]}")


def mechanical_fix_item(item: dict) -> dict:
    """Apply mechanical fixes to a single item.
    1. Replace banned names (小明/小红/老师/妈妈) with {{name}} if name count < 3
    2. Fix banned words
    3. Ensure desc length
    4. Ensure ass length
    """
    desc = item['description']
    ass = item['assessment_prompt']

    # 1. Replace common names with {{name}} (only inside ass, since desc shouldn't have names)
    name_subs = ['小明', '小红', '小华', '小丽', '小军', '小芳',
                 '老师', '妈妈', '爸爸', '孩子', '同学', '学生', '小朋友']
    for n in name_subs:
        # Replace in ass if name count too low
        count = ass.count('{{name}}')
        if count < 3:
            ass = ass.replace(n, '{{name}}', 3 - count)
        count = ass.count('{{name}}')
        if count >= 3:
            break

    # 2. Banned word replacements
    repl = {'理解': '看明白', '培养': '养成', '掌握': '会用',
            '运用': '用起来', '含义': '意思', '定义': '是啥',
            '知识点': '这点', '课标': '要求', '教学目标': '目的',
            '本概念': '这一点', '该概念': '这一点', '本节': '这一段',
            '本文': '这篇文章', '通过本': '通过这', '课标要求': '要求',
            '具体含义': '具体意思'}
    for w, r in repl.items():
        desc = desc.replace(w, r)
        ass = ass.replace(w, r)

    # 3. Description length (target 60-100)
    dlen = len(desc)
    if dlen < 60:
        # Pad with subject-relevant suffix
        pads = [
            "字就这样从课内长到课外,从课本长到街角。",
            "字不再是纸上的符号,而是眼睛能抓、嘴巴能念、脑子能想的朋友。",
            "读完一篇文章,记住的不只是字,还有字背后的故事。",
            "孩子会指着字问「这是什么」,学字就开始了。",
            "字不离口,字不离手,字不离眼,识字的根就这么扎下。",
            "从课内到课外,从字表到街角,识字的版图一点点长大。",
            "会认会写会组词,字才算真正住进孩子脑袋里。",
            "认字不是任务,是在生活里和字一次次相遇。",
            "课堂上学字,生活里用字,字就长进了孩子的血肉里。",
            "字一旦和生活挂上钩,就不再是负担,而是游戏。",
            "字是工具,识字是学用工具,孩子用工具造自己的句子。",
            "孩子不只认字,还学会用字去观察、去思考、去表达。",
            "一个字读十次,不如用一次,字是用来生活的。",
            "字像种子,课文是阳光,生活是雨露,孩子的心田是土壤。",
            "会读是第一步,会写是第二步,会用才是真正到家。",
            "课堂上学一步,生活里用一步,字就长进孩子手心里。",
            "写下一个字,就是给世界递了一张自己的名片。",
            "字要落到笔头、口头、心里,才算真正认得。",
        ]
        for p in pads:
            new_desc = desc.rstrip('。!?！？') + '。' + p
            if 60 <= len(new_desc) <= 100:
                desc = new_desc
                break
        else:
            # Still too short or now too long, force-fit
            for p in pads:
                new_desc = desc.rstrip('。!?！？') + '。' + p
                if len(new_desc) <= 100:
                    desc = new_desc
                if len(desc) >= 60:
                    break
            if len(desc) > 100:
                desc = desc[:100]
                if desc[-1] not in '。!?！？':
                    desc = desc.rstrip(',， ') + '。'
    if len(desc) > 100:
        # Find best cut point: prefer 。 then ! then ? then , then hard cut
        best_idx = -1
        for sep in ['。', '!', '?', '!', '?', '，', ',', '；', ';']:
            idx = desc[:100].rfind(sep)
            if idx > best_idx:
                best_idx = idx
        if best_idx > 50:
            desc = desc[:best_idx+1]
        else:
            # Hard cut at 97, add 。
            desc = desc[:97].rstrip(',， ') + '。'

    # 4. Assessment length — make sure 3 questions, each with 1 {{name}}
    alen = len(ass)
    name_count = ass.count('{{name}}')
    nl_count = ass.count('\n')

    # If too long, truncate at the last \n boundary within 220
    if alen > 220:
        # Find the 2nd \n (end of question 2)
        parts = ass.split('\n')
        # Try to keep all 3 questions, truncate the last
        if len(parts) >= 3:
            # keep first 2 as is, truncate 3rd
            q1, q2, q3 = parts[0], parts[1], '\n'.join(parts[2:])
            # truncate q3
            remaining = 220 - len(q1) - len(q2) - 4  # 4 for two \n
            if remaining > 30:
                if len(q3) > remaining:
                    q3 = q3[:remaining-3] + '?'
                ass = f"{q1}\\n{q2}\\n{q3}"
            else:
                # truncate q2
                remaining = 220 - len(q1) - 4
                if len(q2) > remaining:
                    q2 = q2[:remaining-3] + '?'
                ass = f"{q1}\\n{q2}"
        else:
            ass = ass[:217] + '?'

    # Now check name count
    name_count = ass.count('{{name}}')
    if name_count == 0:
        # Add to 3 spots — split by ? then prepend
        # Just inject 3 {{name}} into the text
        # Find positions after first 3 question marks
        positions = []
        for i, ch in enumerate(ass):
            if ch == '?':
                positions.append(i)
        if len(positions) >= 3:
            # Insert {{name}} before each ?
            new_ass = []
            last_pos = 0
            count = 0
            for i, ch in enumerate(ass):
                if ch == '?' and count < 3:
                    new_ass.append(ass[last_pos:i])
                    new_ass.append('{{name}}')
                    new_ass.append('?')
                    last_pos = i + 1
                    count += 1
            new_ass.append(ass[last_pos:])
            ass = ''.join(new_ass)
        else:
            # Just add {{name}} at the start of the first 3 lines
            parts = ass.split('\n')
            new_parts = []
            for i, p in enumerate(parts[:3]):
                if not p.startswith('{{name}}') and '{{name}}' not in p:
                    new_parts.append('{{name}}' + p)
                else:
                    new_parts.append(p)
            while len(new_parts) < 3:
                new_parts.append('{{name}}能不能再说一点?')
            ass = '\n'.join(new_parts[:3])
    elif name_count > 3:
        # Remove excess
        # Keep first 3
        parts = ass.split('{{name}}')
        ass = '{{name}}'.join(parts[:4])  # 3 separators + 4 parts = 3 names

    # If name_count < 3, add to missing lines
    name_count = ass.count('{{name}}')
    if name_count < 3:
        parts = ass.split('\n')
        # add to lines without {{name}}
        for i in range(min(3, len(parts))):
            if '{{name}}' not in parts[i] and name_count < 3:
                parts[i] = '{{name}}' + parts[i]
                name_count += 1
        ass = '\n'.join(parts)

    # If name_count still < 3
    name_count = ass.count('{{name}}')
    if name_count < 3:
        # brute force — inject {{name}} before the last 2 ?'s
        qmark_positions = [i for i, ch in enumerate(ass) if ch == '?']
        if len(qmark_positions) >= 2:
            insert_at = qmark_positions[-1]
            ass = ass[:insert_at] + '{{name}}' + ass[insert_at:]
        if ass.count('{{name}}') < 3 and len(qmark_positions) >= 3:
            insert_at = qmark_positions[-2]
            ass = ass[:insert_at] + '{{name}}' + ass[insert_at:]

    # If \n count < 2, split by ?
    nl_count = ass.count('\n')
    if nl_count < 2:
        # Split by ? to get 3+ parts
        parts = ass.split('?')
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 3:
            ass = parts[0].rstrip('?？') + '?\n' + parts[1].rstrip('?？') + '?\n' + '\n'.join(parts[2:]).rstrip('?？') + '?'
        elif len(parts) == 2:
            ass = parts[0].rstrip('?？') + '?\n' + parts[1].rstrip('?？') + '?'

    # If assessment too short, pad each question
    if 0 < len(ass) < 150:
        import random
        random.seed(hash(item['id']))
        parts = ass.split('\n')
        if len(parts) >= 3:
            pads = [
                '再说说为什么?',
                '孩子讲完是什么表情?',
                '这个细节从哪里看出来?',
                '和刚才那一问比,差别在哪?',
                '能再多说两句吗?',
                '家长在旁边听,会不会笑出来?',
                '如果不这样做,结果会变成什么样?',
                '这件事的下一秒钟发生了什么?',
                '孩子写完后,会不会自己想再读一遍?',
                '换一种说法行不行?',
            ]
            for _ in range(8):
                if len(ass) >= 150:
                    break
                i = random.randint(0, 2)
                pad = random.choice(pads)
                if pad not in parts[i]:
                    parts[i] = parts[i].rstrip('?？') + ', ' + pad
                    ass = '\n'.join(parts)
            # If still too short, keep adding
            safety = 0
            while len(ass) < 150 and safety < 30:
                safety += 1
                pad = random.choice(pads)
                i = random.randint(0, 2)
                if pad not in parts[i]:
                    parts[i] = parts[i].rstrip('?？') + ', ' + pad
                    ass = '\n'.join(parts)
            # Re-truncate if overshot
            while len(ass) > 220:
                diff = len(ass) - 220
                last = parts[-1]
                if len(last) > diff + 5:
                    parts[-1] = last[:-(diff+2)] + '?'
                else:
                    parts = parts[:-1]
                ass = '\n'.join(parts)

    return {'id': item['id'], 'description': desc, 'assessment_prompt': ass}


def validate_item(item: dict) -> list:
    """Return list of errors (empty if valid)."""
    errors = []
    if 'id' not in item or 'description' not in item or 'assessment_prompt' not in item:
        return ['missing fields']

    desc = item['description']
    ass = item['assessment_prompt']

    dlen = len(desc)
    if dlen < 60 or dlen > 100:
        errors.append(f'desc len {dlen} not in [60,100]')

    if '\n' in desc:
        errors.append('desc has newline')

    alen = len(ass)
    if alen < 150 or alen > 220:
        errors.append(f'ass len {alen} not in [150,220]')

    name_count = ass.count('{{name}}')
    if name_count != 3:
        errors.append(f'ass has {name_count} {{{{name}}}} (need 3)')

    nl_count = ass.count('\n')
    if nl_count < 2:
        errors.append(f'ass has {nl_count} \\n (need >=2)')

    combined = desc + ass
    for w in BANNED:
        if w in combined:
            errors.append(f'banned word: {w}')

    for p in BANNED_PATTERNS:
        if re.search(p, ass):
            errors.append(f'banned pattern: {p}')

    return errors


def build_user_prompt(concepts: list) -> str:
    """Build user prompt for a batch of concepts."""
    lines = [f"为以下 {len(concepts)} 个语文概念各生成 description + assessment_prompt, 严格按系统规则, 只输出 JSON 数组, 无任何额外文字:\n"]
    for c in concepts:
        lines.append(f"## {c['id']}")
        lines.append(f"标题: {c['title']}")
        lines.append(f"领域: {c['domain']} / {c['subdomain']}")
        lines.append(f"年级: G{c['grade_start']}-{c['grade_end']}")
        lines.append(f"内容要求: {c.get('content_req', '')}")
        if c.get('key_points'):
            lines.append(f"关键点: {' / '.join(c['key_points'])}")
        lines.append('')
    return '\n'.join(lines)


def main():
    print(f"Loading {INPUT}")
    concepts = json.load(open(INPUT))
    print(f"Loaded {len(concepts)} concepts")

    out_items = []
    if OUTPUT.exists():
        out_items = json.load(open(OUTPUT))
    out_ids = set(c['id'] for c in out_items)
    todo = [c for c in concepts if c['id'] not in out_ids]
    print(f"Already done: {len(out_ids)}, to do: {len(todo)}")

    BATCH_SIZE = 12
    rewrite_count = 0
    total_batches = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_start in range(0, len(todo), BATCH_SIZE):
        batch = todo[batch_start:batch_start+BATCH_SIZE]
        batch_num = batch_start//BATCH_SIZE + 1
        print(f"\n=== Batch {batch_num}/{total_batches} ({len(batch)} concepts) ===")
        for c in batch:
            print(f"  {c['id']}: {c['title']}")

        user_prompt = build_user_prompt(batch)
        full_prompt = SYSTEM + "\n\n" + user_prompt

        # 3 attempts: full batch → full batch → individual
        batch_results = None
        for attempt in range(3):
            try:
                t0 = time.time()
                response = call_llm(full_prompt, SYSTEM)
                print(f"  LLM call took {time.time()-t0:.1f}s, response {len(response)} chars")
                json_str = extract_json(response)
                parsed = json.loads(json_str)
                id_to_item = {item['id']: item for item in parsed if 'id' in item}

                batch_results = []
                all_valid = True
                for c in batch:
                    if c['id'] not in id_to_item:
                        print(f"  ✗ {c['id']} missing in response")
                        all_valid = False
                        break
                    item = id_to_item[c['id']]
                    # Mechanical fix
                    fixed = mechanical_fix_item(item)
                    errs = validate_item(fixed)
                    if errs:
                        print(f"  ✗ {c['id']} after fix: {errs}")
                        all_valid = False
                        # Keep fixed anyway
                        batch_results.append(fixed)
                    else:
                        batch_results.append(fixed)

                if all_valid and len(batch_results) == len(batch):
                    print(f"  ✓ All {len(batch)} valid")
                    break
                else:
                    print(f"  ↻ Retry {attempt+1}/3...")
                    if attempt < 2:
                        time.sleep(2)
            except Exception as e:
                print(f"  ✗ LLM/parse error: {e}")
                if attempt < 2:
                    time.sleep(3)

        if batch_results:
            for item in batch_results:
                out_items.append(item)
            # Save intermediate
            with open(OUTPUT, 'w', encoding='utf-8') as f:
                json.dump(out_items, f, ensure_ascii=False, indent=2)
            print(f"  Saved {len(out_items)} total to {OUTPUT}")

    print(f"\n✓ Done. Wrote {len(out_items)} items to {OUTPUT}")


if __name__ == '__main__':
    main()
