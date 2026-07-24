"""
V3.3.5 Build script: 给 1 学科加 3 字段 (real_examples / common_mistakes / teaching_activity).

用法: python3 build.py <subject>
subject ∈ {english, history, physics, science, morality_law}

借鉴 V3.3.4 chemistry/math 经验:
- 5 概念/批 (稳定)
- 单条重试 + 二次单条
- parse_json 容错 (CJK 邻接正则 quote 配对)
- 真换行 → 字面 \\n 用 .replace
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

# Token
with open('/Users/tianxiang/.claude/settings.json') as f:
    settings = json.load(f)
TOKEN = settings['env']['ANTHROPIC_AUTH_TOKEN']
BASE_URL = 'https://api.minimaxi.com/anthropic/v1/messages'


SUBJECT = sys.argv[1] if len(sys.argv) > 1 else 'english'
if SUBJECT not in SUBJECTS:
    print(f'Usage: python3 build.py <subject> where subject ∈ {list(SUBJECTS.keys())}')
    sys.exit(1)

CFG = SUBJECTS[SUBJECT]
INPUT = CFG['input_path']
OUTPUT = CFG['output_path']
SYSTEM = CFG['system_prompt']
NAME = CFG['name']

TEXTBOOK_KW_SUBJ = TEXTBOOK_KW[SUBJECT]
SUBJECT_KW_SUBJ = SUBJECT_KW[SUBJECT]
MISTAKE_KW_SUBJ = MISTAKE_KW[SUBJECT]
PADS_SUBJ = PADS[SUBJECT]

print(f'=== V3.3.5 Build: {NAME} ({SUBJECT}) ===')
print(f'  Input:  {INPUT}')
print(f'  Output: {OUTPUT}')
print(f'  Total:  {CFG["total_count"]} 概念')


def call_llm(concepts: list[dict]) -> str:
    """调 LLM 一次, 返回 raw text."""
    user_lines = [f'【重要】这是 {NAME} 学科的概念, 课例/错误/活动必须围绕 {NAME} 学科的教材、教具、典型错误来写, 不要写成其他学科.\n',
                  f'请为以下 {len(concepts)} 个{NAME}概念各生成 real_examples + common_mistakes + teaching_activity:\n']
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
    user_lines.append(f'\n请输出严格 JSON 数组, 每条含 id, real_examples (60-120 字含教材版本/章节), common_mistakes (60-120 字含具体错法), teaching_activity (60-120 字含教具/操作).')
    user_prompt = '\n'.join(user_lines)

    body = json.dumps({
        'model': 'MiniMax-M3',
        'max_tokens': 16000,
        'system': SYSTEM,
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
    """从 LLM 输出里解析 JSON 数组, 容错修."""
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
    """智能截断到 max_len, 优先在「。」/「;」「,」「;」处断开."""
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
    """补足到 min_len, 按字段类型用不同 PADS. 拼接在第一个「。」之后."""
    if len(s) >= min_len:
        return s
    pads = PADS_SUBJ.get(field, ['老师可以多设计几组变式让孩子练。'])
    pad = pads[len(s) % len(pads)]
    cut = s.rfind('。')
    if cut == -1:
        return s + pad
    return s[:cut+1] + pad


def has_textbook(s: str) -> bool:
    for kw in TEXTBOOK_KW_SUBJ:
        if kw in s:
            return True
    if re.search(r'第\s*\d+\s*单元', s):
        return True
    if re.search(r'Unit\s*\d+', s, re.IGNORECASE):
        return True
    if re.search(r'第\s*\d+\s*课', s):
        return True
    if re.search(r'第\s*\d+\s*节', s):
        return True
    if re.search(r'第\s*\d+\s*章', s):
        return True
    return False


def has_mistake_verb(s: str) -> bool:
    for kw in MISTAKE_KW_SUBJ:
        if kw in s:
            return True
    return False


def has_teaching_action(s: str) -> bool:
    for kw in SUBJECT_KW_SUBJ:
        if kw in s:
            return True
    return False


def repair_one(item: dict) -> dict:
    """对一条记录做 3 字段的 mechanical repair."""
    for field in ['real_examples', 'common_mistakes', 'teaching_activity']:
        s = item.get(field, '').strip()
        s = fix_banned(s)
        s = fix_char_displace(s)
        # 移除真实换行 (字段内不换行)
        s = s.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
        s = re.sub(r'  +', ' ', s)
        s = re.sub(r'。\s*。', '。', s)
        # 长度处理
        if len(s) > 120:
            s = smart_truncate(s, 120)
        if len(s) < 60:
            s = smart_pad_with_field(s, field, 60)
        item[field] = s
    return item


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


# ---- 主流程 ----
def main():
    BATCH_SIZE = 5
    data = json.load(open(INPUT))
    print(f'Total: {len(data)} 概念', flush=True)

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
                                # 二次单条
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

    print(f'\n=== Build 完成 ===', flush=True)
    print(f'总产出: {len(all_results)} / {len(data)}', flush=True)
    print(f'失败: {len([c for c in data if c["id"] not in all_results])}', flush=True)
    print(f'用时: {(time.time()-t0)/60:.1f} min', flush=True)


if __name__ == '__main__':
    main()
