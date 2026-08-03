#!/usr/bin/env python3
"""V4.0.6 回归测试: 重新 audit 267 改写后题, 看 high→low 转换率"""
import json
import os
import sys
import time
import urllib.request
import re
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts' / 'audit_poc'))
from prompts import format_exercise
from prompt_v1_batch import V1_BATCH_PROMPT

EXERCISES = ROOT / 'web/data/exercises.json'
QUALITY = ROOT / 'web/data/exercises_quality.json'
OUT = ROOT / 'web/data/exercises_quality_regression.json'
PROGRESS = ROOT / 'scripts/audit_poc/regression_progress.json'

BATCH_SIZE = 3
MODEL_MAX_TOKENS = 4500
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
                time.sleep(backoff)
                continue
            return None, err
        except Exception as e:
            err = f'{type(e).__name__}: {e}'
            time.sleep(min(15, 2 * (2 ** attempt)))
    return None, 'max retries'


def extract_json_array(text):
    if not text: return None
    m = re.search(r'```json\s*(\[.*?\])\s*```', text, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    m = re.search(r'(\[.*\])', text, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    return None


def audit_batch(batch, cid2title):
    n = len(batch)
    batch_text = '\n\n'.join([
        f'### 题 {i+1} ({e["id"]} {cid2title.get(e["concept_id"], "")})\n' + format_exercise(e)
        for i, e in enumerate(batch)
    ])
    prompt = V1_BATCH_PROMPT.format(batch_text=batch_text).replace('一次审 4 道题', f'一次审 {n} 道题').replace('JSON 数组 4 个对象', f'JSON 数组 {n} 个对象')
    text, err = call_llm(prompt)
    if not text:
        return None, err
    arr = extract_json_array(text)
    if not arr:
        return None, f'parse failed'
    if len(arr) > n:
        arr = arr[:n]
    elif len(arr) < n:
        return None, f'short parse ({len(arr)}/{n})'
    return arr, None


_lock = threading.Lock()
_results = {}

def load_progress():
    global _results
    if PROGRESS.exists():
        try:
            _results = json.loads(PROGRESS.read_text()).get('results', {})
        except:
            _results = {}

def save_progress():
    tmp = PROGRESS.with_suffix('.tmp')
    tmp.write_text(json.dumps({
        'updated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'count': len(_results),
        'results': _results,
    }, ensure_ascii=False, indent=2))
    tmp.replace(PROGRESS)


def main():
    exs = json.loads(EXERCISES.read_text())['exercises']
    print(f'总题数: {len(exs)}')

    # 找改写后的题 (有 _patched_by 标记)
    patched = [e for e in exs if e.get('_patched_by', '').startswith('audit_fix_v1')]
    print(f'改写后题: {len(patched)}')

    # 加载原 audit (对比 high→low 转换)
    quality = json.loads(QUALITY.read_text())['quality']
    orig_risks = {}
    for qid, r in quality.items():
        if r.get('risk') == 'high':
            orig_risks[qid] = r.get('risk')
    print(f'原 high 题 (改写前): {len(orig_risks)}')

    # 已跑回归
    load_progress()
    todo = [e for e in patched if e['id'] not in _results]
    print(f'待回归: {len(todo)} (已完成 {len(patched) - len(todo)})')

    if not todo:
        print('全部已回归')
    else:
        graph = json.load(open(ROOT / 'web/data/graph.json'))
        cid2title = {n['id']: n.get('title', '') for n in graph['nodes']}

        t0 = time.time()
        success = 0
        failed = 0
        for i in range(0, len(todo), BATCH_SIZE):
            batch = todo[i:i+BATCH_SIZE]
            results, err = audit_batch(batch, cid2title)
            if results:
                with _lock:
                    for e, r in zip(batch[:len(results)], results):
                        _results[e['id']] = {
                            'concept_id': e['concept_id'],
                            'type': e['type'],
                            'risk': r.get('overall_risk'),
                            'answer_correct': r.get('answer_correct'),
                            'question_clear': r.get('question_clear'),
                            'options_quality': r.get('options_quality'),
                            'difficulty_match': r.get('difficulty_match'),
                            'concept_match': r.get('concept_match'),
                            'fix_suggestion': r.get('fix_suggestion'),
                        }
                success += len(results)
            else:
                failed += len(batch)
                print(f'  批 {i // BATCH_SIZE + 1} 失败: {err}', flush=True)

            if (i + len(batch)) % 30 == 0 or i + len(batch) >= len(todo):
                elapsed = time.time() - t0
                rate = (i + len(batch)) / max(elapsed, 1) * 60
                eta = (len(todo) - i - len(batch)) / max(rate / 60, 0.001)
                print(f'  === {i+len(batch)}/{len(todo)} 成功 {success} 失败 {failed} | {rate:.1f} 题/min | ETA {eta:.0f} min ===', flush=True)
                save_progress()

            time.sleep(BATCH_SLEEP)

        save_progress()
        print(f'\n=== 回归完成: 成功 {success} 失败 {failed}, 总耗时 {(time.time()-t0)/60:.1f} min ===')

    # 写最终
    with open(OUT, 'w') as f:
        json.dump(_results, f, ensure_ascii=False, indent=2)
    print(f'输出: {OUT}')

    # 对比报告
    from collections import Counter
    new_risks = Counter()
    converted = Counter()  # original_risk → new_risk
    for qid, r in _results.items():
        new_risks[r.get('risk', '?')] += 1
        old = orig_risks.get(qid, 'not_high')
        converted[(old, r.get('risk', '?'))] += 1
    print(f'\n=== 改写后 risk 分布 ===')
    for risk, n in new_risks.most_common():
        print(f'  {risk}: {n}')
    print(f'\n=== 转换矩阵 (old → new) ===')
    for (old, new), n in sorted(converted.items()):
        print(f'  {old} → {new}: {n}')


if __name__ == '__main__':
    main()
