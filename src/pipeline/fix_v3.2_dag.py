"""
修复 V3.2 prerequisite 边成环问题
- 找所有 A->B 和 B->A 互为先决的边
- 找所有环里的"非最长链"边
- 降级为 relates_to (保留数据, 但不算 prerequisite DAG)
"""
import json
from pathlib import Path
import networkx as nx
from collections import deque, Counter

ROOT = Path(__file__).parent.parent.parent
GRAPH = ROOT / "data" / "graph" / "all_v3.2.json"

def find_cycles_iter(G, max_cycles=200):
    """迭代找环, 限制 max_cycles"""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in G.nodes()}
    cycles = []
    def dfs(u, path, depth):
        if len(cycles) >= max_cycles: return
        if depth > 10: return  # 限制深度
        color[u] = GRAY
        for v in G.successors(u):
            if color[v] == GRAY:
                idx = path.index(v) if v in path else 0
                cycles.append(path[idx:] + [v])
            elif color[v] == WHITE:
                dfs(v, path + [v], depth + 1)
            if len(cycles) >= max_cycles: return
        color[u] = BLACK
    for n in list(G.nodes()):
        if color[n] == WHITE:
            dfs(n, [n], 0)
            if len(cycles) >= max_cycles: break
    return cycles

def main():
    print(f"读 {GRAPH}")
    with open(GRAPH) as f:
        d = json.load(f)
    nodes = d["nodes"]
    edges = d["edges"]

    # 1. 直接反向 A↔B
    ab_set = set()
    reverse_pairs = set()  # 排序后的 (A, B) 集合
    for e in edges:
        if e.get("rel") == "prerequisite":
            if (e["to"], e["from"]) in ab_set:
                # 互为先决
                pair = tuple(sorted([e["from"], e["to"]]))
                reverse_pairs.add(pair)
            ab_set.add((e["from"], e["to"]))
    print(f"直接 A↔B 对: {len(reverse_pairs)}")

    # 2. 找环 (限制 200)
    G_pre = nx.DiGraph()
    for n in nodes:
        G_pre.add_node(n["id"])
    for e in edges:
        if e.get("rel") == "prerequisite":
            G_pre.add_edge(e["from"], e["to"])

    cycles = find_cycles_iter(G_pre, 200)
    print(f"找到 {len(cycles)} 个环 (上限 200)")

    # 3. 把环里的边降级为 relates_to
    # 策略: 对每条环上出现的边, 数它出现在多少个环里
    edge_in_cycles = Counter()
    for c in cycles:
        # 环: a -> b -> c -> a
        # 边: a->b, b->c, c->a
        for i in range(len(c) - 1):
            edge_in_cycles[(c[i], c[i+1])] += 1
    print(f"环涉及的边数: {len(edge_in_cycles)}")

    # 4. 标记要降级: 出现在 1+ 个环里的边
    downgraded = 0
    for e in edges:
        if e.get("rel") != "prerequisite":
            continue
        # A↔B 直接反向: 直接降级
        pair = tuple(sorted([e["from"], e["to"]]))
        if pair in reverse_pairs:
            e["rel"] = "relates_to"
            e["reason"] = e.get("reason", "") + " (原 prerequisite, 因互为反向被降级为软关联)"
            downgraded += 1
            continue
        # 环里: 降级出现 >= 1 次的边
        if edge_in_cycles.get((e["from"], e["to"]), 0) > 0:
            e["rel"] = "relates_to"
            e["reason"] = e.get("reason", "") + " (原 prerequisite, 因环检测被降级为软关联)"
            downgraded += 1

    print(f"降级 prerequisite→relates_to: {downgraded}")

    # 5. 重新验证
    pre_edges = [e for e in edges if e.get("rel") == "prerequisite"]
    print(f"剩余 prerequisite: {len(pre_edges)}")
    G2 = nx.DiGraph()
    for n in nodes:
        G2.add_node(n["id"])
    for e in pre_edges:
        G2.add_edge(e["from"], e["to"])
    in_deg = {n: 0 for n in G2.nodes()}
    for u, v in G2.edges():
        in_deg[v] = in_deg.get(v, 0) + 1
    queue = deque([n for n, d in in_deg.items() if d == 0])
    visited = 0
    while queue:
        u = queue.popleft()
        visited += 1
        for v in G2.successors(u):
            in_deg[v] -= 1
            if in_deg[v] == 0:
                queue.append(v)
    is_dag = (visited == G2.number_of_nodes())
    print(f"修复后 prerequisite DAG: {is_dag}, visited {visited}/{G2.number_of_nodes()}")

    # 6. 写回
    rel_cnt = Counter(e.get("rel") for e in edges)
    print(f"修复后边类型分布: {dict(rel_cnt)}")

    with open(GRAPH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=None, separators=(',', ':'))
    print(f"写回 {GRAPH}")

if __name__ == "__main__":
    main()
