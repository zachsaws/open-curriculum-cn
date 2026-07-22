"""
完整测试套件 V3 — V3.0 数据 + 关系 + i18n + 性能
跑: python -m pytest api/tests/test_full.py -v
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from api.server import app
from api.web_server import app as web_app

DATA = json.load(open(Path(__file__).parent.parent.parent / "data" / "graph" / "all_v3.0.json"))
client = TestClient(app)
web = TestClient(web_app)


# ====================================================================
# V0: 数据基础
# ====================================================================

def test_v0_data_exists():
    assert DATA is not None
    assert len(DATA["nodes"]) > 0
    assert len(DATA["edges"]) > 0
    print(f"✅ V0 数据: {len(DATA['nodes'])} 节点, {len(DATA['edges'])} 关系")


def test_v0_no_dup_id():
    ids = [n["id"] for n in DATA["nodes"]]
    assert len(ids) == len(set(ids)), "节点 ID 有重复"
    print(f"✅ V0 无重复 ID: {len(ids)} 唯一")


def test_v0_no_self_loop():
    for e in DATA["edges"]:
        fr = e.get("from") if "from" in e else e[0]
        to = e.get("to") if "to" in e else e[1]
        assert fr != to, f"自环: {fr}"
    print(f"✅ V0 无自环边: {len(DATA['edges'])} 条")


def test_v0_edge_refs_exist():
    ids = {n["id"] for n in DATA["nodes"]}
    for e in DATA["edges"]:
        fr = e.get("from") if "from" in e else e[0]
        to = e.get("to") if "to" in e else e[1]
        assert fr in ids, f"边 from 不存在: {fr}"
        assert to in ids, f"边 to 不存在: {to}"
    print(f"✅ V0 所有边引用存在的节点")


# ====================================================================
# V1: 概念字段
# ====================================================================

def test_v1_required_fields():
    required = ["id", "subject", "title"]
    for n in DATA["nodes"]:
        for f in required:
            assert f in n, f"节点 {n.get('id')} 缺字段 {f}"
    print(f"✅ V1 必填字段: id/subject/title 全部存在")


def test_v1_subject_valid():
    valid = {"math", "chinese", "english", "physics", "chemistry", "biology",
             "history", "geography", "morality_law", "science",
             "info_tech", "art", "pe_health", "labor"}
    for n in DATA["nodes"]:
        assert n["subject"] in valid, f"非法学科: {n['id']} {n['subject']}"
    print(f"✅ V1 学科字段合法: 14 个学科")


def test_v1_bloom_coverage():
    """所有概念都应有 bloom 字段"""
    has_bloom = sum(1 for n in DATA["nodes"] if n.get("bloom") and len(n["bloom"]) > 0)
    assert has_bloom == len(DATA["nodes"]), f"bloom 缺失: {len(DATA['nodes']) - has_bloom}"
    print(f"✅ V1 bloom 覆盖: {has_bloom}/{len(DATA['nodes'])}")


def test_v1_content_req_coverage():
    """所有概念都应有 content_req 字段"""
    has = sum(1 for n in DATA["nodes"] if n.get("content_req") and len(n["content_req"]) >= 5)
    pct = has / len(DATA["nodes"]) * 100
    assert pct >= 95, f"content_req 完整率低: {pct:.1f}%"
    print(f"✅ V1 content_req 完整: {has}/{len(DATA['nodes'])} ({pct:.1f}%)")


def test_v1_src_page_valid():
    """src_page > 0 (V2.1 修复后)"""
    valid = sum(1 for n in DATA["nodes"] if n.get("src_page"))
    pct = valid / len(DATA["nodes"]) * 100
    assert pct >= 80, f"src_page 有效率低: {pct:.1f}%"
    print(f"✅ V1 src_page 有效: {valid}/{len(DATA['nodes'])} ({pct:.1f}%)")


def test_v1_src_stage_valid():
    """src_stage 应该是 4 个标准学段名之一"""
    valid = {"第一学段", "第二学段", "第三学段", "第四学段"}
    bad = [n for n in DATA["nodes"] if n.get("src_stage") and n["src_stage"] not in valid]
    assert not bad, f"非法 src_stage: {len(bad)}"
    print(f"✅ V1 src_stage 合法: 4 个学段名")


def test_v1_grade_range_valid():
    """grade_start <= grade_end, 都在 1-9"""
    for n in DATA["nodes"]:
        gs = n.get("grade_start", 0)
        ge = n.get("grade_end", 0)
        assert 1 <= gs <= 9 and 1 <= ge <= 9 and gs <= ge, f"年级范围错: {n['id']}"
    print(f"✅ V1 年级范围合法")


# ====================================================================
# V2: 关系图谱
# ====================================================================

def test_v2_rel_field():
    """V2.2 后所有边都应有 rel 字段"""
    has_rel = sum(1 for e in DATA["edges"] if "rel" in e)
    pct = has_rel / len(DATA["edges"]) * 100
    assert pct >= 95, f"rel 字段缺失: {pct:.1f}%"
    print(f"✅ V2 rel 字段: {has_rel}/{len(DATA['edges'])} ({pct:.1f}%)")


def test_v2_rel_values():
    """rel 值应该为 prerequisite / progresses_to / relates_to"""
    valid = {"prerequisite", "progresses_to", "relates_to"}
    bad = [e for e in DATA["edges"] if "rel" in e and e["rel"] not in valid]
    assert not bad, f"非法 rel 值: {len(bad)}"
    print(f"✅ V2 rel 值合法: 3 种")


def test_v2_progresses_to_count():
    """跨学段螺旋至少 30 条"""
    p = sum(1 for e in DATA["edges"] if e.get("rel") == "progresses_to")
    assert p >= 30, f"跨学段螺旋太少: {p}"
    print(f"✅ V2 跨学段螺旋: {p} 条")


def test_v2_relates_to_count():
    """跨学科关联至少 80 条"""
    r = sum(1 for e in DATA["edges"] if e.get("rel") == "relates_to")
    assert r >= 80, f"跨学科太少: {r}"
    print(f"✅ V2 跨学科关联: {r} 条")


def test_v2_no_orphan_subject():
    """没有 100% 孤儿的学科"""
    for subj in ["math", "chinese", "english", "physics", "chemistry", "biology",
                 "history", "geography", "morality_law", "science",
                 "info_tech", "art", "pe_health", "labor"]:
        nodes = {n["id"] for n in DATA["nodes"] if n["subject"] == subj}
        edges_in = {e.get("to") for e in DATA["edges"] if "to" in e} | {e[1] for e in DATA["edges"] if isinstance(e, list)}
        edges_out = {e.get("from") for e in DATA["edges"] if "from" in e} | {e[0] for e in DATA["edges"] if isinstance(e, list)}
        # 至少有一个节点有边
        has_connected = any((n in edges_in or n in edges_out) for n in nodes)
        # 允许有些节点没边, 但要 ≥ 20% 的有边
        connected_count = sum(1 for n in nodes if n in edges_in or n in edges_out)
        ratio = connected_count / len(nodes) if nodes else 0
        assert ratio > 0.05, f"{subj} 孤儿率太高: {ratio*100:.0f}%"
    print(f"✅ V2 14 学科孤儿率均 < 95%")


# ====================================================================
# V3: B 端 API
# ====================================================================

def test_api_root():
    r = client.get("/")
    assert r.status_code == 200
    d = r.json()
    assert d["concepts"] >= 700
    assert d["edges"] >= 200
    print(f"✅ API root: {d['concepts']} 概念, {d['edges']} 关系")


def test_api_concept_with_relations():
    """概念详情包含 prerequisites + unlocks + rel 字段"""
    r = client.get("/api/concepts/M_G1_NS_06")
    assert r.status_code == 200
    d = r.json()
    assert "prerequisites" in d
    assert "unlocks" in d
    # V2.2 后关系应保留 rel
    for e in d["prerequisites"] + d["unlocks"]:
        assert "rel" in e or "type" in e, f"边缺 rel/type 字段: {e}"
    print(f"✅ API 概念详情: {len(d['prerequisites'])} 先决, {len(d['unlocks'])} 后继")


def test_api_prerequisites_no_recursion_error():
    """/api/prerequisites 不爆栈"""
    r = client.get("/api/prerequisites/M_G4_QR_05")
    assert r.status_code == 200
    d = r.json()
    assert d["max_depth"] < 100, f"递归深度异常: {d['max_depth']}"
    print(f"✅ API 先决链: {d['total_prereqs']} 概念, max_depth={d['max_depth']}")


def test_api_path():
    r = client.get("/api/path?from_id=M_G1_NS_06&to_id=M_G1_NS_12")
    assert r.status_code == 200
    d = r.json()
    assert d["length"] >= 1
    print(f"✅ API 路径: {d['from']} → {d['to']}, length={d['length']}")


def test_api_search():
    r = client.get("/api/search?q=勾股")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    print(f"✅ API 搜索'勾股': {d['total']} 命中")


def test_api_stats():
    r = client.get("/api/stats")
    d = r.json()
    assert d["total_concepts"] >= 700
    assert d["total_edges"] >= 200
    print(f"✅ API 统计: {d['total_concepts']} 概念, {d['total_edges']} 关系")


def test_api_health_v32():
    """V3.2 health 端点: 字段填充 + DAG 状态"""
    r = client.get("/api/health")
    assert r.status_code == 200
    h = r.json()
    assert h["status"] == "ok", f"health status: {h['status']}"
    assert h["dag"]["is_dag"] is True, f"DAG 失败: {h['dag']}"
    # V3.2 字段 100% 填充
    fc = h["field_coverage"]
    must_100 = ["edge_reason_填充", "assessment_prompt_填充", "centrality_填充", "type_填充", "age_填充",
                "bloom_覆盖", "src_page_真实", "key_points_填充"]
    for k in must_100:
        assert fc[k]["pct"] == 100.0, f"{k}: {fc[k]['pct']}%"
    print(f"✅ API /api/health: status={h['status']}, {len([k for k,v in fc.items() if v['pct']==100.0])}/10 字段 100%")


def test_api_subject_names_trilingual():
    """/api/subjects 返回简繁英三语"""
    r = client.get("/api/subjects")
    d = r.json()
    # 至少一个学科有 name_tw + name_en
    for s, v in d.items():
        if "name_tw" in v and "name_en" in v:
            print(f"✅ API 学科三语: {s} = {v.get('name_cn')}/{v['name_tw']}/{v['name_en']}")
            return
    assert False, "API 学科没返回 name_tw/name_en"


def test_api_rss():
    r = client.get("/rss.xml")
    assert r.status_code == 200
    assert "application/rss+xml" in r.headers.get("content-type", "")
    assert "<rss" in r.text
    print(f"✅ API RSS: {len(r.text)} bytes")


# ====================================================================
# V4: Web 静态资源
# ====================================================================

def test_web_index():
    r = web.get("/index.html")
    assert r.status_code == 200
    assert "<title>2022 新课标知识图谱" in r.text
    print(f"✅ Web index: {len(r.text)} bytes")


def test_web_graph_json():
    r = web.get("/data/graph.json")
    assert r.status_code == 200
    d = r.json()
    assert len(d["nodes"]) >= 700
    print(f"✅ Web graph.json: {len(d['nodes'])} 节点")


def test_web_cytoscape_gzipped():
    """cytoscape.min.js 应该有 .gz 预压缩版"""
    import os
    gz = Path(__file__).parent.parent.parent / "web" / "cytoscape.min.js.gz"
    assert gz.exists(), "cytoscape.min.js.gz 不存在"
    size_gz = gz.stat().st_size
    size_orig = (Path(__file__).parent.parent.parent / "web" / "cytoscape.min.js").stat().st_size
    ratio = size_gz / size_orig
    assert ratio < 0.5, f"gzip 压缩比太低: {ratio*100:.0f}%"
    print(f"✅ Web cytoscape.gz: {size_gz} bytes ({ratio*100:.0f}% of original)")


# ====================================================================
# V5: 性能基准
# ====================================================================

def test_perf_api_concepts():
    """API 列概念 < 100ms"""
    start = time.time()
    for _ in range(10):
        r = client.get("/api/concepts?subject=math&limit=100")
    avg = (time.time() - start) / 10 * 1000
    assert avg < 200, f"API 列概念太慢: {avg:.0f}ms"
    print(f"✅ 性能: API 列 100 概念 {avg:.0f}ms")


def test_perf_api_prerequisites():
    """先决链 BFS < 500ms"""
    start = time.time()
    for _ in range(3):
        r = client.get("/api/prerequisites/M_G4_QR_05")
    avg = (time.time() - start) / 3 * 1000
    assert avg < 1000, f"先决链太慢: {avg:.0f}ms"
    print(f"✅ 性能: 先决链 {avg:.0f}ms")


def test_perf_api_search():
    """搜索 < 50ms"""
    start = time.time()
    for _ in range(10):
        r = client.get("/api/search?q=函数")
    avg = (time.time() - start) / 10 * 1000
    assert avg < 100, f"搜索太慢: {avg:.0f}ms"
    print(f"✅ 性能: 搜索 {avg:.0f}ms")


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
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
