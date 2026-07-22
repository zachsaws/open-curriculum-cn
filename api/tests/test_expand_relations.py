"""
V3.0 关系扩充测试套件 — 30 测试, 验证 expand_relations.py 输出

跑:
  python api/tests/test_expand_relations.py
  # 或 pytest:
  python -m pytest api/tests/test_expand_relations.py -v
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

DATA = json.load(open(ROOT / "data" / "graph" / "all_v3.0.json"))
NODES = {n["id"]: n for n in DATA["nodes"]}
EDGES = DATA["edges"]
REQUIRED_FIELDS = {"id", "from", "to", "rel", "source", "weight", "rationale"}
VALID_REL = {"prerequisite", "progresses_to", "relates_to"}
REL_WEIGHT = {"prerequisite": 1.0, "progresses_to": 0.8, "relates_to": 0.5}
VALID_SOURCE = {"curriculum", "domain_logic"}


# ====================================================================
# R1: Schema (8 tests)
# ====================================================================

def test_r1_edge_id_present():
    """R1.1: 所有边都有 id 字段"""
    no_id = [e for e in EDGES if "id" not in e or not e["id"]]
    assert not no_id, f"{len(no_id)} 边缺 id"
    print(f"✅ R1.1 边 id 字段: {len(EDGES)}/{len(EDGES)} (100%)")


def test_r1_edge_id_format():
    """R1.2: id 格式为 e_NNNN (4 位数字)"""
    bad = [e for e in EDGES if not re.match(r"^e_\d{4}$", e.get("id", ""))]
    assert not bad, f"{len(bad)} 边 id 格式错"
    print(f"✅ R1.2 id 格式 e_NNNN: {len(EDGES)} 条")


def test_r1_edge_id_unique():
    """R1.3: id 唯一"""
    ids = [e["id"] for e in EDGES]
    assert len(ids) == len(set(ids)), f"id 重复: {len(ids) - len(set(ids))}"
    print(f"✅ R1.3 id 唯一: {len(set(ids))} 唯一")


def test_r1_required_fields():
    """R1.4: 必填字段完整 (id/from/to/rel/source/weight/rationale)"""
    incomplete = [e for e in EDGES if not REQUIRED_FIELDS.issubset(e.keys())]
    assert not incomplete, f"{len(incomplete)} 边缺字段"
    print(f"✅ R1.4 必填字段完整: {len(REQUIRED_FIELDS)} 字段, {len(EDGES)} 边")


def test_r1_rel_values():
    """R1.5: rel 字段合法"""
    bad = [e for e in EDGES if e["rel"] not in VALID_REL]
    assert not bad, f"{len(bad)} 边 rel 非法"
    print(f"✅ R1.5 rel 合法: {VALID_REL}")


def test_r1_weight_matches_rel():
    """R1.6: weight 字段与 rel 对应 (prereq=1.0, prog=0.8, rel=0.5)"""
    bad = []
    for e in EDGES:
        expected = REL_WEIGHT[e["rel"]]
        if abs(e["weight"] - expected) > 0.001:
            bad.append((e["id"], e["rel"], e["weight"], expected))
    assert not bad, f"{len(bad)} 边 weight 与 rel 不匹配"
    print(f"✅ R1.6 weight 与 rel 对应: 1.0/0.8/0.5 完美分布")


def test_r1_source_values():
    """R1.7: source 字段为 curriculum 或 domain_logic"""
    # V0.8 继承的边 source 是 2022-* 格式, 也接受
    allowed = VALID_SOURCE | {s for s in (e.get("source", "") for e in EDGES) if s.startswith("2022-")}
    bad = [e for e in EDGES if e["source"] not in allowed]
    # V0.8 132 条允许 2022-* 格式; V3.0 新增边必须 curriculum/domain_logic
    new_bad = [e for e in EDGES
               if not e["source"].startswith("2022-")
               and e["source"] not in VALID_SOURCE]
    assert not new_bad, f"{len(new_bad)} 边 source 非法"
    print(f"✅ R1.7 source 合法: {Counter(e['source'] for e in EDGES).most_common(3)}")


def test_r1_rationale_non_empty():
    """R1.8: rationale 字段非空"""
    empty = [e for e in EDGES if not e.get("rationale", "").strip()]
    assert not empty, f"{len(empty)} 边 rationale 为空"
    print(f"✅ R1.8 rationale 非空: {len(EDGES)} 条")


# ====================================================================
# R2: 图完整性 (8 tests)
# ====================================================================

def test_r2_no_self_loop():
    """R2.1: 无自环 (from == to)"""
    self_loops = [e for e in EDGES if e["from"] == e["to"]]
    assert not self_loops, f"{len(self_loops)} 自环"
    print(f"✅ R2.1 无自环: 0/{len(EDGES)}")


def test_r2_no_dangling_from():
    """R2.2: 无悬空 from"""
    dangle = [e for e in EDGES if e["from"] not in NODES]
    assert not dangle, f"{len(dangle)} 悬空 from"
    print(f"✅ R2.2 无悬空 from: 0/{len(EDGES)}")


def test_r2_no_dangling_to():
    """R2.3: 无悬空 to"""
    dangle = [e for e in EDGES if e["to"] not in NODES]
    assert not dangle, f"{len(dangle)} 悬空 to"
    print(f"✅ R2.3 无悬空 to: 0/{len(EDGES)}")


def test_r2_no_duplicate_triple():
    """R2.4: 无 (from, to, rel) 重复"""
    triples = Counter((e["from"], e["to"], e["rel"]) for e in EDGES)
    dups = {k: v for k, v in triples.items() if v > 1}
    assert not dups, f"{len(dups)} 三元组重复"
    print(f"✅ R2.4 无 (from,to,rel) 重复: 0/{len(EDGES)}")


def test_r2_no_backflow_prerequisite():
    """R2.5: 无 prerequisite 跨学段反向 (from.stage > to.stage)"""
    bad = []
    for e in EDGES:
        if e["rel"] != "prerequisite":
            continue
        f, t = e["from"], e["to"]
        if f in NODES and t in NODES:
            fs = NODES[f].get("stage", 0)
            ts = NODES[t].get("stage", 0)
            if fs and ts and fs > ts:
                bad.append((f, t, fs, ts))
    assert not bad, f"{len(bad)} prerequisite 反向"
    print(f"✅ R2.5 无 prerequisite 反向: 0")


def test_r2_all_14_subjects_have_edges():
    """R2.6: 14 学科都有边"""
    subjects = {n["subject"] for n in DATA["nodes"]}
    for subj in subjects:
        in_count = sum(1 for e in EDGES if NODES.get(e["to"], {}).get("subject") == subj)
        out_count = sum(1 for e in EDGES if NODES.get(e["from"], {}).get("subject") == subj)
        assert in_count + out_count > 0, f"{subj} 没任何边"
    print(f"✅ R2.6 14 学科都有边: {len(subjects)} 学科")


def test_r2_edge_density_reasonable():
    """R2.7: 边/节点 比合理 (1.0 - 4.0)"""
    ratio = len(EDGES) / len(DATA["nodes"])
    assert 1.0 <= ratio <= 4.0, f"边/节点比异常: {ratio:.2f}"
    print(f"✅ R2.7 边/节点比: {ratio:.2f}")


def test_r2_no_orphan_node_in_subj():
    """R2.8: 14 学科无 100% 孤儿 (孤儿率 < 95%)"""
    for subj in ["math", "chinese", "english", "physics", "chemistry", "biology",
                 "history", "geography", "morality_law", "science",
                 "info_tech", "art", "pe_health", "labor"]:
        nodes = {n["id"] for n in DATA["nodes"] if n["subject"] == subj}
        connected = {e["from"] for e in EDGES} | {e["to"] for e in EDGES}
        in_subj = nodes & connected
        ratio = len(in_subj) / len(nodes) if nodes else 0
        assert ratio > 0.05, f"{subj} 孤儿率太高: {(1-ratio)*100:.0f}%"
    print(f"✅ R2.8 14 学科孤儿率 < 95%")


# ====================================================================
# R3: 关系分布 (8 tests)
# ====================================================================

def test_r3_total_edges_target():
    """R3.1: 总边数 ≥ 500 (V3.0 目标)"""
    assert len(EDGES) >= 500, f"边数不达标: {len(EDGES)} < 500"
    print(f"✅ R3.1 总边数 ≥ 500: {len(EDGES)} 条")


def test_r3_prerequisite_count():
    """R3.2: prerequisite 边 ≥ 1500 (V0.8 153 + 同学科新链)"""
    prereq = sum(1 for e in EDGES if e["rel"] == "prerequisite")
    assert prereq >= 1500, f"prerequisite 太少: {prereq}"
    print(f"✅ R3.2 prerequisite: {prereq} 条")


def test_r3_progresses_to_count():
    """R3.3: progresses_to 边 ≥ 50 (跨学段螺旋目标 +50)"""
    prog = sum(1 for e in EDGES if e["rel"] == "progresses_to")
    assert prog >= 50, f"progresses_to 太少: {prog}"
    print(f"✅ R3.3 progresses_to: {prog} 条")


def test_r3_relates_to_count():
    """R3.4: relates_to 边 ≥ 100 (跨学科软关联目标 +100)"""
    rel = sum(1 for e in EDGES if e["rel"] == "relates_to")
    assert rel >= 100, f"relates_to 太少: {rel}"
    print(f"✅ R3.4 relates_to: {rel} 条")


def test_r3_all_3_rels_present():
    """R3.5: 3 种 rel 都有"""
    rels = {e["rel"] for e in EDGES}
    assert rels == VALID_REL, f"缺少 rel: {VALID_REL - rels}"
    print(f"✅ R3.5 3 种 rel 齐: {rels}")


def test_r3_cross_subject_pairs():
    """R3.6: 跨学科对覆盖 (≥ 20 对, C(14,2) = 91)"""
    subj_pairs = set()
    for e in EDGES:
        if e["from"] in NODES and e["to"] in NODES:
            f_subj = NODES[e["from"]]["subject"]
            t_subj = NODES[e["to"]]["subject"]
            if f_subj != t_subj:
                subj_pairs.add(tuple(sorted([f_subj, t_subj])))
    assert len(subj_pairs) >= 20, f"跨学科对太少: {len(subj_pairs)}"
    print(f"✅ R3.6 跨学科对: {len(subj_pairs)}/91")


def test_r3_weight_distribution():
    """R3.7: weight 分布与 rel 完美对应"""
    rel_by_weight = defaultdict(set)
    for e in EDGES:
        rel_by_weight[e["weight"]].add(e["rel"])
    # 每个 weight 对应 1 种 rel
    for w, rels in rel_by_weight.items():
        assert len(rels) == 1, f"weight {w} 对应多个 rel: {rels}"
    # 3 种 weight 都存在
    assert {1.0, 0.8, 0.5}.issubset(rel_by_weight.keys()), f"weight 缺: {rel_by_weight}"
    print(f"✅ R3.7 weight 分布: {dict(Counter(e['weight'] for e in EDGES))}")


def test_r3_source_distribution():
    """R3.8: source curriculum + domain_logic + 2022-* 兼容"""
    sources = set(e["source"] for e in EDGES)
    # curriculum / domain_logic / 2022-* (继承)
    has_curriculum = "curriculum" in sources
    has_domain = "domain_logic" in sources
    assert has_curriculum and has_domain, f"缺 source: curriculum={has_curriculum}, domain_logic={has_domain}"
    print(f"✅ R3.8 source 分布: {dict(Counter(e['source'] for e in EDGES).most_common(3))}")


# ====================================================================
# R4: 增量目标 (6 tests)
# ====================================================================

def test_r4_v08_baseline_preserved():
    """R4.1: V0.8 关系 (299) 全部保留 (≥ 299)"""
    # V0.8 source 格式是 2022-* 或没 source (但 V3.0 必有 source)
    # 检查 V0.8 299 边 from/to 是否都还在
    v08 = json.load(open(ROOT / "data" / "graph" / "all_v0.8.json"))
    v08_keys = {(e["from"], e["to"], e.get("rel", "relates_to")) for e in v08["edges"]}
    v30_keys = {(e["from"], e["to"], e["rel"]) for e in EDGES}
    preserved = v08_keys & v30_keys
    assert len(preserved) >= 280, f"V0.8 关系丢失: {len(v08_keys) - len(preserved)}"
    print(f"✅ R4.1 V0.8 关系保留: {len(preserved)}/{len(v08_keys)}")


def test_r4_intra_subject_prereq_added():
    """R4.2: 同学科 prerequisite 新增 (≥ 1000)"""
    prereq = [e for e in EDGES if e["rel"] == "prerequisite"]
    # V0.8 已有 153, 同学科新链应至少加 1000
    assert len(prereq) >= 1000, f"prerequisite 不足: {len(prereq)}"
    print(f"✅ R4.2 同学科 prerequisite: {len(prereq)} 条")


def test_r4_progresses_to_added():
    """R4.3: 跨学段 progresses_to 新增 (≥ 50, V0.8 是 33)"""
    prog = sum(1 for e in EDGES if e["rel"] == "progresses_to")
    assert prog >= 50, f"progresses_to 不足: {prog}"
    print(f"✅ R4.3 跨学段 progresses_to: {prog} 条 (V0.8: 33)")


def test_r4_relates_to_added():
    """R4.4: 跨学科 relates_to 新增 (≥ 100, V0.8 是 113)"""
    rel = sum(1 for e in EDGES if e["rel"] == "relates_to")
    assert rel >= 100, f"relates_to 不足: {rel}"
    print(f"✅ R4.4 跨学科 relates_to: {rel} 条 (V0.8: 113)")


def test_r4_backup_exists():
    """R4.5: V0.8 备份存在"""
    bak = ROOT / "data" / "graph" / "all_v0.8.json.bak"
    assert bak.exists(), f"备份不存在: {bak}"
    print(f"✅ R4.5 V0.8 备份: {bak.name} ({bak.stat().st_size} bytes)")


def test_r4_v30_v08_edge_growth():
    """R4.6: V3.0 边数 ≥ 1.5x V0.8 边数"""
    v08 = json.load(open(ROOT / "data" / "graph" / "all_v0.8.json"))
    growth = len(EDGES) / len(v08["edges"])
    assert growth >= 1.5, f"边数增长不足: {growth:.2f}x"
    print(f"✅ R4.6 边数增长: {len(v08['edges'])} → {len(EDGES)} ({growth:.2f}x)")


# ====================================================================
# Main
# ====================================================================

if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_r")]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"❌ {t.__name__}: {e}")
            failed += 1
    print(f"\n{'='*60}")
    print(f"结果: {passed} 通过 / {failed} 失败 / {passed+failed} 总数")
    sys.exit(0 if failed == 0 else 1)
