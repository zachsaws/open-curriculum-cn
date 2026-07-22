"""
V3.0 合并脚本 — 把 14 学科 {subject}_v3.0.json 合并到 all_v3.0.json
- 保留 V0.8.bak 的所有关系 (跨学段/跨学科)
- 加入所有 V3.0 新概念
- 跑 schema 验证
- 输出: data/graph/all_v3.0.json
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent.parent
GRAPH_DIR = ROOT / "data" / "graph"

SUBJECTS = ['math', 'chinese', 'english', 'physics', 'chemistry', 'biology',
            'history', 'geography', 'morality_law', 'science', 'info_tech',
            'art', 'pe_health', 'labor']


def main():
    print("=" * 70)
    print("V3.0 合并 — 14 学科 → all_v3.0.json")
    print("=" * 70)

    # 优先读已有 all_v3.0.json (保留已有 relations), 否则读 V0.8
    all_v3_path = GRAPH_DIR / 'all_v3.0.json'
    all_v08_path = GRAPH_DIR / 'all_v0.8.json.bak'

    if all_v3_path.exists():
        with open(all_v3_path) as f:
            base = json.load(f)
        print(f"  V3.0 基础: {len(base['nodes'])} 节点, {len(base['edges'])} 关系")
    elif all_v08_path.exists():
        with open(all_v08_path) as f:
            base = json.load(f)
        print(f"  V0.8 基础: {len(base['nodes'])} 节点, {len(base['edges'])} 关系")
    else:
        with open(GRAPH_DIR / 'all_v0.8.json') as f:
            base = json.load(f)
        print(f"  V0.8 基础: {len(base['nodes'])} 节点, {len(base['edges'])} 关系")

    # 收集所有 V3.0 概念
    all_v30_nodes = []
    base_ids = {n['id'] for n in base['nodes']}
    print(f"  基础 ID 数: {len(base_ids)}")

    for subject in SUBJECTS:
        v30_path = GRAPH_DIR / f"{subject}_v3.0.json"
        if not v30_path.exists():
            print(f"  ⚠️ {subject} V3.0 缺失")
            continue
        with open(v30_path) as f:
            d = json.load(f)
        nodes = d['nodes']
        # 查重 (但 V3.0 基础已有同样节点的, 不重复添加 — 保留 V3.0 enrich 后的)
        new_count = 0
        for n in nodes:
            if n['id'] not in base_ids:
                all_v30_nodes.append(n)
                base_ids.add(n['id'])
                new_count += 1
        print(f"  {subject:14s}: {len(nodes)} 节点 (+{new_count} 新)")

    # 合并节点 (基础已有, 新概念追加; 但用 V3.0 文件的节点覆盖 — 保留 enrich 后的字段)
    by_id = {n['id']: n for n in base['nodes']}
    for n in all_v30_nodes:
        by_id[n['id']] = n
    # 但 V3.0 单学科文件中的概念应该覆盖基础版本
    # 先读单学科文件, 覆盖
    for subject in SUBJECTS:
        v30_path = GRAPH_DIR / f"{subject}_v3.0.json"
        if not v30_path.exists():
            continue
        with open(v30_path) as f:
            d = json.load(f)
        for n in d['nodes']:
            by_id[n['id']] = n

    merged_nodes = list(by_id.values())
    # 合并边 — 保留基础 (V3.0) 所有边
    merged_edges = list(base['edges'])
    print(f"\n  合并后: {len(merged_nodes)} 节点, {len(merged_edges)} 关系")

    # Schema 验证
    issues = []
    seen_ids = set()
    for n in merged_nodes:
        if n['id'] in seen_ids:
            issues.append(f"重复 ID: {n['id']}")
        seen_ids.add(n['id'])
        # 必填字段
        for f in ['id', 'subject', 'title', 'stage', 'grade_start', 'grade_end',
                  'domain', 'subdomain', 'difficulty', 'summary', 'content_req',
                  'src_page', 'src_stage', 'bloom']:
            if f not in n:
                issues.append(f"{n['id']} 缺字段 {f}")
        # 学段合法性
        if n.get('stage') not in [1, 2, 3, 4]:
            issues.append(f"{n['id']} 非法 stage={n.get('stage')}")
        # 年级范围
        gs = n.get('grade_start', 0)
        ge = n.get('grade_end', 0)
        if not (1 <= gs <= 9 and 1 <= ge <= 9 and gs <= ge):
            issues.append(f"{n['id']} 非法年级范围: {gs}-{ge}")
        # bloom 非空
        if not n.get('bloom'):
            issues.append(f"{n['id']} bloom 为空")
        # content_req 长度
        if not n.get('content_req') or len(n['content_req']) < 5:
            issues.append(f"{n['id']} content_req 短: {n.get('content_req', '')[:30]}")

    # 边验证
    for e in merged_edges:
        fr = e.get('from') if 'from' in e else e[0]
        to = e.get('to') if 'to' in e else e[1]
        if fr == to:
            issues.append(f"自环边: {fr}")
        if fr not in seen_ids:
            issues.append(f"边 from 引用不存在: {fr}")
        if to not in seen_ids:
            issues.append(f"边 to 引用不存在: {to}")

    print(f"\n  Schema 验证: {len(issues)} 个问题")
    for iss in issues[:20]:
        print(f"    ⚠️ {iss}")
    if len(issues) > 20:
        print(f"    ... 还有 {len(issues) - 20} 个")

    # 输出
    out = {'nodes': merged_nodes, 'edges': merged_edges}
    out_path = GRAPH_DIR / 'all_v3.0.json'
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n  📁 输出: {out_path}")

    # 统计
    by_subject = defaultdict(int)
    for n in merged_nodes:
        by_subject[n['subject']] += 1
    print(f"\n  学科分布:")
    for s in SUBJECTS:
        print(f"    {s:14s}: {by_subject[s]}")
    print(f"  {'总计':14s}: {sum(by_subject.values())}")

    if issues:
        print(f"\n  ❌ {len(issues)} 个问题, 请修复")
        sys.exit(1)
    print(f"\n  ✅ all_v3.0.json 验证通过")


if __name__ == "__main__":
    main()
