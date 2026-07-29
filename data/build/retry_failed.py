#!/usr/bin/env python3
"""
V4.0.1 重试脚本 — 14 parse 失败概念
原因: build_p2.py max_tokens=2500 + 长 prompt 容易截断
修法: max_tokens=4000 + 简化 prompt (只 title + 短 desc + 3 key_points)
"""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent.parent
SRC = ROOT / 'data' / 'graph' / 'all_v3.7_p1.json'
DST = ROOT / 'data' / 'exercises' / 'exercises_v1.json'
SETTINGS = Path.home() / '.claude' / 'settings.json'

LLM_URL = 'https://api.minimaxi.com/anthropic/v1/messages'
LLM_MODEL = 'MiniMax-M3'
LLM_MAX_TOKENS = 4000

# 14 parse 失败概念
PARSE_FAILED = [
    'M_G3_ST_08',       # 数据意识与应用
    'P_P3_07',          # 光的折射
    'ML_ML_G9_03',      # 走向共同富裕
    'SC_S2_LS_03',      # 人体的呼吸/消化/循环
    'SC_S2_TE_01',      # 设计与制作
    'SC_S3_MS_03',      # 能量的多种形式
    'CN_G56_WR_02',     # 写人: 典型事例
    'ML_G79_LG_01',     # 法治社会
    'ML_G79_RE_02',     # 历史责任
    'ML_G79_GR_01',     # 人生规划
    'SC_G56_LS_03',     # 生命的共同特征
    'SC_G56_LS_07',     # 常见传染病
    'IT_G56_DA_07',     # 数据清洗
    'IT_G79_AI_02',     # AI 项目实践
]


def get_api_key():
    with open(SETTINGS) as f:
        s = json.load(f)
    return s.get('env', {}).get('ANTHROPIC_AUTH_TOKEN', '')


def call_llm(prompt, api_key, max_retries=3):
    req = urllib.request.Request(
        LLM_URL,
        data=json.dumps({
            'model': LLM_MODEL,
            'max_tokens': LLM_MAX_TOKENS,
            'messages': [{'role': 'user', 'content': prompt}],
        }).encode('utf-8'),
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        method='POST'
    )
    last_err = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read())
                return data['content'][0]['text']
        except urllib.error.HTTPError as e:
            last_err = f'HTTP {e.code}: {e.read()[:200].decode("utf-8","replace")}'
        except Exception as e:
            last_err = f'{type(e).__name__}: {e}'
        time.sleep(2 + attempt * 2)
    raise RuntimeError(f'LLM 失败 3 次: {last_err}')


def build_short_prompt(node):
    """简化 prompt, 避免长 description 撑爆 tokens."""
    title = node.get('title', '')
    desc = (node.get('description') or '')[:200]
    kp = node.get('key_points', [])[:3]
    return f"""出 K12 题目, 概念: {title}
{desc}
要点: {json.dumps(kp, ensure_ascii=False)}

出 5 道题 (1 选择 + 1 填空 + 3 简答).

严格 JSON 格式:
{{
  "exercises": [
    {{"type":"multiple_choice","question":"...","options":["A. ...","B. ...","C. ...","D. ..."],"answer":"A","explanation":"..."}},
    {{"type":"fill_blank","question":"...____...","answer":["关键词"],"explanation":"..."}},
    {{"type":"short_answer","question":"...","answer":"...","explanation":"..."}},
    {{"type":"short_answer","question":"...","answer":"...","explanation":"..."}},
    {{"type":"short_answer","question":"...","answer":"...","explanation":"..."}}
  ]
}}"""


def parse_llm(text):
    """更宽松的 parse: 处理 ```json...``` 或裸 JSON"""
    text = text.strip()
    if '```' in text:
        for p in text.split('```'):
            p = p.strip()
            if p.startswith('json'):
                p = p[4:].strip()
            if p.startswith('{') and p.endswith('}'):
                try:
                    return json.loads(p)
                except json.JSONDecodeError:
                    continue
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            # 截断修复: 找最后一个 } 截断
            t = text[start:end+1]
            last = t.rfind('},{')
            if last > 0:
                try:
                    return json.loads(t[:last+1] + ']}')
                except json.JSONDecodeError:
                    pass
    return None


def process(node, api_key):
    """1 LLM call 5 题."""
    prompt = build_short_prompt(node)
    text = call_llm(prompt, api_key)
    parsed = parse_llm(text)
    if not parsed:
        return None
    exs = parsed.get('exercises', [])
    if len(exs) < 5:
        return None

    # 分配 id
    cid = node['id']
    # 找当前最大 NNN
    start_num = 1
    # 全部走 LLM 槽 _001-_005 (因为之前都失败了, 不占用)
    out = []
    for i, ex in enumerate(exs[:5]):
        ex_id = f"EX_{cid}_{i+1:03d}"
        et = ex.get('type', 'unknown')
        if et not in ('multiple_choice', 'fill_blank', 'short_answer'):
            et = 'short_answer'
        item = {
            'id': ex_id,
            'concept_id': cid,
            'type': et,
            'difficulty': ex.get('difficulty', node.get('difficulty', 3)),
            'question': ex.get('question', '').strip(),
            'answer': ex.get('answer', ''),
            'explanation': ex.get('explanation', '').strip(),
            'bloom': '',
            'is_real_exam': False,
            'tags': [],
        }
        if et == 'multiple_choice':
            opts = ex.get('options', [])
            if not isinstance(opts, list) or len(opts) != 4:
                continue
            item['options'] = [str(o).strip() for o in opts]
            ans = ex.get('answer', '')
            if ans not in ('A', 'B', 'C', 'D'):
                continue
        elif et == 'fill_blank':
            ans = ex.get('answer', [])
            if isinstance(ans, str):
                ans = [ans]
            item['answer'] = [str(a).strip() for a in ans]
        if not item['question'] or not item['explanation']:
            continue
        out.append(item)
    if len(out) < 4:  # 至少 4 道题 OK 才入库
        return None
    return out


def main():
    api_key = get_api_key()
    if not api_key:
        print('❌ 找不到 ANTHROPIC_AUTH_TOKEN')
        return

    g = json.load(open(SRC))
    nodes_by_id = {n['id']: n for n in g['nodes']}

    out_data = json.load(open(DST))
    existing_ids = {ex['id'] for ex in out_data.get('exercises', [])}

    log = []
    n_ok = 0
    n_fail = 0
    start = time.time()
    for i, cid in enumerate(PARSE_FAILED):
        if cid not in nodes_by_id:
            print(f'⚠️ {cid} 不在图谱里')
            continue
        n = nodes_by_id[cid]
        rate = (i + 1) / max(time.time() - start, 0.1)
        eta = (len(PARSE_FAILED) - i - 1) / max(rate, 0.001) / 60
        print(f'[{i+1}/{len(PARSE_FAILED)}] {cid} ({n["title"][:20]}) {rate:.3f}/s, ETA {eta:.0f}min', flush=True)
        out = process(n, api_key)
        if out is None or len(out) < 4:
            log.append(f'❌ {cid}: 失败')
            n_fail += 1
        else:
            # 删除原 _001-_005 (如果有, 可能是 V4.0.0 时代的老题)
            prefix = f"EX_{cid}_"
            out_data['exercises'] = [e for e in out_data['exercises'] if not e['id'].startswith(prefix)]
            existing_ids = {e['id'] for e in out_data['exercises']}
            # 加新题
            for ex in out:
                out_data['exercises'].append(ex)
                existing_ids.add(ex['id'])
            log.append(f'✅ {cid}: {len(out)} 道题')
            n_ok += 1

        # 写盘
        with open(DST, 'w', encoding='utf-8') as f:
            json.dump(out_data, f, ensure_ascii=False, indent=2)

    log_path = DST.parent / (DST.stem + '.log')
    with open(log_path, 'a') as f:
        f.write('\n=== retry_failed 14 parse 失败 ===\n')
        f.write('\n'.join(log))
        f.write('\n')
    print(f'\n✅ 成功 {n_ok}/14, 失败 {n_fail}/14, 写到 {DST}')
    print(f'总题数: {len(out_data["exercises"])}')


if __name__ == '__main__':
    main()
