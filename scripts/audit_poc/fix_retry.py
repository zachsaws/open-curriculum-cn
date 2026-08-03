#!/usr/bin/env python3
"""Step 3 retry: 43 失败题重跑 (max_tokens 5500)"""
import json
import os
import sys
import time
import urllib.request
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts' / 'audit_poc'))
from audit_fix import V1_FIX_PROMPT

EXERCISES = ROOT / 'web/data/exercises.json'
OUT = ROOT / 'scripts/audit_poc/exercises_fixed.json'
PROGRESS = ROOT / 'scripts/audit_poc/fix_progress.json'

MODEL_MAX_TOKENS = 8000  # 加大
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
                stop = d.get('stop_reason', '')
                for c in d.get('content', []):
                    if c.get('type') == 'text':
                        text = c.get('text', '')
                        if stop == 'max_tokens':
                            return text, 'WARN: max_tokens 截断'
                        return text, None
                return None, 'empty content'
        except urllib.error.HTTPError as e:
            err = f'HTTP {e.code}: {e.reason}'
            if e.code in (429, 500, 502, 503, 504, 529):
                backoff = min(30, 3 * (2 ** attempt))
                print(f'  [retry {attempt+1}] {err} → sleep {backoff}s', flush=True)
                time.sleep(backoff)
                continue
            return None, err
        except Exception as e:
            err = f'{type(e).__name__}: {e}'
            backoff = min(15, 2 * (2 ** attempt))
            print(f'  [retry {attempt+1}] {err} → sleep {backoff}s', flush=True)
            time.sleep(backoff)
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

    prompt = V1_FIX_PROMPT.format(
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
        return None, f'parse failed (raw: {text[:200]})'
    if not fixed.get('question') or not fixed.get('answer'):
        return None, 'missing question or answer'
    return fixed, None


def main():
    # 加载 43 失败题 (从 log 提取)
    import subprocess
    log = open('/tmp/fix_full.log').read()
    fail_ids = []
    for line in log.split('\n'):
        m = re.search(r'\[\d+/\d+\] (\S+) ✗', line)
        if m:
            qid = m.group(1)
            if qid not in fail_ids:
                fail_ids.append(qid)
    print(f'43 失败题: {len(fail_ids)}')

    # 加载原题
    exs = json.loads(EXERCISES.read_text())['exercises']
    ex_by_id = {e['id']: e for e in exs}

    # 加载 quality
    quality = json.load(open(ROOT / 'web/data/exercises_quality.json'))['quality']

    # 加载 fixed 进度 (已成功的 235)
    fixed = json.load(open(PROGRESS))['fixed']
    print(f'已成功: {len(fixed)}')

    graph = json.load(open(ROOT / 'web/data/graph.json'))
    cid2title = {n['id']: n.get('title', '') for n in graph['nodes']}

    # 重跑 43 题
    t0 = time.time()
    success = 0
    failed = 0
    for i, qid in enumerate(fail_ids):
        ex = ex_by_id.get(qid)
        if not ex:
            print(f'  [{i+1}/{len(fail_ids)}] {qid} ✗ 原题找不到')
            continue
        # 找 audit
        audit = quality.get(qid, {})
        if not audit:
            for k, v in quality.items():
                if v.get('concept_id') == ex['concept_id'] and v.get('risk') == 'high':
                    audit = v
                    break
        if not audit:
            audit = {'risk': 'high', 'fix_suggestion': '无具体建议'}

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
            nc = len(result.get('changed', []))
            print(f'  [{i+1}/{len(fail_ids)}] {qid} ✓ {nc} 改动', flush=True)
        else:
            failed += 1
            print(f'  [{i+1}/{len(fail_ids)}] {qid} ✗ {err[:80]}', flush=True)

        if (i + 1) % 10 == 0 or i == len(fail_ids) - 1:
            elapsed = time.time() - t0
            rate = (i + 1) / max(elapsed, 1) * 60
            eta = (len(fail_ids) - i - 1) / max(rate / 60, 0.001)
            print(f'  === {i+1}/{len(fail_ids)} 成功 {success} 失败 {failed} | {rate:.1f} 题/min | ETA {eta:.0f} min ===', flush=True)
            # save
            tmp = PROGRESS.with_suffix('.tmp')
            tmp.write_text(json.dumps({
                'updated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'count': len(fixed),
                'fixed': fixed,
            }, ensure_ascii=False, indent=2))
            tmp.replace(PROGRESS)

        time.sleep(BATCH_SLEEP)

    print(f'\n=== Retry 完成: 成功 {success} 失败 {failed}, 总耗时 {(time.time()-t0)/60:.1f} min ===')

    # 写最终结果
    with open(OUT, 'w') as f:
        json.dump(fixed, f, ensure_ascii=False, indent=2)
    print(f'输出: {OUT} (总 {len(fixed)} 题)')


if __name__ == '__main__':
    main()
