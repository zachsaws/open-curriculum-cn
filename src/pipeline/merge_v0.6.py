"""
V0.6 合并 — 把 14 学科抽出的概念合并到 all_v0.6.json
ID 规则: {SUBJECT_PREFIX}_{原ID}
- math:    M_xxx
- chinese: CN_xxx
- english: EN_xxx
- physics: P_xxx
- chemistry: CH_xxx
- biology: B_xxx
- history: H_xxx
- geography: G_xxx
- science: SC_xxx
- morality_law: ML_xxx
- info_tech: IT_xxx
- art: ART_xxx
- pe_health: PE_xxx
- labor: L_xxx
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GRAPH_DIR = ROOT / "data" / "graph"

PREFIX = {
    "math": "M",
    "chinese": "CN",
    "english": "EN",
    "physics": "P",
    "chemistry": "CH",
    "biology": "B",
    "history": "H",
    "geography": "G",
    "science": "SC",
    "morality_law": "ML",
    "info_tech": "IT",
    "art": "ART",
    "pe_health": "PE",
    "labor": "L",
}


def clean_id(subject, raw_id):
    """统一 ID 规范: {SUBJECT_PREFIX}_{内部ID}
    raw_id 可能形态:
      - 'c_C1_AL_01' (chinese, 来自旧 make_concepts 小写 c_ 前缀)
      - 'p_P1_01'   (physics)
      - 'M_G1_NS_01' (math, 已经是大写 M_ 前缀 — 这是 math_v0.6.json 的原始格式)
      - 'C1_01'     (没有前缀)
    目标: 统一输出 'CN_C1_AL_01', 'P_P1_01', 'M_G1_NS_01', 'CH_C1_01'
    """
    s = raw_id
    # 去掉首个下划线前的小写字母前缀
    m = re.match(r"^([a-z])_(.+)$", s)
    if m:
        s = m.group(2)
    # math 特殊: 已经是大写 M_ 前缀,直接用
    if subject == "math" and re.match(r"^M_", s):
        return s
    return f"{PREFIX[subject]}_{s}"


def load_subject(fname, subject):
    """加载单个学科 graph,返回 (nodes, edges) 已 normalize ID"""
    with open(GRAPH_DIR / fname) as f:
        data = json.load(f)
    nodes = []
    for n in data["nodes"]:
        n2 = dict(n)
        n2["id"] = clean_id(subject, n["id"])
        nodes.append(n2)
    edges = []
    for e in data["edges"]:
        e2 = {
            "from": clean_id(subject, e["from"]),
            "to": clean_id(subject, e["to"]),
            "type": e["type"],
        }
        edges.append(e2)
    return nodes, edges


def main():
    all_nodes = []
    all_edges = []

    # 数学 — 已是大写 M_
    n, e = load_subject("math_v0.6.json", "math")
    all_nodes.extend(n)
    all_edges.extend(e)
    print(f"math: {len(n)} nodes, {len(e)} edges")

    # 其他 13 学科 (语文英语物理化学生物历史地理科学道法信息科技艺术体育劳动)
    # subjects_v0.6.json: chinese, english, geography, history, morality_law, science
    # subjects_v0.6_part2.json: physics, chemistry, biology, info_tech, art, pe_health, labor
    # 用 subject 字段自动归类
    for fname, default_subj in [
        ("subjects_v0.6.json", None),
        ("subjects_v0.6_part2.json", None),
    ]:
        with open(GRAPH_DIR / fname) as f:
            data = json.load(f)
        for n in data["nodes"]:
            subj = n["subject"]
            n2 = dict(n)
            n2["id"] = clean_id(subj, n["id"])
            all_nodes.append(n2)

    # 去重 (以防 ID 冲突)
    seen = set()
    unique = []
    for n in all_nodes:
        if n["id"] in seen:
            print(f"DUPLICATE: {n['id']} - skipping")
            continue
        seen.add(n["id"])
        unique.append(n)
    all_nodes = unique

    # 验证数学内部 edges
    ids = {n["id"] for n in all_nodes}
    valid_edges = []
    for e in all_edges:
        if e["from"] not in ids:
            print(f"WARN: missing from {e['from']}")
            continue
        if e["to"] not in ids:
            print(f"WARN: missing to {e['to']}")
            continue
        if e["from"] == e["to"]:
            continue
        valid_edges.append(e)

    # 加一些跨学科软关系 (math↔physics, math↔chemistry, etc.)
    cross = generate_cross_subject_edges(ids)
    valid_edges.extend(cross)
    print(f"跨学科关系: +{len(cross)}")

    print(f"\n=== V0.6 总计 ===")
    print(f"节点: {len(all_nodes)}")
    print(f"关系: {len(valid_edges)}")
    by_subj = {}
    for n in all_nodes:
        by_subj.setdefault(n["subject"], 0)
        by_subj[n["subject"]] += 1
    for s, n in sorted(by_subj.items(), key=lambda x: -x[1]):
        print(f"  {s}: {n}")

    # 输出
    out = {"nodes": all_nodes, "edges": valid_edges}
    out_path = GRAPH_DIR / "all_v0.6.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nwritten: {out_path}")


def generate_cross_subject_edges(ids):
    """跨学科软关系 — 标记 0=soft"""
    soft = [
        # 数学 ↔ 物理
        ("M_G2_GM_07", "P_DUMMY_PLACEHOLDER", 0),  # placeholder, fill below
    ]
    edges = []
    # 数学:速度 → 物理:速度
    if "M_G2_QR_04" in ids and "P_xxx_SPEED" not in ids:
        pass  # skip placeholder
    # 实际映射
    mapping = [
        # 物理会用数学:速度 → 物理里的"速度"概念 (P2_04)
        ("M_G2_QR_04", "P_P2_04", 0),  # 数量关系 速度时间 → 物理 速度
        ("M_G2_GM_07", "P_P2_12", 0),  # 面积 → 压强
        ("M_G2_GM_13", "P_P2_17", 0),  # 长方形面积 → 杠杆力臂计算
        ("M_G3_NS_13", "P_P2_23", 0),  # 正比例 → 物理量
        # 数学 ↔ 化学
        ("M_G3_NS_09", "CH_C3_06", 0),  # 百分数 → 化学式计算
        # 数学 ↔ 生物
        ("M_G2_ST_05", "B_B3_03", 0),  # 平均数 → 能量流动
        # 数学 ↔ 信息科技
        ("M_G3_NS_11", "IT_I2_05", 0),  # 比 → 算法
        # 物理 → 化学
        ("P_P1_09", "CH_C6_02", 0),  # 原子结构
        # 语文 → 历史
        ("CN_C4_BO_01", "H_H1_CA_05", 0),  # 阅读汉代 → 了解汉代
        # 科学 ↔ 生物
        ("SC_S2_MS_04", "B_B1_10", 0),  # 声音传播 → 神经系统信号
        # 地理 ↔ 生物
        ("G_G3_01", "B_B2_01", 0),  # 人口 → 生物分类
        # 信息科技 → 美术
        ("IT_I6_01", "ART_A5_02", 0),  # AI → 短视频创作
    ]
    for fr, to, typ in mapping:
        if fr in ids and to in ids:
            edges.append({"from": fr, "to": to, "type": typ})
    return edges


if __name__ == "__main__":
    main()
