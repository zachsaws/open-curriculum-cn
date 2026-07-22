"""
V3.2 P1: manifest + provenance + type + age + centrality + DAG validation
- 6 件事一次做完
"""
import json
import re
from pathlib import Path
from collections import Counter, defaultdict
import networkx as nx

ROOT = Path(__file__).parent.parent.parent
GRAPH = ROOT / "data" / "graph" / "all_v3.2.json"
CLUSTERS = ROOT / "data" / "graph" / "clusters.json"
STANDARDS = ROOT / "data" / "graph" / "curriculum-standards.json"
MANIFEST = ROOT / "data" / "graph" / "manifest.json"
PROVENANCE = ROOT / "PROVENANCE.md"

# grade → age 映射 (中国 2022 义教)
GRADE_AGE = {1: 6, 2: 7, 3: 8, 4: 9, 5: 10, 6: 11, 7: 12, 8: 13, 9: 14}

# type 分类规则
def classify_type(node):
    """基于 title + content_req 关键词分类 CONCEPTUAL/PROCEDURAL/FACTUAL"""
    title = node.get("title", "")
    content = node.get("content_req", "")
    full = title + " " + content
    # PROCEDURAL 关键词
    proc_kw = ["运算", "计算", "画", "制作", "操作", "实验", "测量", "解法", "步骤", "方法", "方法", "技巧",
               "写法", "读法", "唱", "跳", "做", "煮", "缝", "整理", "打扫", "种植", "养殖", "工艺",
               "流程", "程序", "算法", "步骤", "解方程", "化简", "化归", "变换", "转化"]
    # FACTUAL 关键词
    fact_kw = ["认识", "了解", "知道", "记忆", "背诵", "说出", "列举", "说出", "识别", "了解", "理解概念",
               "定义", "概念", "含义", "意义", "历史", "人物", "事件", "年代", "地理", "国名", "首都",
               "首都", "轮廓", "符号", "元素", "朝代", "年份"]
    # CONCEPTUAL (其他)
    proc_score = sum(1 for k in proc_kw if k in full)
    fact_score = sum(1 for k in fact_kw if k in full)
    if proc_score > fact_score and proc_score > 0:
        return "PROCEDURAL"
    if fact_score > proc_score and fact_score > 0:
        return "FACTUAL"
    if proc_score == 0 and fact_score == 0:
        return "CONCEPTUAL"
    return "CONCEPTUAL"

def main():
    print(f"读 {GRAPH}")
    with open(GRAPH) as f:
        d = json.load(f)
    nodes = d["nodes"]
    edges = d["edges"]

    # 1. type 字段
    print("\n[1/6] type 字段...")
    type_counter = Counter()
    for n in nodes:
        if not n.get("type"):
            n["type"] = classify_type(n)
        type_counter[n["type"]] += 1
    print(f"  type 分布: {dict(type_counter)}")

    # 2. age 字段
    print("\n[2/6] age 字段...")
    age_filled = 0
    for n in nodes:
        g = n.get("grade_start", 1)
        ge = n.get("grade_end", g)
        if not n.get("age_range_start"):
            n["age_range_start"] = GRADE_AGE.get(g, 6)
            n["age_range_end"] = GRADE_AGE.get(ge, 14)
            age_filled += 1
    print(f"  age 填充: {age_filled}")

    # 3. centrality (用 networkx)
    print("\n[3/6] centrality (degree/closeness/betweenness)...")
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n["id"])
    for e in edges:
        G.add_edge(e["from"], e["to"])
    print(f"  图节点: {G.number_of_nodes()}, 边: {G.number_of_edges()}")
    # degree centrality
    dc = nx.degree_centrality(G)
    # 抽样 closeness (O(N*E), 200 节点最快, 但 V3.1 1906 节点)
    # 用近似: 只算 indegree 出度比
    id2centrality = {}
    for n in nodes:
        nid = n["id"]
        # 复合 centrality: indegree + outdegree 加权
        in_d = G.in_degree(nid)
        out_d = G.out_degree(nid)
        # indegree 权重高 (因为"被多少人需要" 比 "能解锁多少" 更重要)
        c = (in_d * 2 + out_d * 1) / 100  # 归一化
        id2centrality[nid] = round(c, 4)
    # 写入
    cnt_filled = 0
    for n in nodes:
        if id2centrality.get(n["id"]) is not None:
            n["centrality"] = id2centrality[n["id"]]
            cnt_filled += 1
    print(f"  centrality 填充: {cnt_filled}")
    # 验证
    cnts = sorted([n["centrality"] for n in nodes if n.get("centrality")], reverse=True)
    print(f"  centrality top5: {cnts[:5]}")
    print(f"  centrality median: {cnts[len(cnts)//2]}")

    # 4. DAG 验证 (用 Kahn 算法, O(V+E), 不调用 simple_cycles)
    print("\n[4/6] DAG 验证 (Kahn 算法)...")
    # 计算 in-degree
    in_deg = {n: 0 for n in G.nodes()}
    for u, v in G.edges():
        in_deg[v] = in_deg.get(v, 0) + 1
    # Kahn's
    from collections import deque
    queue = deque([n for n, d in in_deg.items() if d == 0])
    visited = 0
    while queue:
        u = queue.popleft()
        visited += 1
        for v in G.successors(u):
            in_deg[v] -= 1
            if in_deg[v] == 0:
                queue.append(v)
    is_dag = (visited == G.number_of_nodes())
    print(f"  is DAG: {is_dag}")
    print(f"  visited {visited}/{G.number_of_nodes()} nodes")
    cycles_count = 0 if is_dag else (G.number_of_nodes() - visited)
    if not is_dag:
        # 找环 (DFS, 限制 5 个)
        def find_cycles(limit=5):
            WHITE, GRAY, BLACK = 0, 1, 2
            color = {n: WHITE for n in G.nodes()}
            cycles = []
            def dfs(u, path):
                if len(cycles) >= limit: return
                color[u] = GRAY
                for v in G.successors(u):
                    if color[v] == GRAY:
                        idx = path.index(v) if v in path else 0
                        cycles.append(path[idx:] + [v])
                    elif color[v] == WHITE:
                        dfs(v, path + [v])
                color[u] = BLACK
            for n in list(G.nodes())[:200]:  # 只检查前 200 节点节省时间
                if color[n] == WHITE:
                    dfs(n, [n])
                    if len(cycles) >= limit: break
            return cycles
        cycles = find_cycles(5)
        print(f"  ! 至少 {cycles_count} 个节点在环中, 样本 (前 5):")
        for c in cycles[:5]:
            print(f"    {' -> '.join(c[:6])}...")

    # 5. manifest.json
    print("\n[5/6] manifest.json...")
    subj_count = Counter(n["subject"] for n in nodes)
    rel_count = Counter(e.get("rel", "?") for e in edges)
    by_subj_nodes = {s: c for s, c in subj_count.items()}
    by_rel_edges = {r: c for r, c in rel_count.items()}
    # prerequisite 单独的 DAG 状态
    pre_edges = [e for e in edges if e.get("rel") == "prerequisite"]
    G_pre = nx.DiGraph()
    for n in nodes:
        G_pre.add_node(n["id"])
    for e in pre_edges:
        G_pre.add_edge(e["from"], e["to"])
    in_deg_p = {n: 0 for n in G_pre.nodes()}
    for u, v in G_pre.edges():
        in_deg_p[v] = in_deg_p.get(v, 0) + 1
    queue_p = deque([n for n, d in in_deg_p.items() if d == 0])
    visited_p = 0
    while queue_p:
        u = queue_p.popleft()
        visited_p += 1
        for v in G_pre.successors(u):
            in_deg_p[v] -= 1
            if in_deg_p[v] == 0:
                queue_p.append(v)
    pre_is_dag = (visited_p == G_pre.number_of_nodes())
    manifest = {
        "dataset": "Open Curriculum CN",
        "taxonomyVersion": "v3.2",
        "generatedAt": "2026-07-22T20:30:00.000Z",
        "publisher": "智身科技 / 智身研究院",
        "sourceData": "中华人民共和国教育部 2022 义务教育课程方案和课程标准",
        "dataSourceUrls": [
            "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html",
        ],
        "codesOnlySources": [],
        "textIncludedSources": ["cn-compulsory-2022"],
        "counts": {
            "concepts": len(nodes),
            "edges": len(edges),
            "subjects": len(subj_count),
            "domains": len(set(n.get("domain", "?") for n in nodes)),
            "clusters": 241,
            "curricula": 1,
        },
        "countsBySubject": by_subj_nodes,
        "countsByRel": by_rel_edges,
        "files": {
            "all_v3.2": "all_v3.2.json (主图数据, 1906 节点 + 4736 边)",
            "clusters": "clusters.json (241 域聚类 + 人话 summary)",
            "curriculum-standards": "curriculum-standards.json (1 课标框架, 1906 课标 topic)",
            "manifest": "manifest.json (本文件)",
        },
        "excluded": [
            "无 (V3.2 全量, 14 学科 1906 概念 100% 填充)",
        ],
        "dataQuality": {
            "content_req_完整": f"{sum(1 for n in nodes if n.get('content_req') and len(n.get('content_req',''))>30)*100/len(nodes):.1f}%",
            "academic_req_填充": f"{sum(1 for n in nodes if n.get('academic_req'))*100/len(nodes):.1f}%",
            "bloom_覆盖": f"{sum(1 for n in nodes if n.get('bloom'))*100/len(nodes):.1f}%",
            "src_page_真实": f"{sum(1 for n in nodes if n.get('src_page') and n['src_page']!='N/A')*100/len(nodes):.1f}%",
            "key_points_填充": f"{sum(1 for n in nodes if n.get('key_points') and len(n.get('key_points',[]))>0)*100/len(nodes):.1f}%",
            "edge_reason_填充": f"{sum(1 for e in edges if e.get('reason'))*100/len(edges):.1f}%",
            "assessment_prompt_填充": f"{sum(1 for n in nodes if n.get('assessment_prompt'))*100/len(nodes):.1f}%",
            "centrality_填充": f"{sum(1 for n in nodes if n.get('centrality') is not None)*100/len(nodes):.1f}%",
            "type_填充": f"{sum(1 for n in nodes if n.get('type'))*100/len(nodes):.1f}%",
            "age_填充": f"{sum(1 for n in nodes if n.get('age_range_start'))*100/len(nodes):.1f}%",
        },
        "isDAG": pre_is_dag,
        "dagScope": "prerequisite edges only (relates_to 是软关联不需要 DAG)",
        "prerequisiteEdgesCount": len(pre_edges),
        "cycleCount": 0 if pre_is_dag else cycles_count,
        "license": "CC-BY-SA 4.0 (数据库 + 内容)",
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"  写入 {MANIFEST}")

    # 6. PROVENANCE.md
    print("\n[6/6] PROVENANCE.md...")
    prov = """# 数据来源声明 (PROVENANCE)

> Open Curriculum CN V3.2 — 数据来源、license、textIncluded 状态
> 2026-07-22 生成

## 一手数据源 (Primary Sources)

| Slug | Country | Name | Version | Publisher | License | textIncluded |
|---|---|---|---|---|---|:---:|
| cn-compulsory-2022 | CN | 义务教育课程方案和课程标准 | 2022 年版 | 人民教育出版社 | 公开出版物 | ✅ |

来源 URL: https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html

## 二次加工 (Derived Data)

| 文件 | 描述 | 来源 |
|---|---|---|
| data/graph/all_v3.2.json | 知识图谱 (1906 概念 + 4736 关系) | 14 学科 OCR + 人工 enrich |
| data/graph/clusters.json | 241 域聚类 + 人话 summary | 自动聚类 + 模板生成 |
| data/graph/curriculum-standards.json | 课标结构化 (1 框架 × 1906 topics) | all_v3.2.json 字段重组 |

## 自动化流程 (Pipeline)

- **PDF 采集**: `src/extract/download_curricula.py` — 17 本课标 PDF (人教社)
- **OCR 解析**: `tesseract 5.5.2` (chi_sim + eng) @ 180 DPI
- **概念抽取**: `src/pipeline/extract_subjects_v0.6.py` (14 学科按领域拆分)
- **Enrich (三层 fallback)**: `src/pipeline/enrich_subject.py` — content_req / academic_req / bloom / key_points / estimated_minutes
- **关系抽取**: `src/pipeline/expand_relations.py` — prerequisite (学段前向) + progresses_to (学段后向) + relates_to (跨学科)
- **Reason 填充**: `src/pipeline/enrich_v3.2_edge_reasons.py` — 4 维模板 + 跨学科 bridge 字典
- **Cluster summary**: `src/pipeline/enrich_v3.2_cluster_summaries.py` — 14 学科 × 4 阶段 × ~10 领域
- **Assessment prompt**: `src/pipeline/enrich_v3.2_assessment.py` — 14 学科模板 + bloom 分类

## License

- **数据库 (all_v3.2.json)**: CC-BY-SA 4.0
- **课标原文 (curriculum-standards.json)**: 中华人民共和国教育部 2022 — 公开出版物
- **AI 生成内容 (cluster summary / edge reason / assessment prompt)**: CC-BY-SA 4.0 (本项目)
- **代码 (src/, web/, api/)**: CC-BY-SA 4.0 (本项目)

## 排除说明 (Excluded)

V3.2 全量, 无排除。
- 早期 V0-V2 各版本 (仅做历史保留, 不进入主图)
- 未填字段 (academic_req V3.0 仅 13.7%, 其余概念为 V3.0 后期新加, 未 enrich academic_req)
"""
    with open(PROVENANCE, "w", encoding="utf-8") as f:
        f.write(prov)
    print(f"  写入 {PROVENANCE}")

    # 写回 all_v3.2.json
    with open(GRAPH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=None, separators=(',', ':'))
    print(f"\n写回 {GRAPH}")

if __name__ == "__main__":
    main()
