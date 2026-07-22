"""
V0.8 关系图谱验证 — 检查数据健康度, 输出 relations_report.json

校验项:
  1. 无悬空 (from/to 引用存在的节点)
  2. 无自环 (from == to)
  3. rel 字段合法 (prerequisite / progresses_to / relates_to)
  4. 统计: 总边数 / 按 rel 分类 / 跨学科 / 跨学段 / 同领域
  5. 孤儿节点统计 (无任何边)

输入: data/graph/all_v0.8.json
输出: data/graph/relations_report.json
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GRAPH_DIR = ROOT / "data" / "graph"
SRC = GRAPH_DIR / "all_v0.8.json"
REPORT = GRAPH_DIR / "relations_report.json"

VALID_REL = {"prerequisite", "progresses_to", "relates_to"}


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    nodes = data["nodes"]
    edges = data["edges"]
    node_map = {n["id"]: n for n in nodes}
    node_ids = set(node_map)

    # --- 校验 ---
    errors = {
        "self_loop": [],
        "dangling_from": [],
        "dangling_to": [],
        "invalid_rel": [],
        "duplicate": [],
        "backflow_prerequisite": [],  # 硬先决不应 backflow (from.stage > to.stage)
    }

    seen = set()
    for e in edges:
        f, t = e.get("from"), e.get("to")
        rel = e.get("rel")

        # 1. 自环
        if f == t:
            errors["self_loop"].append(e)
            continue

        # 2. 悬空
        if f not in node_ids:
            errors["dangling_from"].append(e)
            continue
        if t not in node_ids:
            errors["dangling_to"].append(e)
            continue

        # 3. rel 合法
        if rel not in VALID_REL:
            errors["invalid_rel"].append(e)

        # 4. 重复 (from, to)
        key = (f, t)
        if key in seen:
            errors["duplicate"].append(e)
        seen.add(key)

        # 5. backflow (硬先决不应 backflow)
        if rel == "prerequisite":
            fs = node_map[f].get("stage", 0)
            ts = node_map[t].get("stage", 0)
            if fs > ts and fs and ts:
                errors["backflow_prerequisite"].append((f, t, fs, ts))

    # --- 统计 ---
    rel_counts = Counter(e.get("rel", "MISSING") for e in edges)

    # 边结构
    by_structure = {
        "intra_domain": 0,   # 同领域同段
        "cross_stage": 0,    # 同领域跨段 (螺旋)
        "cross_subject": 0,  # 跨学科
    }
    for e in edges:
        if e.get("from") not in node_map or e.get("to") not in node_map:
            continue
        f = node_map[e["from"]]
        t = node_map[e["to"]]
        if f.get("subject") != t.get("subject"):
            by_structure["cross_subject"] += 1
        elif f.get("stage") != t.get("stage"):
            by_structure["cross_stage"] += 1
        else:
            by_structure["intra_domain"] += 1

    # 跨学科覆盖: 多少对 (subject_a, subject_b) 有边
    subj_pairs = set()
    for e in edges:
        if e.get("from") not in node_map or e.get("to") not in node_map:
            continue
        f = node_map[e["from"]]
        t = node_map[e["to"]]
        if f.get("subject") != t.get("subject"):
            pair = tuple(sorted([f["subject"], t["subject"]]))
            subj_pairs.add(pair)

    # 孤儿: in=0 AND out=0
    in_deg = defaultdict(int)
    out_deg = defaultdict(int)
    for e in edges:
        in_deg[e["to"]] += 1
        out_deg[e["from"]] += 1

    orphans_by_subj = defaultdict(int)
    total_orphans = 0
    for n in nodes:
        if in_deg[n["id"]] == 0 and out_deg[n["id"]] == 0:
            orphans_by_subj[n["subject"]] += 1
            total_orphans += 1

    # 各学科边数 (作为孤儿) — 用于对比 V0.7
    by_subject_edges = Counter()
    by_subject_nodes = Counter()
    for n in nodes:
        by_subject_nodes[n["subject"]] += 1
    for e in edges:
        if e.get("from") in node_map:
            by_subject_edges[node_map[e["from"]]["subject"]] += 1
        if e.get("to") in node_map:
            by_subject_edges[node_map[e["to"]]["subject"]] += 1
    # 一节点可能被多次计入 (in+out), 这里给一个更精确的: 节点参与的边数
    in_subj = Counter()
    out_subj = Counter()
    for e in edges:
        if e.get("from") in node_map:
            out_subj[node_map[e["from"]]["subject"]] += 1
        if e.get("to") in node_map:
            in_subj[node_map[e["to"]]["subject"]] += 1

    # --- 报告 ---
    report = {
        "version": "v0.8",
        "generated_at": "2026-07-23",
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "by_rel": dict(rel_counts),
            "by_structure": by_structure,
            "total_orphans": total_orphans,
            "orphan_rate": round(total_orphans / len(nodes) * 100, 1) if nodes else 0,
            "cross_subject_pairs_covered": len(subj_pairs),
            "cross_subject_pairs_possible": 91,  # C(14,2)
            "cross_subject_coverage_pct": round(len(subj_pairs) / 91 * 100, 1),
        },
        "errors": {k: len(v) for k, v in errors.items()},
        "error_details": {
            "self_loop": errors["self_loop"][:5],
            "dangling_from": errors["dangling_from"][:5],
            "dangling_to": errors["dangling_to"][:5],
            "invalid_rel": errors["invalid_rel"][:5],
            "duplicate": errors["duplicate"][:5],
            "backflow_prerequisite": errors["backflow_prerequisite"][:10],
        },
        "by_subject": {},
        "cross_subject_pairs": sorted([list(p) for p in subj_pairs]),
    }

    # 各学科详情
    for subj in sorted(by_subject_nodes.keys()):
        nodes_n = by_subject_nodes[subj]
        in_n = in_subj.get(subj, 0)
        out_n = out_subj.get(subj, 0)
        report["by_subject"][subj] = {
            "nodes": nodes_n,
            "in_edges": in_n,
            "out_edges": out_n,
            "avg_in": round(in_n / nodes_n, 3) if nodes_n else 0,
            "avg_out": round(out_n / nodes_n, 3) if nodes_n else 0,
            "orphans": orphans_by_subj.get(subj, 0),
            "orphan_rate_pct": round(orphans_by_subj.get(subj, 0) / nodes_n * 100, 1) if nodes_n else 0,
        }

    # --- 写报告 ---
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # --- 控制台输出 ---
    print(f"📊 V0.8 关系图谱报告 ({SRC.name})")
    print(f"\n总节点: {len(nodes)}, 总边: {len(edges)}")
    print(f"\n按 rel 分类:")
    for r in ["prerequisite", "progresses_to", "relates_to"]:
        print(f"  {r}: {rel_counts.get(r, 0)}")
    print(f"\n按结构分类:")
    for k, v in by_structure.items():
        print(f"  {k}: {v}")
    print(f"\n跨学科覆盖: {len(subj_pairs)}/91 对 ({round(len(subj_pairs)/91*100, 1)}%)")
    print(f"\n错误检查:")
    for k, v in errors.items():
        marker = "✓" if len(v) == 0 else "✗"
        print(f"  {marker} {k}: {len(v)}")

    print(f"\n孤儿节点: {total_orphans} / {len(nodes)} ({round(total_orphans/len(nodes)*100, 1)}%)")
    print(f"\n各学科:")
    print(f"  {'学科':<15} {'节点':>5} {'in':>4} {'out':>4} {'avg_in':>7} {'avg_out':>7} {'孤儿':>5} {'孤儿率':>7}")
    for subj, info in sorted(report["by_subject"].items(), key=lambda x: -x[1]["orphans"]):
        print(f"  {subj:<15} {info['nodes']:>5} {info['in_edges']:>4} {info['out_edges']:>4} "
              f"{info['avg_in']:>7} {info['avg_out']:>7} {info['orphans']:>5} {info['orphan_rate_pct']:>6}%")

    print(f"\n✅ 报告写入: {REPORT}")


if __name__ == "__main__":
    main()
