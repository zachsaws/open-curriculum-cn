"""
V3.3 合并: 把 7 完成学科 + chinese 77 + math 50 PoC 的 LLM 输出合并到 all_v3.3.json.
其余 1061 概念保留 V3.2 fallback (description/content_req/assessment_prompt 套词).

输出: data/graph/all_v3.3.json + web/data/graph.json
"""
import json
import os
import sys
from collections import Counter

ROOT = '/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn'
os.chdir(ROOT)

# 1. 收集所有 LLM 输出
LLM_SUBJECTS = {
    'biology': 'data/graph/biology_v33_llm.json',
    'history': 'data/graph/history_v33_llm.json',
    'info_tech': 'data/graph/info_tech_v33_llm.json',
    'pe_health': 'data/graph/pe_health_v33_llm.json',
    'science': 'data/graph/science_v33_llm.json',
    'morality_law': 'data/graph/morality_law_v33_llm.json',
    'geography': 'data/graph/geography_v33_llm.json',
    'math': 'data/graph/math_v33_llm.json',  # 只 50/337
    'chinese': 'data/graph/chinese_v33_batch1.json',  # 只 77/209
    'english': 'data/graph/english_v33_llm.json',  # 296/296
    'physics': 'data/graph/physics_v33_llm.json',  # 121/121 V3.3.3
    'labor': 'data/graph/labor_v33_llm.json',  # 85/85 V3.3.3
    'art': 'data/graph/art_v33_llm.json',  # 78/78 V3.3.3
}

llm_map = {}  # id -> {description, assessment_prompt}
stats = {}

for subj, path in LLM_SUBJECTS.items():
    if not os.path.exists(path):
        stats[subj] = (0, 0)
        continue
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        concepts = data.get('concepts', data.get('items', []))
    else:
        concepts = data
    for c in concepts:
        if 'description' in c and 'assessment_prompt' in c:
            llm_map[c['id']] = {
                'description': c['description'],
                'assessment_prompt': c['assessment_prompt'],
                'subject': c.get('subject', subj),
            }
    stats[subj] = (len([c for c in concepts if 'description' in c]), len(concepts))

print(f"LLM 输出: {len(llm_map)} 概念 across {len(LLM_SUBJECTS)} 学科")
for s, (a, t) in stats.items():
    print(f"  {s:14s}: {a:4d}/{t:4d} 概念有 LLM 输出")

# 2. 读 V3.2 基础数据
with open('data/graph/all_v3.2.json', 'r', encoding='utf-8') as f:
    base = json.load(f)

nodes = base.get('nodes', [])
edges = base.get('edges', base.get('relations', []))
print(f"\nV3.2 基础: {len(nodes)} nodes, {len(edges)} edges")

# 3. 合并: 每个节点覆盖 description/assessment_prompt
llm_count = 0
v32_count = 0
v33_nodes = []
for n in nodes:
    nid = n.get('id')
    new_n = dict(n)
    if nid in llm_map:
        new_n['description'] = llm_map[nid]['description']
        new_n['assessment_prompt'] = llm_map[nid]['assessment_prompt']
        new_n['llm_enhanced'] = True
        llm_count += 1
    else:
        new_n['llm_enhanced'] = False
        v32_count += 1
    v33_nodes.append(new_n)

print(f"\n合并结果: LLM 增强 {llm_count} (实际: {len(llm_map)} unique), V3.2 fallback {v32_count}")
print(f"Total: {len(v33_nodes)} nodes, {len(edges)} edges")

# 4. 写 all_v3.3.json
import datetime
v33_data = {
    'version': 'v3.3.3',
    'generatedAt': datetime.datetime.now().isoformat() + 'Z',
    'subjects_covered': list(LLM_SUBJECTS.keys()),
    'llm_enhanced_count': llm_count,
    'v32_fallback_count': v32_count,
    'conceptCount': len(v33_nodes),
    'edgeCount': len(edges),
    'nodes': v33_nodes,
    'edges': edges,
}
out = 'data/graph/all_v3.3.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(v33_data, f, ensure_ascii=False, separators=(',', ':'))
print(f"\n✓ 写 {out} ({os.path.getsize(out) / 1024:.1f} KB)")

# 5. 同步到 web (压缩版: 不包含 academic_req 这种大字段)
import gzip
web_data = {
    'version': 'v3.3.3',
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

# 6. 统计 by subject
print("\nBy subject:")
by_subj = Counter(n['subject'] for n in v33_nodes)
llm_by_subj = Counter(n['subject'] for n in v33_nodes if n['llm_enhanced'])
for s, n in by_subj.most_common():
    l = llm_by_subj.get(s, 0)
    print(f"  {s:14s}: {l:4d}/{n:4d} LLM 增强 ({l/n*100:.0f}%)")
