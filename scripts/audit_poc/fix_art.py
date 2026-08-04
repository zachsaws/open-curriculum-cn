#!/usr/bin/env python3
"""V4.0.6 D: art 学科定制改写 (7 题 + art 全 high 重跑)"""
import json
import os
import sys
import time
import urllib.request
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts' / 'audit_poc'))
from audit_fix_art import V1_FIX_ART_PROMPT

EXERCISES = ROOT / 'web/data/exercises.json'
QUALITY = ROOT / 'web/data/exercises_quality.json'
REGRESSION = ROOT / 'web/data/exercises_quality_regression.json'
OUT = ROOT / 'scripts/audit_poc/exercises_fixed_art.json'
PROGRESS = ROOT / 'scripts/audit_poc/art_fix_progress.json'

MODEL_MAX_TOKENS = 8000
BATCH_SLEEP = 3.0


def get_llm_config():
    cfg = json.load(open(os.path.expanduser('~/.claude/settings.json')))['env']
    return cfg['ANTHROPIC_AUTH_TOKEN'], cfg['ANTHROPIC_BASE_URL']


def call_llm(prompt, max_retries=5):
    key, base = get_llm_config()
    url = f'{base}/v1/messages'
    data = json.dumps({
        'model': 'MiniMax-M3',
        'max_tokens': MODEL_MAX_TOKENS,
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode()
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, method='POST', headers={
                'x-api-key': key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            }, data=data)
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read().decode()
                d = json.loads(body)
                for c in d.get('content', []):
                    if c.get('type') == 'text':
                        return c.get('text', ''), None
                return None, 'empty'
        except urllib.error.HTTPError as e:
            err = f'HTTP {e.code}'
            if e.code in (429, 500, 502, 503, 504, 529):
                backoff = min(30, 3 * (2 ** attempt))
                time.sleep(backoff)
                continue
            return None, err
        except Exception as e:
            time.sleep(min(15, 2 * (2 ** attempt)))
    return None, 'max retries'


def extract_json(text):
    if not text: return None
    m = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    m = re.search(r'(\{.*\})', text, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    return None


def fix_one(ex, audit, cid2title):
    cid = ex['concept_id']
    title = cid2title.get(cid, '')
    options = ex.get('options', []) or []
    options_str = '\n'.join(options) if options else 'N/A'

    prompt = V1_FIX_ART_PROMPT.format(
        question=ex.get('question', ''),
        concept_id=cid,
        concept_title=title,
        qtype=ex.get('type', ''),
        difficulty=ex.get('difficulty', '?'),
        bloom=ex.get('bloom', ''),
        options=options_str,
        answer=str(ex.get('answer', '')),
        explanation=ex.get('explanation', ''),
        answer_correct=audit.get('answer_correct'),
        question_clear=audit.get('question_clear'),
        options_quality=audit.get('options_quality'),
        difficulty_match=audit.get('difficulty_match'),
        difficulty_suggested=audit.get('difficulty_suggested'),
        concept_match=audit.get('concept_match'),
        fix_suggestion=audit.get('fix_suggestion') or '无',
    )
    text, err = call_llm(prompt)
    if not text:
        return None, err
    fixed = extract_json(text)
    if not fixed:
        return None, 'parse failed'
    if not fixed.get('question') or not fixed.get('answer'):
        return None, 'missing fields'
    return fixed, None


def main():
    exs = json.loads(EXERCISES.read_text())['exercises']
    ex_by_id = {e['id']: e for e in exs}
    print(f'总题数: {len(exs)}')

    # 找 art 学科所有 high 题 (V4.0.6 Step 2 评估)
    quality = json.loads(QUALITY.read_text())['quality']
    art_high = [(qid, r) for qid, r in quality.items()
                if r.get('risk') == 'high' and r.get('concept_id', '').startswith('ART_')]
    print(f'art high 总数: {len(art_high)}')

    # 排除已成功的 (V4.0.6 Step 3 改写 + regression 后变 success 的)
    regression = json.loads(REGRESSION.read_text()) if REGRESSION.exists() else {}
    art_qids = [qid for qid, _ in art_high]
    art_remaining = []
    for qid in art_qids:
        if qid in ex_by_id:
            # 跳过已 auto_fix_status=success
            e = ex_by_id[qid]
            if e.get('_auto_fix_status') == 'success':
                continue
            art_remaining.append(qid)
    print(f'art 待 art-prompt 改写: {len(art_remaining)} (排除 success)')

    # 加载 progress
    fixed = {}
    if PROGRESS.exists():
        try:
            fixed = json.loads(PROGRESS.read_text()).get('fixed', {})
        except:
            fixed = {}
    print(f'已 art 改写: {len(fixed)}')

    todo = [qid for qid in art_remaining if qid not in fixed]
    print(f'待 art 改写: {len(todo)}')

    if not todo:
        print('全部已 art 改完')
    else:
        graph = json.load(open(ROOT / 'web/data/graph.json'))
        cid2title = {n['id']: n.get('title', '') for n in graph['nodes']}

        t0 = time.time()
        success = 0
        failed = 0
        for i, qid in enumerate(todo):
            ex = ex_by_id[qid]
            # 找 audit
            audit = quality.get(qid, {})
            if not audit:
                cid = ex['concept_id']
                for k, v in quality.items():
                    if v.get('concept_id') == cid and v.get('risk') == 'high':
                        audit = v
                        break
            if not audit:
                audit = {'risk': 'high', 'fix_suggestion': 'art 学科无具体建议'}

            result, err = fix_one(ex, audit, cid2title)
            if result:
                fixed[qid] = {
                    'q_id': qid,
                    'concept_id': ex['concept_id'],
                    'type': ex['type'],
                    'original_question': ex.get('question', '')[:100],
                    'original_answer': str(ex.get('answer', ''))[:30],
                    'fixed_question': result.get('question', ''),
                    'fixed_options': result.get('options', []),
                    'fixed_answer': result.get('answer', ''),
                    'fixed_explanation': result.get('explanation', ''),
                    'fixed_difficulty': result.get('difficulty'),
                    'fixed_bloom': result.get('bloom'),
                    'fixed_concept_id': result.get('concept_id', ex['concept_id']),
                    'changed': result.get('changed', []),
                    'note': result.get('note', ''),
                }
                success += 1
                print(f'  [{i+1}/{len(todo)}] {qid} ✓ {len(result.get("changed", []))} 改动', flush=True)
            else:
                failed += 1
                print(f'  [{i+1}/{len(todo)}] {qid} ✗ {err}', flush=True)

            if (i + 1) % 5 == 0 or i == len(todo) - 1:
                elapsed = time.time() - t0
                rate = (i + 1) / max(elapsed, 1) * 60
                eta = (len(todo) - i - 1) / max(rate / 60, 0.001)
                print(f'  === {i+1}/{len(todo)} 成功 {success} 失败 {failed} | {rate:.1f} 题/min | ETA {eta:.0f} min ===', flush=True)
                tmp = PROGRESS.with_suffix('.tmp')
                tmp.write_text(json.dumps({
                    'updated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'count': len(fixed),
                    'fixed': fixed,
                }, ensure_ascii=False, indent=2))
                tmp.replace(PROGRESS)

            time.sleep(BATCH_SLEEP)

        print(f'\n=== Art 改写完成: 成功 {success} 失败 {failed}, 总耗时 {(time.time()-t0)/60:.1f} min ===')

    with open(OUT, 'w') as f:
        json.dump(fixed, f, ensure_ascii=False, indent=2)
    print(f'输出: {OUT} (总 {len(fixed)} 题)')


if __name__ == '__main__':
    main()
