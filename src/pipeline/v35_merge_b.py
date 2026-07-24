"""
V3.3.5 合并 B 批: 把 B 批 7 学科 (info_tech 97 / geography 91 / pe_health 87 / labor 85 / art 78 / biology 71 / chemistry 62) 共 571 概念的 3 字段合并到 all_v3.3.json.

输入:
- data/graph/all_v3.3.json (V3.3.5 基础, A 批已合并, 含 math+chinese 546 + A 批 789 = 1335 概念已带 V3.3.4/V3.3.5 字段)
- data/graph/{info_tech,geography,pe_health,labor,art,biology,chemistry}_v35_llm.json (B 批 7 学科)

输出:
- data/graph/all_v3.3.json (V3.3.5 B, version 升级, B 批 7 学科加 3 字段)
- web/data/graph.json + .gz (公网同步)
"""
import json
import os
import sys
import datetime
import gzip
import random
from collections import Counter

ROOT = '/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn'
os.chdir(ROOT)

# B 批 7 学科
B_BATCH_SUBJECTS = ['info_tech', 'geography', 'pe_health', 'labor', 'art', 'biology', 'chemistry']
V35_FILES = {
    subj: f'data/graph/{subj}_v35_llm.json' for subj in B_BATCH_SUBJECTS
}

v35_map = {}  # id -> {real_examples, common_mistakes, teaching_activity}
v35_stats = {}

for subj, path in V35_FILES.items():
    if not os.path.exists(path):
        v35_stats[subj] = (0, 0)
        print(f"  ⚠ {subj}: {path} 不存在 (skip)", flush=True)
        continue
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        concepts = data.get('concepts', data.get('items', []))
    else:
        concepts = data
    for c in concepts:
        if all(k in c for k in ['real_examples', 'common_mistakes', 'teaching_activity']):
            v35_map[c['id']] = {
                'real_examples': c['real_examples'],
                'common_mistakes': c['common_mistakes'],
                'teaching_activity': c['teaching_activity'],
            }
    v35_stats[subj] = (len([c for c in concepts if 'real_examples' in c]), len(concepts))

print(f"V3.3.5 B 批字段: {len(v35_map)} 概念 across {len(B_BATCH_SUBJECTS)} 学科")
for s, (a, t) in v35_stats.items():
    print(f"  {s:14s}: {a:4d}/{t:4d} 概念有 V3.3.5 字段")

# 读 V3.3.5 基础 (A 批已合并)
with open('data/graph/all_v3.3.json', 'r', encoding='utf-8') as f:
    base = json.load(f)

print(f"\n当前 base version: {base.get('version')}")
nodes = base.get('nodes', [])
edges = base.get('edges', base.get('relations', []))
print(f"基础: {len(nodes)} nodes, {len(edges)} edges")

# 合并: 每个节点加 3 字段 (如果 id 在 v35_map)
v35_count = 0
new_nodes = []
for n in nodes:
    nid = n.get('id')
    new_n = dict(n)
    if nid in v35_map:
        new_n['real_examples'] = v35_map[nid]['real_examples']
        new_n['common_mistakes'] = v35_map[nid]['common_mistakes']
        new_n['teaching_activity'] = v35_map[nid]['teaching_activity']
        v35_count += 1
    new_nodes.append(new_n)

print(f"\n合并结果: V3.3.5 B 批增强 {v35_count} 概念 (期望: {sum(t for _, t in v35_stats.values())})")

# 写 all_v3.3.json
v33_data = {
    'version': 'v3.3.5',
    'generatedAt': datetime.datetime.now().isoformat() + 'Z',
    'subjects_covered': base.get('subjects_covered', []),
    'llm_enhanced_count': base.get('llm_enhanced_count', 0),
    'v32_fallback_count': base.get('v32_fallback_count', 0),
    'v34_enhanced_count': base.get('v34_enhanced_count', 0),
    'v35_a_enhanced_count': base.get('v35_a_enhanced_count', 0),
    'v35_b_enhanced_count': v35_count,
    'conceptCount': len(new_nodes),
    'edgeCount': len(edges),
    'nodes': new_nodes,
    'edges': edges,
}
out = 'data/graph/all_v3.3.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(v33_data, f, ensure_ascii=False, separators=(',', ':'))
print(f"\n✓ 写 {out} ({os.path.getsize(out) / 1024:.1f} KB)")

# 同步到 web
web_data = {
    'version': 'v3.3.5',
    'conceptCount': len(new_nodes),
    'edgeCount': len(edges),
    'nodes': new_nodes,
    'edges': edges,
}
web_path = 'web/data/graph.json'
with open(web_path, 'w', encoding='utf-8') as f:
    json.dump(web_data, f, ensure_ascii=False, separators=(',', ':'))
sz = os.path.getsize(web_path)
print(f"✓ 写 {web_path} ({sz/1024:.1f} KB)")

with open(web_path, 'rb') as f:
    gz = gzip.compress(f.read(), compresslevel=9)
with open(web_path + '.gz', 'wb') as f:
    f.write(gz)
print(f"✓ 写 {web_path}.gz ({len(gz)/1024:.1f} KB, {len(gz)/sz*100:.1f}% of raw)")

# 统计
print("\nBy subject:")
by_subj = Counter(n['subject'] for n in new_nodes)
llm_by_subj = Counter(n['subject'] for n in new_nodes if n.get('llm_enhanced'))
v34_by_subj = Counter(n['subject'] for n in new_nodes if n.get('real_examples'))
for s, n in by_subj.most_common():
    l = llm_by_subj.get(s, 0)
    v = v34_by_subj.get(s, 0)
    print(f"  {s:14s}: V3.3 LLM {l:4d}/{n:4d} ({l/n*100:.0f}%), V3.3.5 增强 {v:4d}/{n:4d} ({v/n*100:.0f}%)")

# 抽样验证 5 概念 (1 per 学科)
print("\n=== 7 概念抽样验证 (1 per 学科) ===")
random.seed(42)
nodes_by_id = {n['id']: n for n in new_nodes}
for subj in B_BATCH_SUBJECTS:
    subj_ids = [i for i in v35_map.keys() if nodes_by_id.get(i, {}).get('subject') == subj]
    if not subj_ids:
        print(f"\n  [{subj}] 无抽样")
        continue
    sid = random.choice(subj_ids)
    n = nodes_by_id[sid]
    print(f"\n--- {sid} ({n['title']}) [{subj}] ---")
    for f in ['real_examples', 'common_mistakes', 'teaching_activity']:
        v = n.get(f, 'N/A')
        print(f"  {f} (len={len(v)}):")
        print(f"    {v}")
