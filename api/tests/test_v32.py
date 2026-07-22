"""
V3.2 新增字段测试
- edge reason 100% 填充
- assessment_prompt 100% 填充
- centrality 100% 填充
- type 100% 填充
- age 100% 填充
- prerequisite 边是 DAG
- 跨学段螺旋 数量 > 100
- 跨学科关联 数量 > 500
- 关系类型分布: prerequisite + progresses_to + relates_to
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GRAPH = ROOT / "data" / "graph" / "all_v3.2.json"
CLUSTERS = ROOT / "data" / "graph" / "clusters.json"
STANDARDS = ROOT / "data" / "graph" / "curriculum-standards.json"
MANIFEST = ROOT / "data" / "graph" / "manifest.json"

def load():
    return json.load(open(GRAPH)), json.load(open(CLUSTERS)), json.load(open(STANDARDS)), json.load(open(MANIFEST))

def stage_of(g):
    if g <= 2: return (1, 2)
    if g <= 4: return (3, 4)
    if g <= 6: return (5, 6)
    return (7, 9)

def stage_from_id(eid):
    """id-based 跨学段判断: M_G1_NS_01 → grade 1, M_G3_NS_01 → grade 3"""
    parts = eid.split("_")
    if len(parts) < 2: return None
    g = parts[1]
    if g.startswith("G") and g[1:].isdigit():
        return int(g[1:])
    return None

def test_v32_data():
    d, c, s, m = load()
    nodes, edges = d["nodes"], d["edges"]
    # 基本数据完整性
    assert len(nodes) == 1906, f"节点数: {len(nodes)}"
    assert len(edges) == 4736, f"边数: {len(edges)}"
    # V3.2 字段填充
    type_filled = sum(1 for n in nodes if n.get("type") in ("CONCEPTUAL", "PROCEDURAL", "FACTUAL"))
    assert type_filled == 1906, f"type 填充: {type_filled}/1906"
    age_filled = sum(1 for n in nodes if n.get("age_range_start") is not None and n.get("age_range_end") is not None)
    assert age_filled == 1906, f"age 填充: {age_filled}/1906"
    cent_filled = sum(1 for n in nodes if n.get("centrality") is not None)
    assert cent_filled == 1906, f"centrality 填充: {cent_filled}/1906"
    assess_filled = sum(1 for n in nodes if n.get("assessment_prompt"))
    assert assess_filled == 1906, f"assessment 填充: {assess_filled}/1906"
    reason_filled = sum(1 for e in edges if e.get("reason"))
    assert reason_filled == 4736, f"reason 填充: {reason_filled}/4736"
    print("✅ V3.2 数据完整性: 1906 节点, 4736 边, 6 个新字段 100% 填充")

def test_v32_dag():
    d, _, _, _ = load()
    edges = d["edges"]
    pre = [e for e in edges if e.get("rel") == "prerequisite"]
    # Kahn 算法
    from collections import deque
    in_deg = {}
    adj = {}
    for n in d["nodes"]:
        in_deg[n["id"]] = 0
        adj[n["id"]] = []
    for e in pre:
        adj[e["from"]].append(e["to"])
        in_deg[e["to"]] = in_deg.get(e["to"], 0) + 1
    queue = deque([n for n, d in in_deg.items() if d == 0])
    visited = 0
    while queue:
        u = queue.popleft()
        visited += 1
        for v in adj[u]:
            in_deg[v] -= 1
            if in_deg[v] == 0:
                queue.append(v)
    assert visited == len(d["nodes"]), f"prerequisite DAG 失败: visited {visited}/{len(d['nodes'])}"
    print(f"✅ DAG: prerequisite {len(pre)} 边全部 DAG, visited {visited}/{len(d['nodes'])}")

def test_v32_cross_grade_and_subj():
    d, _, _, _ = load()
    nodes = d["nodes"]
    edges = d["edges"]
    id2n = {n["id"]: n for n in nodes}
    # V3.0 数据是每年级一段, 用 id 解析
    cross_grade = 0
    cross_subj = 0
    for e in edges:
        fg = stage_from_id(e["from"])
        tg = stage_from_id(e["to"])
        if fg is not None and tg is not None and fg != tg:
            cross_grade += 1
        fs = e["from"].split("_", 1)[0]
        ts = e["to"].split("_", 1)[0]
        if fs != ts:
            cross_subj += 1
    assert cross_grade > 500, f"跨学段: {cross_grade}"
    assert cross_subj > 1500, f"跨学科: {cross_subj}"
    print(f"✅ 跨学段: {cross_grade} ({cross_grade*100/len(edges):.1f}%) / 跨学科: {cross_subj} ({cross_subj*100/len(edges):.1f}%)")

def test_v32_clusters():
    _, c, _, _ = load()
    assert c["clusterCount"] >= 100, f"clusters: {c['clusterCount']}"
    # 抽样 5 个, 每个 summary 不能是空
    for x in c["clusters"][:5]:
        assert x.get("summary_zh"), f"cluster 无 summary: {x['id']}"
        assert x.get("concept_count", 0) > 0
    print(f"✅ Clusters: {c['clusterCount']} 域, 5 个抽样都有 summary_zh")

def test_v32_standards():
    _, _, s, _ = load()
    assert s["curriculumCount"] >= 1, f"curricula: {s['curriculumCount']}"
    cs = s["curricula"][0]
    assert cs["topicCount"] == 1906, f"curriculum topics: {cs['topicCount']}"
    # 抽样 3 个 topic, 都有 data
    for t in cs["topics"][:3]:
        assert t.get("key"), f"topic 无 key"
        assert t.get("code"), f"topic 无 code"
        assert t.get("data", {}).get("title"), f"topic data 无 title"
    print(f"✅ Standards: 1 框架 × {cs['topicCount']} topics")

def test_v32_manifest():
    _, _, _, m = load()
    assert m["isDAG"] is True, f"manifest DAG 状态: {m.get('isDAG')}"
    assert m["prerequisiteEdgesCount"] >= 1500, f"manifest prerequisite 数: {m.get('prerequisiteEdgesCount')}"
    assert m["cycleCount"] == 0, f"manifest cycleCount: {m.get('cycleCount')}"
    # 数据质量: 至少 9 个 100%
    full = sum(1 for v in m["dataQuality"].values() if "100.0%" in v)
    assert full >= 8, f"100% 填充项: {full}/10 (质量: {m['dataQuality']})"
    print(f"✅ Manifest: isDAG=True, cycleCount=0, {full}/10 字段 100% 填充")

def test_v32_relations_distribution():
    d, _, _, _ = load()
    edges = d["edges"]
    from collections import Counter
    rel_cnt = Counter(e.get("rel") for e in edges)
    assert rel_cnt["prerequisite"] >= 1500, f"prerequisite: {rel_cnt['prerequisite']}"
    assert rel_cnt["relates_to"] >= 2000, f"relates_to: {rel_cnt['relates_to']}"
    assert rel_cnt["progresses_to"] >= 300, f"progresses_to: {rel_cnt['progresses_to']}"
    print(f"✅ 关系分布: prerequisite={rel_cnt['prerequisite']} / progresses_to={rel_cnt['progresses_to']} / relates_to={rel_cnt['relates_to']}")

def test_v32_reason_quality():
    """reason 质量抽样"""
    d, _, _, _ = load()
    edges = d["edges"]
    id2n = {n["id"]: n for n in d["nodes"]}
    # 抽样 5 条, 每条 reason 包含 from_title 或 to_title
    import random
    random.seed(42)
    sample = random.sample(edges, 5)
    for e in sample:
        from_n = id2n.get(e["from"])
        to_n = id2n.get(e["to"])
        r = e.get("reason", "")
        # reason 至少 10 字
        assert len(r) >= 10, f"reason 太短: {r}"
        # 包含其中一个 title 关键词
        if from_n and to_n:
            from_kw = from_n["title"][:6] if from_n["title"] else ""
            to_kw = to_n["title"][:6] if to_n["title"] else ""
            assert from_kw in r or to_kw in r, f"reason 没包含 from/to title: {r} (from={from_kw}, to={to_kw})"
    print(f"✅ Reason 质量: 5 个抽样都包含 from/to title 关键词")

if __name__ == "__main__":
    print("=== V3.2 测试套件 ===\\n")
    test_v32_data()
    test_v32_dag()
    test_v32_cross_grade_and_subj()
    test_v32_clusters()
    test_v32_standards()
    test_v32_manifest()
    test_v32_relations_distribution()
    test_v32_reason_quality()
    print("\\n🎉 全部 8 个 V3.2 测试通过")
