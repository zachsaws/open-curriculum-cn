"""
V3.0 关系扩充 — 把 Open Curriculum CN 关系数从 299 扩到 500+

输入:
  - data/graph/all_v0.8.json   (V0.8 基础: 758 概念, 299 关系)
  - data/graph/all_v3.0.json   (V3.0 概念: 1906 概念, 由 expand_concepts sub-agent 生成)
                                如果不存在, fallback 到 all_v0.8.json

输出:
  - data/graph/all_v3.0.json   (V3.0 完整图: 1906 概念, 500+ 关系)
  - 备份: all_v0.8.json.bak

边 schema:
  {
    "id": "e_NNN",            # 自动生成, 4 位数字
    "from": "<node_id>",
    "to": "<node_id>",
    "rel": "prerequisite" | "progresses_to" | "relates_to",
    "source": "curriculum" | "domain_logic",
    "weight": 1.0 | 0.8 | 0.5,
    "rationale": "<short reason>"
  }

权重:
  - prerequisite  = 1.0  (硬先决, 同学科同领域)
  - progresses_to = 0.8  (跨学段螺旋, 同学科跨学段)
  - relates_to    = 0.5  (跨学科软关联, 跨学科)

策略:
  0. 备份 V0.8 → all_v0.8.json.bak
  1. 加载 V0.8 基础边 (299), 补完整字段
  2. A) 同学科同领域 prerequisite (按学段, 链式前后缀)
  3. B) 跨学段 progresses_to (学段 + 领域, 螺旋上升)
  4. C) 跨学科 relates_to (重点学科对, 关键词匹配)
  5. 去重, 写入 all_v3.0.json
  6. 输出报告: relations_v3.0_report.json

用法:
  python src/pipeline/expand_relations.py
  # 或 dry-run (不写):
  python src/pipeline/expand_relations.py --dry-run
"""

import json
import re
import shutil
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

ROOT = Path(__file__).parent.parent.parent
GRAPH_DIR = ROOT / "data" / "graph"
SRC_V08 = GRAPH_DIR / "all_v0.8.json"
SRC_V30 = GRAPH_DIR / "all_v3.0.json"
DST_V30 = GRAPH_DIR / "all_v3.0.json"
BAK_V08 = GRAPH_DIR / "all_v0.8.json.bak"
REPORT = GRAPH_DIR / "relations_v3.0_report.json"

VALID_REL = {"prerequisite", "progresses_to", "relates_to"}
REL_WEIGHT = {"prerequisite": 1.0, "progresses_to": 0.8, "relates_to": 0.5}
SUBJECT_PREFIX = {
    'math': 'M', 'chinese': 'CN', 'english': 'EN',
    'physics': 'P', 'chemistry': 'CH', 'biology': 'B',
    'history': 'H', 'geography': 'G', 'morality_law': 'ML',
    'science': 'SC', 'info_tech': 'IT', 'art': 'ART',
    'pe_health': 'PE', 'labor': 'L',
}

# 跨学科关联优先级 (curriculum 设计意图)
LINK_PAIRS = [
    # math 系
    ('math', 'physics', 'M-P',  'math→physics: 速度/压强/浮力/杠杆/功/能/欧姆/比例/函数/三角函数'),
    ('math', 'chemistry', 'M-CH', 'math→chemistry: 化学式/比例/百分数/方程/函数/守恒'),
    ('math', 'biology', 'M-B',  'math→biology: 统计/比例/指数/对数/正比/反比'),
    ('math', 'info_tech', 'M-IT', 'math→info_tech: 布尔/二进制/算法/函数/对数/统计'),
    ('math', 'geography', 'M-G',  'math→geography: 统计/比例/经纬度/地图比例尺'),
    # chinese 系
    ('chinese', 'history', 'CN-H', 'chinese→history: 古诗/文言文 → 朝代'),
    ('chinese', 'morality_law', 'CN-ML', 'chinese→morality_law: 议论文 → 法治'),
    ('chinese', 'english', 'CN-EN', 'chinese↔english: 文化对比/互译'),
    # science 系
    ('physics', 'chemistry', 'P-CH', 'physics↔chemistry: 物质结构/能量/守恒'),
    ('physics', 'biology', 'P-B',  'physics→biology: 能量流动/生物电'),
    ('chemistry', 'biology', 'CH-B', 'chemistry↔biology: 元素/分子/化合物'),
    # info_tech
    ('info_tech', 'math', 'IT-M', 'info_tech→math: 计算思维/逻辑/算法'),
    # geography
    ('geography', 'biology', 'G-B', 'geography→biology: 生态/生物多样性'),
    # history
    ('history', 'morality_law', 'H-ML', 'history→morality_law: 制度沿革/法治变迁'),
    # 综合
    ('science', 'math', 'SC-M', 'science→math: 数据/测量/统计'),
    ('science', 'physics', 'SC-P', 'science→physics: 物质/能量'),
    ('science', 'chemistry', 'SC-CH', 'science→chemistry: 物质变化'),
    ('science', 'biology', 'SC-B', 'science→biology: 生命/生态'),
    ('pe_health', 'biology', 'PE-B', 'pe_health→biology: 运动生理/人体结构'),
    ('pe_health', 'science', 'PE-SC', 'pe_health→science: 力学基础'),
    ('pe_health', 'morality_law', 'PE-ML', 'pe_health→morality_law: 体育精神/规则'),
    ('art', 'chinese', 'ART-CN', 'art→chinese: 古诗配画/文学意境'),
    ('art', 'history', 'ART-H', 'art→history: 艺术史/朝代'),
    ('art', 'morality_law', 'ART-ML', 'art→morality_law: 美育/价值观'),
    ('labor', 'science', 'L-SC', 'labor→science: 技术原理'),
    ('labor', 'info_tech', 'L-IT', 'labor→info_tech: 数字化生产'),
    ('english', 'history', 'EN-H', 'english→history: 文化背景'),
    ('english', 'geography', 'EN-G', 'english→geography: 国际视野'),
    ('english', 'chinese', 'EN-CN', 'english↔chinese: 跨文化'),
]


# ============================================================================
# Helpers
# ============================================================================

def title_keywords(t, min_len=2, max_len=4):
    """提取标题关键词 (2-4 字中文/英文)"""
    if not t:
        return set()
    return set(re.findall(r'[\u4e00-\u9fa5A-Za-z]+', t))


def normalize_title(t):
    if not t:
        return ''
    return re.sub(r'[\s（）()【】《》、,。.!?;；:：·]', '', t)[:10]


def stage_to_range(stage):
    return {1: (1, 2), 2: (3, 4), 3: (5, 6), 4: (7, 9)}.get(stage, (1, 2))


def stage_to_grade_str(stage):
    if stage == 1:
        return "G1-2"
    if stage == 2:
        return "G3-4"
    if stage == 3:
        return "G5-6"
    return "G7-9"


# ============================================================================
# Step 0: 备份
# ============================================================================

def backup_v08():
    if not BAK_V08.exists():
        shutil.copy2(SRC_V08, BAK_V08)
        print(f"  备份: {SRC_V08} → {BAK_V08}")
    else:
        # 已存在, 跳过 (不覆盖)
        print(f"  备份已存在, 跳过: {BAK_V08}")


# ============================================================================
# 边补全: 给现有边加 id/source/weight/rationale
# ============================================================================

def enrich_existing_edge(e, idx):
    """给现有边加完整字段, 返回 (id, edge_dict)"""
    rel = e.get("rel")
    if rel not in VALID_REL:
        rel = "relates_to"  # 容错: 默认

    # 保留已有 source/rationale (V0.8 132 条)
    src = e.get("source", "curriculum" if rel in ("prerequisite", "progresses_to") else "domain_logic")
    rationale = e.get("rationale")
    if not rationale:
        # 自动生成
        if rel == "prerequisite":
            rationale = f"{e['from']} → {e['to']} (同领域硬先决)"
        elif rel == "progresses_to":
            rationale = f"{e['from']} → {e['to']} (跨学段螺旋)"
        else:
            rationale = f"{e['from']} → {e['to']} (跨学科软关联)"

    weight = e.get("weight", REL_WEIGHT[rel])
    # 规整化 weight 到 3 种标准值
    if rel == "prerequisite":
        weight = 1.0
    elif rel == "progresses_to":
        weight = 0.8
    else:
        weight = 0.5

    return {
        "id": f"e_{idx:04d}",
        "from": e["from"],
        "to": e["to"],
        "rel": rel,
        "source": src,
        "weight": weight,
        "rationale": rationale,
    }


# ============================================================================
# Step 2A: 同学科同领域 prerequisite (链式)
# ============================================================================

def gen_intra_subject_prerequisite(nodes, existing):
    """同 (subject, stage, domain) 内, 按 ID 序号链式 prerequisite"""
    by_key = defaultdict(list)
    for n in nodes:
        m = re.match(r'^([A-Z]+_[A-Z]+\d+|\w+)_(.+)$', n['id'])
        # 简化: 用 (subject, stage, domain) 分组
        key = (n['subject'], n.get('stage'), n.get('domain'))
        by_key[key].append(n)

    new_edges = []
    seen = set(existing)
    for key, group in by_key.items():
        # 按 id 排序
        group = sorted(group, key=lambda x: x['id'])
        for i in range(len(group) - 1):
            a, b = group[i], group[i + 1]
            edge_key = (a['id'], b['id'], 'prerequisite')
            if edge_key in seen or a['id'] == b['id']:
                continue
            seen.add(edge_key)
            stage = a.get('stage', 1)
            grade_str = stage_to_grade_str(stage)
            rationale = f"{a['title']} → {b['title']} ({grade_str} 同领域硬先决)"
            new_edges.append({
                "from": a['id'],
                "to": b['id'],
                "rel": "prerequisite",
                "source": "curriculum",
                "weight": 1.0,
                "rationale": rationale,
            })
    return new_edges, seen


# ============================================================================
# Step 2B: 跨学段 progresses_to (同 subject 跨 stage, 同 domain 螺旋)
# ============================================================================

def gen_cross_stage_progresses(nodes, existing):
    """同 subject 同 domain 跨 stage → progresses_to

    扩展: 对只有 stage 4 的学科 (history/geography/physics/chemistry/biology),
    在 stage 4 内按"时期"螺旋 (古代→近代→现代 / 物质→反应→应用 等)
    """
    by_key = defaultdict(list)
    for n in nodes:
        key = (n['subject'], n.get('domain'))
        by_key[key].append(n)

    # 按 stage 分组
    by_subject_domain_stage = defaultdict(lambda: defaultdict(list))
    for (subj, dom), ns in by_key.items():
        for n in ns:
            by_subject_domain_stage[(subj, dom)][n.get('stage', 1)].append(n)

    new_edges = []
    seen = set(existing)
    for (subj, dom), stage_map in by_subject_domain_stage.items():
        # 对每个 (subj, dom), 跨 stage 取代表螺旋
        for st_from in range(1, 4):  # 1->2, 2->3, 3->4
            st_to = st_from + 1
            if st_from not in stage_map or st_to not in stage_map:
                continue
            # 从 from 阶段取代表 (选有意义的)
            for n_from in stage_map[st_from]:
                # 在 to 阶段找一个最相关的 (按关键词匹配)
                kw_from = title_keywords(n_from.get('title', ''))
                if not kw_from:
                    continue
                best = None
                best_match = 0
                for n_to in stage_map[st_to]:
                    kw_to = title_keywords(n_to.get('title', ''))
                    common = len(kw_from & kw_to)
                    if common > best_match:
                        best = n_to
                        best_match = common
                if not best or best_match < 1:
                    continue
                edge_key = (n_from['id'], best['id'], 'progresses_to')
                if edge_key in seen or n_from['id'] == best['id']:
                    continue
                seen.add(edge_key)
                g_from = stage_to_grade_str(st_from)
                g_to = stage_to_grade_str(st_to)
                rationale = f"{n_from['title']} → {best['title']} ({g_from} → {g_to} 同领域螺旋)"
                new_edges.append({
                    "from": n_from['id'],
                    "to": best['id'],
                    "rel": "progresses_to",
                    "source": "curriculum",
                    "weight": 0.8,
                    "rationale": rationale,
                })

    # === 兜底: stage 4 内的"时期"螺旋 (历史/地理/物理/化学/生物) ===
    # 在同 subject 同 domain 内, 按 ID 序号链式, 但不重复 prerequisite 的 (from, to)
    for (subj, dom), stage_map in by_subject_domain_stage.items():
        if 4 not in stage_map or len(stage_map[4]) < 2:
            continue
        # 按 id 排序
        nodes_sorted = sorted(stage_map[4], key=lambda x: x['id'])
        for i in range(len(nodes_sorted) - 1):
            a, b = nodes_sorted[i], nodes_sorted[i + 1]
            edge_key = (a['id'], b['id'], 'progresses_to')
            if edge_key in seen or a['id'] == b['id']:
                continue
            # 只在同 domain 但不同 subdomain 时加 (避免和 prerequisite 重叠)
            if a.get('subdomain') == b.get('subdomain'):
                continue
            seen.add(edge_key)
            rationale = f"{a['title']} → {b['title']} (G7-9 时期螺旋)"
            new_edges.append({
                "from": a['id'],
                "to": b['id'],
                "rel": "progresses_to",
                "source": "curriculum",
                "weight": 0.8,
                "rationale": rationale,
            })
    return new_edges, seen


# ============================================================================
# Step 2C: 跨学科 relates_to
# ============================================================================

def gen_cross_subject_relates(nodes, existing, max_total=2500):
    """跨学科 relates_to — 重点学科对, 关键词 + subdomain 匹配 + round-robin 兜底"""
    by_subj_stage = defaultdict(list)
    for n in nodes:
        by_subj_stage[(n['subject'], n.get('stage', 1))].append(n)

    new_edges = []
    seen = set(existing)
    existing_subjects = set(s for (s, _) in by_subj_stage.keys())

    for s1, s2, label, desc in LINK_PAIRS:
        if s1 not in existing_subjects or s2 not in existing_subjects:
            continue
        if len(new_edges) >= max_total:
            break
        # 同 stage 跨学科
        for stage in [1, 2, 3, 4]:
            if len(new_edges) >= max_total:
                break
            nodes1 = by_subj_stage.get((s1, stage), [])
            nodes2 = by_subj_stage.get((s2, stage), [])
            if not nodes1 or not nodes2:
                continue
            # 索引 n2 by domain/subdomain
            n2_by_sub = defaultdict(list)
            for n2 in nodes2:
                sub_key = (n2.get('domain', ''), n2.get('subdomain', ''))
                n2_by_sub[sub_key].append(n2)
            n2_round_robin_idx = [0]
            for n1 in nodes1:
                if len(new_edges) >= max_total:
                    break
                kw1 = title_keywords(n1.get('title', ''))
                best = None
                best_match = 0
                # 1) 同 subdomain 关键词匹配
                sub_key = (n1.get('domain', ''), n1.get('subdomain', ''))
                for n2 in n2_by_sub.get(sub_key, []):
                    kw2 = title_keywords(n2.get('title', ''))
                    common = len(kw1 & kw2)
                    if common > best_match:
                        best = n2
                        best_match = common
                # 2) 同 domain 关键词匹配
                if not best or best_match < 1:
                    n2_in_domain = [n for k, ns in n2_by_sub.items()
                                     if k[0] == n1.get('domain', '') for n in ns]
                    for n2 in n2_in_domain:
                        kw2 = title_keywords(n2.get('title', ''))
                        common = len(kw1 & kw2)
                        if common > best_match:
                            best = n2
                            best_match = common
                # 3) 跨 domain 关键词匹配
                if not best or best_match < 1:
                    for n2 in nodes2:
                        kw2 = title_keywords(n2.get('title', ''))
                        common = len(kw1 & kw2)
                        if common > best_match:
                            best = n2
                            best_match = common
                # 4) round-robin 兜底 — 保证每个 n1 至少有 1 条
                if not best:
                    best = nodes2[n2_round_robin_idx[0] % len(nodes2)]
                    n2_round_robin_idx[0] += 1
                edge_key = (n1['id'], best['id'], 'relates_to')
                if edge_key in seen or n1['id'] == best['id']:
                    continue
                seen.add(edge_key)
                grade_str = stage_to_grade_str(stage)
                rationale = f"{n1['title']} ↔ {best['title']} ({label} {grade_str} 跨学科软关联)"
                new_edges.append({
                    "from": n1['id'],
                    "to": best['id'],
                    "rel": "relates_to",
                    "source": "domain_logic",
                    "weight": 0.5,
                    "rationale": rationale,
                })
    return new_edges, seen


# ============================================================================
# 去重 + 验证
# ============================================================================

def deduplicate(edges):
    """按 (from, to, rel) 去重, 保留第一个 (含 id)"""
    seen = set()
    out = []
    for e in edges:
        key = (e['from'], e['to'], e['rel'])
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def reassign_ids(edges):
    """重排 id 为 e_NNN (0001, 0002, ...)"""
    for i, e in enumerate(edges, 1):
        e['id'] = f"e_{i:04d}"
    return edges


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="不写文件")
    parser.add_argument("--max-relates", type=int, default=2500, help="跨学科 relates_to 上限")
    args = parser.parse_args()

    print("=" * 70)
    print("V3.0 关系扩充")
    print("=" * 70)

    # 0. 备份
    backup_v08()

    # 1. 加载
    with open(SRC_V08, encoding="utf-8") as f:
        v08 = json.load(f)
    print(f"\n  基础: V0.8 = {len(v08['nodes'])} 节点, {len(v08['edges'])} 边")

    # V3.0 概念: 优先 all_v3.0.json (expand_concepts sub-agent 产物), 否则用 V0.8
    if SRC_V30.exists():
        with open(SRC_V30, encoding="utf-8") as f:
            v30 = json.load(f)
        # 但只取 V3.0 的 nodes
        v30_nodes = v30.get("nodes", [])
        # 兼容: 如果 V3.0 的 nodes 不够, fallback V0.8
        if len(v30_nodes) >= len(v08['nodes']):
            nodes = v30_nodes
            print(f"  V3.0 概念: {len(nodes)} 节点 (来自 all_v3.0.json)")
        else:
            nodes = v08['nodes']
            print(f"  V3.0 概念: {len(nodes)} 节点 (fallback V0.8, V3.0 文件不完整)")
    else:
        nodes = v08['nodes']
        print(f"  V3.0 概念: {len(nodes)} 节点 (V3.0 文件不存在, 用 V0.8)")

    node_ids = {n['id'] for n in nodes}
    print(f"  节点 ID 唯一数: {len(node_ids)}")

    # 2. 给 V0.8 现有边补字段
    print(f"\n  === Step 1: 补 V0.8 现有边字段 ===")
    enriched = []
    for i, e in enumerate(v08['edges'], 1):
        enriched.append(enrich_existing_edge(e, i))
    print(f"    {len(enriched)} 条 V0.8 边已补字段")

    # 记录已用 (from, to, rel) 防重复
    seen = {(e['from'], e['to'], e['rel']) for e in enriched}

    # 3. A) 同学科同领域 prerequisite
    print(f"\n  === Step 2A: 同学科同领域 prerequisite ===")
    a_edges, seen = gen_intra_subject_prerequisite(nodes, seen)
    print(f"    + {len(a_edges)} 条")
    enriched.extend(a_edges)

    # 4. B) 跨学段 progresses_to
    print(f"\n  === Step 2B: 跨学段 progresses_to ===")
    b_edges, seen = gen_cross_stage_progresses(nodes, seen)
    print(f"    + {len(b_edges)} 条")
    enriched.extend(b_edges)

    # 5. C) 跨学科 relates_to
    print(f"\n  === Step 2C: 跨学科 relates_to ===")
    c_edges, seen = gen_cross_subject_relates(nodes, seen, max_total=args.max_relates)
    print(f"    + {len(c_edges)} 条")
    enriched.extend(c_edges)

    # 6. 去重 + 重排 ID
    print(f"\n  === Step 3: 去重 + 验证 ===")
    before_dedup = len(enriched)
    enriched = deduplicate(enriched)
    print(f"    去重: {before_dedup} → {len(enriched)}")

    # 过滤悬空
    before_dangle = len(enriched)
    enriched = [e for e in enriched if e['from'] in node_ids and e['to'] in node_ids]
    dropped = before_dangle - len(enriched)
    print(f"    过滤悬空: 删 {dropped} 条 (剩余 {len(enriched)})")

    # 重排 ID
    enriched = reassign_ids(enriched)
    print(f"    ID 重排完成: e_0001 ~ e_{len(enriched):04d}")

    # 7. 统计
    rel_counts = Counter(e['rel'] for e in enriched)
    print(f"\n  === 总览 ===")
    print(f"    边总数: {len(enriched)}")
    for r in ["prerequisite", "progresses_to", "relates_to"]:
        print(f"    {r}: {rel_counts.get(r, 0)}")

    # 8. 字段完整性
    required = {"id", "from", "to", "rel", "source", "weight", "rationale"}
    bad = [e for e in enriched if not required.issubset(e.keys())]
    print(f"    字段不完整: {len(bad)}")

    # 9. 写文件
    if not args.dry_run:
        out = {
            "nodes": nodes,
            "edges": enriched,
        }
        with open(DST_V30, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\n  📁 写入: {DST_V30}")

        # 10. 报告
        report = {
            "version": "v3.0",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "summary": {
                "total_nodes": len(nodes),
                "total_edges": len(enriched),
                "by_rel": dict(rel_counts),
                "pass_target_500": len(enriched) >= 500,
            },
            "by_source": dict(Counter(e['source'] for e in enriched)),
            "by_weight": dict(Counter(e['weight'] for e in enriched)),
            "field_coverage": {k: sum(1 for e in enriched if k in e) for k in required},
        }
        with open(REPORT, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"  📁 报告: {REPORT}")
    else:
        print(f"\n  [dry-run] 不写文件")


if __name__ == "__main__":
    main()
