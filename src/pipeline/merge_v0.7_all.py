"""V0.7 全量合并 — 14 学科 V0.7 合并到 all_v0.7.json"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GRAPH_DIR = ROOT / "data" / "graph"

SUBJECTS = ['math', 'chinese', 'english', 'physics', 'chemistry', 'biology',
            'history', 'geography', 'morality_law', 'science',
            'info_tech', 'art', 'pe_health', 'labor']


def main():
    # 读 all_v0.6.json 拿 edges
    with open(GRAPH_DIR / "all_v0.6.json") as f:
        old = json.load(f)
    edges = old['edges']

    # 合并 14 学科 V0.7
    all_nodes = []
    for s in SUBJECTS:
        path = GRAPH_DIR / f"{s}_v0.7.json"
        if not path.exists():
            print(f"⚠️ {s}_v0.7.json 不存在, 跳过")
            continue
        with open(path) as f:
            data = json.load(f)
        all_nodes.extend(data['nodes'])
        print(f"  {s}: {len(data['nodes'])} 概念")

    # 去重
    seen = set()
    unique = []
    for n in all_nodes:
        if n['id'] in seen:
            print(f"  DUPLICATE: {n['id']}")
            continue
        seen.add(n['id'])
        unique.append(n)
    all_nodes = unique

    print(f"\n总计: {len(all_nodes)} 概念 + {len(edges)} 关系")
    out = {"nodes": all_nodes, "edges": edges}
    with open(GRAPH_DIR / "all_v0.7.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"written: {GRAPH_DIR / 'all_v0.7.json'}")


if __name__ == "__main__":
    main()
