#!/usr/bin/env python3
"""
V4.0.6 Step 2: 9264 题 AI 评估全量批跑
- v1 prompt 批量 5 题版
- 14 学科 worker 并发
- 写入 exercises_quality.json (9264 条带 5 维标签)
- 限速重试 + 退避
- 支持 cron 续跑 (跳已有)
"""
import json
import os
import sys
import time
import urllib.request
import re
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / 'scripts' / 'audit_poc'))
from prompts import format_exercise
from prompt_v1_batch import V1_BATCH_PROMPT

EXERCISES = ROOT / 'web/data/exercises.json'
OUT = ROOT / 'web/data/exercises_quality.json'
PROGRESS = ROOT / 'scripts/audit_poc/audit_progress.json'
BATCH_SIZE = 4
MAX_WORKERS = 1   # 单 worker, 稳 (2 worker 撞 429 太频繁)
MODEL_MAX_TOKENS = 5500
BATCH_SLEEP = 3.5  # 每批间隔, 控流

# 学科按概念前缀
SUBJECT_PREFIX = {
    'math': 'M_',
    'chinese': 'CN_',
    'english': 'EN_',
    'physics': 'P_',
    'chemistry': 'CH_',
    'biology': 'B_',
    'history': 'H_',
    'geography': 'G_',
    'morality_law': 'ML_',
    'info_tech': 'IT_',
    'science': 'SC_',
    'art': 'ART_',
    'pe_health': 'PE_',
    'labor': 'L_',
}


def get_llm_config():
    cfg = json.load(open(os.path.expanduser('~/.claude/settings.json')))['env']
    return cfg['ANTHROPIC_AUTH_TOKEN'], cfg['ANTHROPIC_BASE_URL']


def call_llm(prompt, max_retries=5):
    """调 LLM, 返文本, 撞限速自动退避"""
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
                # 检查 stop_reason
                stop = d.get('stop_reason', '')
                usage = d.get('usage', {})
                for c in d.get('content', []):
                    if c.get('type') == 'text':
                        text = c.get('text', '')
                        if stop == 'max_tokens':
                            return text, f'WARN: max_tokens 截断 (output {usage.get("output_tokens")} tokens)'
                        return text, None
                return None, 'empty content'
        except urllib.error.HTTPError as e:
            err = f'HTTP {e.code}: {e.reason}'
            # 429 限速或 5xx 服务端错 → 退避
            if e.code in (429, 500, 502, 503, 504):
                backoff = min(30, 3 * (2 ** attempt))
                print(f'  [retry {attempt+1}/{max_retries}] {err} → sleep {backoff}s', flush=True)
                time.sleep(backoff)
                continue
            return None, err
        except Exception as e:
            err = f'{type(e).__name__}: {e}'
            backoff = min(15, 2 * (2 ** attempt))
            print(f'  [retry {attempt+1}/{max_retries}] {err} → sleep {backoff}s', flush=True)
            time.sleep(backoff)
    return None, 'max retries exceeded'


def extract_json_array(text):
    """从 LLM 输出提取 JSON 数组"""
    if not text:
        return None
    # 找 ```json ... ``` 块
    m = re.search(r'```json\s*(\[.*?\])\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass
    # 找裸 JSON 数组 (从 [ 到 ])
    m = re.search(r'(\[.*\])', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass
    return None


def audit_batch(batch, cid2title):
    """审一批 (BATCH_SIZE, 最后一批可能少), 返 [parsed_objects] 或 None"""
    # 实际题数可能 < BATCH_SIZE (最后一批)
    n = len(batch)
    # 仍按 BATCH_SIZE 写 prompt (让 LLM 知道可能少)
    batch_text = '\n\n'.join([
        f'### 题 {i+1} ({e["id"]} {cid2title.get(e["concept_id"], "")})\n' + format_exercise(e)
        for i, e in enumerate(batch)
    ])
    # 改 prompt 期望 N
    prompt = V1_BATCH_PROMPT.format(batch_text=batch_text).replace('一次审 4 道题', f'一次审 {n} 道题').replace('JSON 数组 4 个对象', f'JSON 数组 {n} 个对象')
    text, err = call_llm(prompt)
    if not text:
        return None, {'err': err, 'raw': ''}
    arr = extract_json_array(text)
    if not arr:
        return None, {'err': f'parse failed (got 0 objects, expected {n}) err={err}', 'raw': text[:300]}
    # LLM 偶尔多返或少返: 截取前 N 个
    if len(arr) > n:
        arr = arr[:n]
    elif len(arr) < n:
        # 少返 (可能截断): 跳过这批, 不入库
        return None, {'err': f'parse failed (got {len(arr)} objects, expected {n}) 截断', 'raw': text[:300]}
    return arr, None


# ============== 共享 progress ==============
_progress_lock = threading.Lock()
_quality = {}  # q_id -> quality record


def load_progress():
    """读已完成的 (q_id, risk)"""
    global _quality
    if PROGRESS.exists():
        try:
            d = json.loads(PROGRESS.read_text())
            _quality = d.get('quality', {})
        except:
            _quality = {}


def save_progress():
    """原子写"""
    tmp = PROGRESS.with_suffix('.tmp')
    tmp.write_text(json.dumps({
        'updated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'count': len(_quality),
        'quality': _quality,
    }, ensure_ascii=False, indent=2))
    tmp.replace(PROGRESS)


def add_quality(batch, results):
    """thread-safe 添加结果"""
    with _progress_lock:
        for e, r in zip(batch, results):
            _quality[e['id']] = {
                'concept_id': e['concept_id'],
                'type': e['type'],
                'difficulty': e.get('difficulty'),
                'risk': r.get('overall_risk'),
                'answer_correct': r.get('answer_correct'),
                'question_clear': r.get('question_clear'),
                'options_quality': r.get('options_quality'),
                'difficulty_match': r.get('difficulty_match'),
                'difficulty_suggested': r.get('difficulty_suggested'),
                'concept_match': r.get('concept_match'),
                'fix_suggestion': r.get('fix_suggestion'),
            }


def run_worker(worker_id, subject, exercises, cid2title):
    """单 worker: 跑一个学科所有题"""
    # 过滤出该学科的题
    prefix = SUBJECT_PREFIX[subject]
    pool = [e for e in exercises if e['concept_id'].startswith(prefix)]
    print(f'[W{worker_id} {subject}] 启动, {len(pool)} 题', flush=True)

    # 跳过已完成
    todo = [e for e in pool if e['id'] not in _quality]
    print(f'[W{worker_id} {subject}] 待跑 {len(todo)} 题 (跳过 {len(pool) - len(todo)} 已完成)', flush=True)

    t0 = time.time()
    success = 0
    failed = 0
    save_every = 20  # 每 20 批 (100 题) 写一次 progress

    for i in range(0, len(todo), BATCH_SIZE):
        batch = todo[i:i+BATCH_SIZE]
        n = min(len(batch), BATCH_SIZE)
        results, err = audit_batch(batch, cid2title)
        if results:
            add_quality(batch[:len(results)], results)
            success += len(results)
        else:
            failed += len(batch)
            # 详细错误
            raw = err.get('raw', '') if isinstance(err, dict) else ''
            print(f'[W{worker_id} {subject}] 批 {i // BATCH_SIZE + 1} 失败: {err}', flush=True)
            if raw:
                print(f'  raw[:200]: {raw[:200]}', flush=True)

        # 进度
        done = i + len(batch)
        if done % 100 == 0 or done == len(todo):
            elapsed = time.time() - t0
            rate = done / max(elapsed, 1) * 60  # 题/分钟
            eta_min = (len(todo) - done) / max(rate, 0.1)
            print(f'[W{worker_id} {subject}] {done}/{len(todo)} 题 | 成功 {success} 失败 {failed} | {rate:.1f} 题/min | ETA {eta_min:.0f} min', flush=True)

        if (i // BATCH_SIZE) % save_every == 0:
            save_progress()

        time.sleep(BATCH_SLEEP)  # 限速保护 (2.5s/批)

    save_progress()
    elapsed = time.time() - t0
    print(f'[W{worker_id} {subject}] 完成, {success} 成功, {failed} 失败, {elapsed/60:.1f} min', flush=True)


def main():
    # 加载题库
    exs = json.loads(EXERCISES.read_text())['exercises']
    print(f'总题数: {len(exs)}')

    # 概念 title
    graph = json.load(open(ROOT / 'web/data/graph.json'))
    cid2title = {n['id']: n.get('title', '') for n in graph['nodes']}

    # 加载 progress
    load_progress()
    print(f'已完成: {len(_quality)}')

    # 按学科分题给 worker
    # 14 学科分给 MAX_WORKERS 个 worker
    # 每个 worker 跑多个学科 (按题量分)
    subjects_sorted = sorted(SUBJECT_PREFIX.keys(), key=lambda s: -sum(1 for e in exs if e['concept_id'].startswith(SUBJECT_PREFIX[s])))
    print(f'学科按题量: {[(s, sum(1 for e in exs if e["concept_id"].startswith(SUBJECT_PREFIX[s]))) for s in subjects_sorted]}')

    # 把学科 round-robin 分给 workers
    worker_subjects = [[] for _ in range(MAX_WORKERS)]
    for i, s in enumerate(subjects_sorted):
        worker_subjects[i % MAX_WORKERS].append(s)
    print(f'\nWorker 分配:')
    for wid, subs in enumerate(worker_subjects):
        n = sum(sum(1 for e in exs if e['concept_id'].startswith(SUBJECT_PREFIX[s])) for s in subs)
        print(f'  W{wid}: {subs} ({n} 题)')

    # 多 worker 错开启动, 避免 429 限速
    t_global = time.time()
    threads = []
    for wid, subs in enumerate(worker_subjects):
        for s in subs:
            t = threading.Thread(target=run_worker, args=(wid, s, exs, cid2title), name=f'W{wid}-{s}')
            t.start()
            threads.append(t)
            time.sleep(5)  # 错开 5s 启动

    for t in threads:
        t.join()

    # 写最终结果
    save_progress()
    elapsed = time.time() - t_global
    print(f'\n=== 全部完成 ===')
    print(f'总耗时: {elapsed/60:.1f} min')
    print(f'输出: {PROGRESS}')
    print(f'评估数: {len(_quality)} / {len(exs)}')

    # 复制到 web/data/ 给前端用
    import shutil
    shutil.copy(PROGRESS, OUT)
    print(f'复制到: {OUT}')


if __name__ == '__main__':
    main()
