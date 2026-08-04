#!/usr/bin/env python3
"""V4.0.6 B: 全量 difficulty 校准 2654 题"""
import json
import os
import sys
import time
import urllib.request
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts' / 'audit_poc'))
from difficulty_fix import V1_DIFF_PROMPT
from prompts import format_exercise

EXERCISES = ROOT / 'web/data/exercises.json'
QUALITY = ROOT / 'web/data/exercises_quality.json'
PROGRESS = ROOT / 'scripts/audit_poc/diff_progress.json'
OUT = ROOT / 'web/data/exercises_diff.json'

MODEL_MAX_TOKENS = 500  # 单字段, 短输出
BATCH_SLEEP = 3.5  # 撞限速后调更稳


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


def main():
    exs = json.loads(EXERCISES.read_text())['exercises']
    ex_by_id = {e['id']: e for e in exs}
    print(f'总题数: {len(exs)}')

    # 找 difficulty 漂的题 (原 audit difficulty_match=false)
    quality = json.loads(QUALITY.read_text())['quality']
    drift_ids = [qid for qid, r in quality.items() if not r.get('difficulty_match') and qid in ex_by_id]
    print(f'difficulty 漂: {len(drift_ids)}')

    # 加载 progress
    fixed_diff = {}
    if PROGRESS.exists():
        try:
            fixed_diff = json.loads(PROGRESS.read_text()).get('fixed_diff', {})
        except:
            fixed_diff = {}
    print(f'已校准: {len(fixed_diff)}')

    todo = [qid for qid in drift_ids if qid not in fixed_diff]
    print(f'待校准: {len(todo)}')

    if not todo:
        print('全部已校准')
    else:
        t0 = time.time()
        success = 0
        failed = 0
        for i, qid in enumerate(todo):
            ex = ex_by_id[qid]
            options = ex.get('options', []) or []
            options_str = '\n'.join(options) if options else 'N/A'

            prompt = V1_DIFF_PROMPT.format(
                question=ex.get('question', ''),
                qtype=ex.get('type', ''),
                difficulty=ex.get('difficulty', '?'),
                answer=str(ex.get('answer', '')),
                bloom=ex.get('bloom', ''),
                options=options_str,
            )

            text, err = call_llm(prompt)
            if text:
                parsed = extract_json(text)
                if parsed and parsed.get('difficulty'):
                    try:
                        new_d = int(parsed['difficulty'])
                        if 1 <= new_d <= 5:
                            old_d = ex.get('difficulty')
                            fixed_diff[qid] = {
                                'q_id': qid,
                                'old_difficulty': old_d,
                                'new_difficulty': new_d,
                                'reason': parsed.get('reason', ''),
                            }
                            success += 1
                        else:
                            failed += 1
                    except (ValueError, TypeError):
                        failed += 1
                else:
                    failed += 1
            else:
                failed += 1
                if i < 5: print(f'  [{qid}] err: {err}', flush=True)

            if (i + 1) % 50 == 0 or i == len(todo) - 1:
                elapsed = time.time() - t0
                rate = (i + 1) / max(elapsed, 1) * 60
                eta = (len(todo) - i - 1) / max(rate / 60, 0.001)
                print(f'  === {i+1}/{len(todo)} 成功 {success} 失败 {failed} | {rate:.1f} 题/min | ETA {eta:.0f} min ===', flush=True)
                tmp = PROGRESS.with_suffix('.tmp')
                tmp.write_text(json.dumps({
                    'updated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                    'count': len(fixed_diff),
                    'fixed_diff': fixed_diff,
                }, ensure_ascii=False, indent=2))
                tmp.replace(PROGRESS)

            time.sleep(BATCH_SLEEP)

        print(f'\n=== Difficulty 校准完成: 成功 {success} 失败 {failed}, 总耗时 {(time.time()-t0)/60:.1f} min ===')

    # 应用到 exercises
    n_patched = 0
    for qid, f in fixed_diff.items():
        if qid in ex_by_id:
            ex_by_id[qid]['difficulty'] = f['new_difficulty']
            ex_by_id[qid]['_diff_recalibrated_at'] = '2026-08-03'
            ex_by_id[qid]['_diff_old'] = f['old_difficulty']
            n_patched += 1
    print(f'已 patch {n_patched} 题 difficulty')

    # 备份当前版
    import shutil
    shutil.copy(EXERCISES, ROOT / 'web/data/exercises.v4.0.6_diff_pre.json')
    exs['note'] = f'V4.0.6 difficulty 全量校准: {len(fixed_diff)} 题 d 字段重打标'
    with open(EXERCISES, 'w') as f:
        json.dump(exs, f, ensure_ascii=False, indent=2)
    print('写新 exercises.json')

    with open(OUT, 'w') as f:
        json.dump(fixed_diff, f, ensure_ascii=False, indent=2)
    print(f'输出: {OUT}')

    # 报告
    from collections import Counter
    drift = Counter()
    for f in fixed_diff.values():
        drift[(f['old_difficulty'], f['new_difficulty'])] += 1
    print(f'\n=== 难度漂分布 (old → new) ===')
    for (o, n), cnt in sorted(drift.items(), key=lambda x: -x[1]):
        sym = '↑' if n > o else ('↓' if n < o else '=')
        print(f'  {o} → {n} ({sym}): {cnt}')


if __name__ == '__main__':
    main()
