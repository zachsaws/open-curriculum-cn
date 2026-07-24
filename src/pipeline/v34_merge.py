"""
V3.3.4 合并: 把 math 337 + chinese 209 的 3 个新字段 (real_examples, common_mistakes, teaching_activity) 合并到 all_v3.3.json.

输入:
- data/graph/all_v3.3.json (V3.3 基础)
- data/graph/math_v34_llm.json (math 337)
- data/graph/chinese_v34_llm.json (chinese 209)

输出:
- data/graph/all_v3.3.json (V3.3.4, version 升级 + nodes 加 3 字段)
- web/data/graph.json (公网同步)
- web/data/graph.json.gz
"""
import json
import os
import sys
from collections import Counter

ROOT = '/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn'
os.chdir(ROOT)

# 1. 读 V3.3.4 新字段
V34_FILES = {
    'math': 'data/graph/math_v34_llm.json',
    'chinese': 'data/graph/chinese_v34_llm.json',
}

v34_map = {}  # id -> {real_examples, common_mistakes, teaching_activity}
v34_stats = {}

for subj, path in V34_FILES.items():
    if not os.path.exists(path):
        v34_stats[subj] = (0, 0)
        continue
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        concepts = data.get('concepts', data.get('items', []))
    else:
        concepts = data
    for c in concepts:
        if all(k in c for k in ['real_examples', 'common_mistakes', 'teaching_activity']):
            v34_map[c['id']] = {
                'real_examples': c['real_examples'],
                'common_mistakes': c['common_mistakes'],
                'teaching_activity': c['teaching_activity'],
            }
    v34_stats[subj] = (len([c for c in concepts if 'real_examples' in c]), len(concepts))

print(f"V3.3.4 字段: {len(v34_map)} 概念 across {len(V34_FILES)} 学科")
for s, (a, t) in v34_stats.items():
    print(f"  {s:14s}: {a:4d}/{t:4d} 概念有 V3.3.4 字段")

# 2. 读 V3.3 基础
with open('data/graph/all_v3.3.json', 'r', encoding='utf-8') as f:
    base = json.load(f)

nodes = base.get('nodes', [])
edges = base.get('edges', base.get('relations', []))
print(f"\nV3.3 基础: {len(nodes)} nodes, {len(edges)} edges")

# 3. 合并: 每个节点加 3 字段 (如果 id 在 v34_map)
v34_count = 0
v33_nodes = []
for n in nodes:
    nid = n.get('id')
    new_n = dict(n)
    if nid in v34_map:
        new_n['real_examples'] = v34_map[nid]['real_examples']
        new_n['common_mistakes'] = v34_map[nid]['common_mistakes']
        new_n['teaching_activity'] = v34_map[nid]['teaching_activity']
        v34_count += 1
    v33_nodes.append(new_n)

print(f"\n合并结果: V3.3.4 增强 {v34_count} (实际: {len(v34_map)} unique)")

# 4. 写 all_v3.3.json
import datetime
v33_data = {
    'version': 'v3.3.4',
    'generatedAt': datetime.datetime.now().isoformat() + 'Z',
    'subjects_covered': base.get('subjects_covered', []),
    'llm_enhanced_count': base.get('llm_enhanced_count', 0),
    'v32_fallback_count': base.get('v32_fallback_count', 0),
    'v34_enhanced_count': v34_count,
    'conceptCount': len(v33_nodes),
    'edgeCount': len(edges),
    'nodes': v33_nodes,
    'edges': edges,
}
out = 'data/graph/all_v3.3.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(v33_data, f, ensure_ascii=False, separators=(',', ':'))
print(f"\n✓ 写 {out} ({os.path.getsize(out) / 1024:.1f} KB)")

# 5. 同步到 web
import gzip
web_data = {
    'version': 'v3.3.4',
    'conceptCount': len(v33_nodes),
    'edgeCount': len(edges),
    'nodes': v33_nodes,
    'edges': edges,
}
web_path = 'web/data/graph.json'
with open(web_path, 'w', encoding='utf-8') as f:
    json.dump(web_data, f, ensure_ascii=False, separators=(',', ':'))
sz = os.path.getsize(web_path)
print(f"✓ 写 {web_path} ({sz/1024:.1f} KB)")

# gz
with open(web_path, 'rb') as f:
    gz = gzip.compress(f.read(), compresslevel=9)
with open(web_path + '.gz', 'wb') as f:
    f.write(gz)
print(f"✓ 写 {web_path}.gz ({len(gz)/1024:.1f} KB, {len(gz)/sz*100:.1f}% of raw)")

# 6. 统计
print("\nBy subject:")
by_subj = Counter(n['subject'] for n in v33_nodes)
llm_by_subj = Counter(n['subject'] for n in v33_nodes if n.get('llm_enhanced'))
v34_by_subj = Counter(n['subject'] for n in v33_nodes if 'real_examples' in n)
for s, n in by_subj.most_common():
    l = llm_by_subj.get(s, 0)
    v = v34_by_subj.get(s, 0)
    print(f"  {s:14s}: V3.3 LLM {l:4d}/{n:4d} ({l/n*100:.0f}%), V3.3.4 增强 {v:4d}/{n:4d} ({v/n*100:.0f}%)")

# 7. 抽样验证 5 个 (3 math + 2 chinese)
print("\n=== 5 概念抽样验证 ===")
import random
random.seed(42)
v34_ids = list(v34_map.keys())
math_ids = [i for i in v34_ids if i.startswith('M_')]
chi_ids = [i for i in v34_ids if i.startswith('CN_')]
samples = random.sample(math_ids, 3) + random.sample(chi_ids, 2)
nodes_by_id = {n['id']: n for n in v33_nodes}
for sid in samples:
    n = nodes_by_id[sid]
    print(f"\n--- {sid} ({n['title']}) ---")
    for f in ['real_examples', 'common_mistakes', 'teaching_activity']:
        v = n.get(f, 'N/A')
        print(f"  {f} (len={len(v)}):")
        print(f"    {v}")
