"""
B 端 API 测试
跑: cd open-curriculum-cn && source .venv/bin/activate && python -m pytest api/tests/test_api.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "subjects" in data
    assert "concepts" in data
    assert data["concepts"] >= 700
    print(f"✅ root: {data['concepts']} concepts, {data['subjects']} subjects")


def test_stats():
    r = client.get("/api/stats")
    assert r.status_code == 200
    data = r.json()
    assert "by_subject" in data
    assert "math" in data["by_subject"]
    assert data["by_subject"]["math"] >= 200
    print(f"✅ stats: math={data['by_subject']['math']}")


def test_subjects():
    r = client.get("/api/subjects")
    assert r.status_code == 200
    data = r.json()
    assert "math" in data
    assert data["math"]["name_cn"] == "数学"
    print(f"✅ subjects: {len(data)} 学科")


def test_list_concepts():
    r = client.get("/api/concepts?subject=math&limit=5")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 200
    assert len(data["concepts"]) == 5
    print(f"✅ list_concepts: total={data['total']}, returned 5")


def test_list_concepts_by_stage():
    r = client.get("/api/concepts?subject=math&stage=4&limit=10")  # V3.2: stage 1-4 (G7-9 = 4)
    assert r.status_code == 200
    data = r.json()
    # 第四学段 (G7-9) 数学应该有 ~75 个概念
    assert data["total"] >= 50
    for c in data["concepts"]:
        assert c["stage"] == 4
    print(f"✅ list_concepts stage=4 (G7-9): {data['total']} concepts")


def test_get_concept():
    r = client.get("/api/concepts/M_G4_QR_05")  # 一元二次方程
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "一元二次方程"
    assert "content_req" in data
    assert "prerequisites" in data
    assert "unlocks" in data
    print(f"✅ get_concept: {data['title']}, {data['prereq_count']} 先决, {data['unlock_count']} 后继")


def test_get_concept_404():
    r = client.get("/api/concepts/NONEXISTENT")
    assert r.status_code == 404
    print("✅ get_concept 404")


def test_prerequisites():
    r = client.get("/api/prerequisites/M_G4_QR_05")
    assert r.status_code == 200
    data = r.json()
    assert data["total_prereqs"] > 0
    assert data["max_depth"] > 0
    print(f"✅ prerequisites: {data['total_prereqs']} 概念, max_depth={data['max_depth']}")


def test_find_path():
    # 找一个数学内有路径的 pair
    r = client.get("/api/path?from_id=M_G1_NS_06&to_id=M_G1_NS_12")  # 四则运算意义 → 减法是加法的逆运算
    assert r.status_code == 200
    data = r.json()
    print(f"✅ path: {data['from']} → {data['to']}, length={data['length']}, path={data['path']}")


def test_find_path_no_route():
    # 反向
    r = client.get("/api/path?from_id=M_G4_QR_05&to_id=M_G1_NS_01")
    assert r.status_code == 404
    print("✅ path 404 (no reverse route)")


def test_search():
    r = client.get("/api/search?q=勾股")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    print(f"✅ search '勾股': {data['total']} 命中")


def test_search_subject():
    r = client.get("/api/search?q=方程&subject=math")
    assert r.status_code == 200
    data = r.json()
    assert all(c["subject"] == "math" for c in data["concepts"])
    print(f"✅ search '方程' in math: {data['total']} 命中")


if __name__ == "__main__":
    test_root()
    test_stats()
    test_subjects()
    test_list_concepts()
    test_list_concepts_by_stage()
    test_get_concept()
    test_get_concept_404()
    test_prerequisites()
    test_find_path()
    test_find_path_no_route()
    test_search()
    test_search_subject()
    print("\n🎉 12/12 测试通过")
