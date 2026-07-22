"""V0.7 合并 — 用 math_v0.7 替换 all_v0.6 的数学部分"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GRAPH_DIR = ROOT / "data" / "graph"


def main():
    with open(GRAPH_DIR / "all_v0.6.json") as f:
        old = json.load(f)
    with open(GRAPH_DIR / "math_v0.7.json") as f:
        new_math = json.load(f)
    # 替换数学节点
    new_nodes = [n for n in old["nodes"] if n["subject"] != "math"] + new_math["nodes"]
    # 数学 edges 保持
    new_edges = [e for e in old["edges"]]
    print(f"V0.7: {len(new_nodes)} nodes, {len(new_edges)} edges")
    by_subj = {}
    for n in new_nodes:
        by_subj.setdefault(n["subject"], 0)
        by_subj[n["subject"]] += 1
    for s, n in sorted(by_subj.items(), key=lambda x: -x[1]):
        print(f"  {s}: {n}")
    out = {"nodes": new_nodes, "edges": new_edges}
    with open(GRAPH_DIR / "all_v0.7.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nwritten: {GRAPH_DIR / 'all_v0.7.json'}")


if __name__ == "__main__":
    main()
