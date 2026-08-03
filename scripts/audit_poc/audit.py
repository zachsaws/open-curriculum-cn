#!/usr/bin/env python3
"""
V4.0.6 题库 AI 评估 Step 1: 4 prompt 对比 PoC
- 50 题 (按学科分层)
- 4 个 prompt 版本对比
- 输出 4 份 results_*.json
- 让天祥看 20 题定 prompt
"""
import json
import os
import sys
import time
import urllib.request
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SAMPLE = ROOT / 'scripts/audit_poc' / 'sample_50.json'
OUT_DIR = ROOT / 'scripts/audit_poc'
sys.path.insert(0, str(ROOT / 'scripts' / 'audit_poc'))
from prompts import PROMPTS, format_exercise


# LLM 客户端 (minimaxi.com anthropic)
def get_llm_config():
    cfg = json.load(open(os.path.expanduser('~/.claude/settings.json')))['env']
    return cfg['ANTHROPIC_AUTH_TOKEN'], cfg['ANTHROPIC_BASE_URL']


def call_llm(prompt, max_tokens=800, model='MiniMax-M3', retries=3):
    """调 LLM, 返文本"""
    key, base = get_llm_config()
    url = f'{base}/v1/messages'
    data = json.dumps({
        'model': model,
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode()

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, method='POST', headers={
                'x-api-key': key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            }, data=data)
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read().decode()
                d = json.loads(body)
                for c in d.get('content', []):
                    if c.get('type') == 'text':
                        return c.get('text', '')
                return None
        except Exception as e:
            print(f'  retry {attempt+1}: {e}', flush=True)
            time.sleep(2 ** attempt)
    return None


def extract_json(text):
    """从 LLM 输出里提取 JSON"""
    if not text:
        return None
    # 找 ```json ... ``` 块
    m = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass
    # 找裸 JSON
    m = re.search(r'(\{.*\})', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass
    return None


def main():
    samples = json.loads(SAMPLE.read_text())
    print(f'加载 {len(samples)} 题')

    # 加载 graph.json 取概念 title
    graph = json.load(open(ROOT / 'web/data/graph.json'))
    cid2title = {n['id']: n.get('title', '') for n in graph['nodes']}

    # 4 个 prompt 各跑
    for version, prompt_tpl in PROMPTS.items():
        print(f'\n=== {version} ===')
        results = []
        t0 = time.time()
        for i, e in enumerate(samples):
            ex_text = format_exercise(e, cid2title.get(e['concept_id'], ''))
            prompt = prompt_tpl.format(ex_text=ex_text)
            t1 = time.time()
            text = call_llm(prompt)
            dt = time.time() - t1
            parsed = extract_json(text)
            results.append({
                'q_id': e['id'],
                'concept_id': e['concept_id'],
                'type': e['type'],
                'difficulty': e.get('difficulty'),
                'question': e.get('question', '')[:80],
                'answer': e.get('answer', '')[:30],
                'llm_raw': (text or '')[:400],
                'llm_parsed': parsed,
                'latency_s': round(dt, 2),
            })
            print(f'  [{i+1}/{len(samples)}] {e["id"]} ... {dt:.1f}s {"✓" if parsed else "✗"}', flush=True)
            time.sleep(0.5)  # 限速保护

        out = OUT_DIR / f'results_{version}.json'
        with open(out, 'w') as f:
            json.dump({
                'version': version,
                'count': len(results),
                'parsed_ok': sum(1 for r in results if r['llm_parsed']),
                'total_time_s': round(time.time() - t0, 1),
                'results': results,
            }, f, ensure_ascii=False, indent=2)
        print(f'  写盘: {out.name} (parsed {sum(1 for r in results if r["llm_parsed"])}/{len(results)})')
        print(f'  总耗时: {time.time()-t0:.0f}s')


if __name__ == '__main__':
    main()
