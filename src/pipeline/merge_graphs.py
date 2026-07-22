"""
合并所有学科 V0.1 图谱为总 graph.json
"""
import json
from pathlib import Path
from datetime import datetime

GRAPH_DIR = Path(__file__).parent.parent.parent / "data" / "graph"
WEB_DATA = Path(__file__).parent.parent.parent / "web" / "data"
WEB_DATA.mkdir(parents=True, exist_ok=True)

def main():
    files = sorted(GRAPH_DIR.glob("*_v0.1.json"))
    print(f"找到 {len(files)} 个学科图谱")

    all_nodes = []
    all_edges = []
    edge_set = set()
    subjects_count = {}

    for f in files:
        g = json.loads(f.read_text())
        for n in g["nodes"]:
            all_nodes.append(n)
        for e in g["edges"]:
            edge_key = (e[0], e[1])
            if edge_key in edge_set:
                continue
            edge_set.add(edge_key)
            all_edges.append(e)
        subjects_count[g["subject"]] = g["node_count"]

    # 验证
    node_ids = {n["id"] for n in all_nodes}
    valid_edges = []
    for f, t, w in all_edges:
        if f in node_ids and t in node_ids:
            valid_edges.append([f, t, w])
        else:
            print(f"  WARN: 边 {f}->{t} 节点缺失")

    total = {
        "version": "0.5.0",
        "scope": "义教 1-9 年级 (课标 2022 版) - 全部 14 门学科",
        "subjects": list(subjects_count.keys()),
        "subjects_count": subjects_count,
        "node_count": len(all_nodes),
        "edge_count": len(valid_edges),
        "nodes": all_nodes,
        "edges": valid_edges,
        "generated_at": datetime.now().isoformat(),
        "license": "CC-BY-SA 4.0",
        "data_sources": [
            "教育部 2022 义教课标 16 门 (17 PDF)",
            "人教版 / 部编版教材目录结构",
        ],
    }

    out = GRAPH_DIR / "all_v0.5.json"
    out.write_text(json.dumps(total, ensure_ascii=False, indent=1))
    web_out = WEB_DATA / "graph.json"
    web_out.write_text(json.dumps(total, ensure_ascii=False, indent=1))

    print(f"\n✅ 合并完成: {len(all_nodes)} 概念, {len(valid_edges)} 关系")
    print(f"   学科: {len(subjects_count)}")
    for s, c in subjects_count.items():
        print(f"     - {s}: {c} 概念")
    print(f"\n   输出: {out}")
    print(f"   Web:  {web_out}")

if __name__ == "__main__":
    main()
