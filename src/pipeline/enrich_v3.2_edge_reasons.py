"""
V3.2 P0: 给 4736 条边自动生成 reason (人话)
- prerequisite (1759): 必填 reason
- progresses_to (364): 必填 reason
- relates_to (2613): 必填 reason

策略: 4 维模板 (rel_type, same_subject, same_domain, same_stage)
+ 跨学科 bridge 字典 (~20 对)
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
IN = ROOT / "data" / "graph" / "all_v3.0.json"
OUT = ROOT / "data" / "graph" / "all_v3.2.json"

# 跨学科 bridge 字典 — 表达"X 学科的概念怎样帮到 Y 学科"
BRIDGE = {
    ("math", "physics"): "数学工具 (公式/计算)",
    ("math", "chemistry"): "数学计算 (摩尔/平衡)",
    ("math", "biology"): "统计与概率",
    ("math", "info_tech"): "数学逻辑与算法",
    ("math", "geography"): "数据计算与图表",
    ("math", "science"): "科学测量与计算",
    ("math", "art"): "几何与对称",
    ("math", "labor"): "测量与估算",
    ("math", "pe_health"): "数据记录",
    ("physics", "chemistry"): "实验方法",
    ("physics", "biology"): "物理原理",
    ("physics", "info_tech"): "电子电路",
    ("physics", "geography"): "地球物理",
    ("physics", "science"): "科学探究",
    ("physics", "labor"): "技术应用",
    ("chemistry", "biology"): "生物化学基础",
    ("chemistry", "science"): "物质科学",
    ("chemistry", "labor"): "化学实验",
    ("chemistry", "geography"): "岩石与矿物",
    ("chemistry", "info_tech"): "材料科学",
    ("chemistry", "art"): "颜料化学",
    ("chemistry", "pe_health"): "营养与代谢",
    ("biology", "geography"): "自然地理与生态",
    ("biology", "science"): "生命科学",
    ("biology", "pe_health"): "健康与卫生",
    ("biology", "labor"): "生物实践",
    ("biology", "info_tech"): "生物信息学",
    ("biology", "art"): "自然形态",
    ("biology", "chinese"): "生物科普阅读",
    ("chinese", "history"): "史料阅读与古文",
    ("chinese", "geography"): "地名与文化",
    ("chinese", "morality_law"): "价值观与表达",
    ("chinese", "art"): "文学与艺术鉴赏",
    ("chinese", "labor"): "文字记录与表达",
    ("english", "chinese"): "中英对照与互译",
    ("english", "info_tech"): "英文技术文档",
    ("english", "science"): "科学术语英文",
    ("history", "geography"): "历史地理背景",
    ("history", "morality_law"): "历史与价值观",
    ("history", "art"): "艺术史",
    ("history", "chinese"): "古文与史料",
    ("history", "labor"): "传统工艺史",
    ("history", "pe_health"): "体育史",
    ("geography", "history"): "地缘历史",
    ("geography", "biology"): "自然地理",
    ("geography", "morality_law"): "国情与制度",
    ("geography", "info_tech"): "GIS 与地图",
    ("geography", "labor"): "乡土实践",
    ("morality_law", "history"): "法治史",
    ("morality_law", "chinese"): "案例阅读",
    ("morality_law", "labor"): "社会服务",
    ("info_tech", "math"): "算法与逻辑",
    ("info_tech", "science"): "数据采集",
    ("info_tech", "art"): "数字艺术",
    ("info_tech", "labor"): "数字工具",
    ("info_tech", "pe_health"): "健康数据",
    ("art", "chinese"): "文学意境",
    ("art", "history"): "艺术史",
    ("art", "geography"): "地域文化",
    ("art", "morality_law"): "美育与价值观",
    ("art", "labor"): "工艺实践",
    ("pe_health", "biology"): "生理基础",
    ("pe_health", "science"): "运动科学",
    ("pe_health", "morality_law"): "健康与安全",
    ("labor", "pe_health"): "生活技能",
    ("labor", "info_tech"): "工具使用",
    ("labor", "art"): "手工艺",
    ("science", "physics"): "物理原理",
    ("science", "chemistry"): "化学原理",
    ("science", "biology"): "生命原理",
    ("science", "geography"): "地球科学",
    ("science", "info_tech"): "数据采集",
    ("science", "art"): "科学绘图",
    ("science", "chinese"): "科学说明文",
}

def bridge(from_s, to_s):
    """取跨学科 bridge 描述"""
    if from_s == to_s:
        return None
    return BRIDGE.get((from_s, to_s)) or BRIDGE.get((to_s, from_s)) or "学科间联系"

def stage_key(g):
    if g <= 2: return "G1-2"
    if g <= 4: return "G3-4"
    if g <= 6: return "G5-6"
    return "G7-9"

def stage_name_zh(g):
    if g <= 2: return "低年级"
    if g <= 4: return "中年级"
    if g <= 6: return "高年级"
    return "初中"

def gen_prerequisite_reason(from_n, to_n):
    """prerequisite 边的 reason"""
    same_subj = from_n["subject"] == to_n["subject"]
    same_domain = from_n.get("domain") == to_n.get("domain")
    same_stage = stage_key(from_n.get("grade_start", 1)) == stage_key(to_n.get("grade_start", 1))
    fs = from_n["subject"]
    ts = to_n["subject"]
    ft = from_n["title"]
    tt = to_n["title"]
    fd = from_n.get("domain", "")
    td = to_n.get("domain", "")
    if same_subj and same_domain and same_stage:
        return f"学{stage_name_zh(from_n.get('grade_start', 1))}的「{ft}」是同段「{tt}」的直接基础"
    if same_subj and same_domain and not same_stage:
        return f"「{ft}」是「{tt}」在更高年级的螺旋上升 ({stage_key(from_n.get('grade_start', 1))} → {stage_key(to_n.get('grade_start', 1))})"
    if same_subj and not same_domain:
        return f"同属 {SUBJ_ZH.get(fs, fs)}，「{ft}」({fd}) 是理解「{tt}」({td}) 的工具"
    # 跨学科
    b = bridge(fs, ts)
    return f"{SUBJ_ZH.get(fs, fs)}的「{ft}」为{SUBJ_ZH.get(ts, ts)}的「{tt}」提供{b}"

def gen_progresses_reason(from_n, to_n):
    """progresses_to 边的 reason"""
    same_subj = from_n["subject"] == to_n["subject"]
    if same_subj:
        fs = from_n["subject"]
        fd = from_n.get("domain", "")
        td = to_n.get("domain", "")
        if fd == td:
            return f"学完「{from_n['title']}」自然进入「{to_n['title']}」的下一阶段"
        return f"学完「{from_n['title']}」({fd}) 后可以拓展到「{to_n['title']}」({td})"
    b = bridge(from_n["subject"], to_n["subject"])
    return f"学完{SUBJ_ZH.get(from_n['subject'], from_n['subject'])}的「{from_n['title']}」后，可以延伸到{SUBJ_ZH.get(to_n['subject'], to_n['subject'])}的「{to_n['title']}」（{b}）"

def gen_relates_reason(from_n, to_n):
    """relates_to 边的 reason"""
    same_subj = from_n["subject"] == to_n["subject"]
    if same_subj:
        if from_n.get("domain") == to_n.get("domain"):
            return f"同属{SUBJ_ZH.get(from_n['subject'], from_n['subject'])}的「{from_n.get('domain', '')}」领域，「{from_n['title']}」与「{to_n['title']}」在教学中常一起出现"
        return f"同属{SUBJ_ZH.get(from_n['subject'], from_n['subject'])}，「{from_n['title']}」({from_n.get('domain', '')}) 与「{to_n['title']}」({to_n.get('domain', '')}) 互相印证"
    b = bridge(from_n["subject"], to_n["subject"])
    return f"{SUBJ_ZH.get(from_n['subject'], from_n['subject'])}的「{from_n['title']}」与{SUBJ_ZH.get(to_n['subject'], to_n['subject'])}的「{to_n['title']}」有 {b} 的联系"

SUBJ_ZH = {
    "math": "数学", "chinese": "语文", "english": "英语",
    "physics": "物理", "chemistry": "化学", "biology": "生物",
    "history": "历史", "geography": "地理", "morality_law": "道德与法治",
    "science": "科学", "info_tech": "信息科技", "art": "艺术",
    "pe_health": "体育与健康", "labor": "劳动",
}

def main():
    print(f"读 {IN}")
    with open(IN) as f:
        d = json.load(f)
    nodes = d["nodes"]
    edges = d["edges"]
    id2node = {n["id"]: n for n in nodes}

    filled = 0
    skipped = 0
    for e in edges:
        from_n = id2node.get(e["from"])
        to_n = id2node.get(e["to"])
        if not from_n or not to_n:
            skipped += 1
            continue
        if e.get("reason"):
            continue  # 已填
        rel = e.get("rel", "prerequisite")
        if rel == "prerequisite":
            r = gen_prerequisite_reason(from_n, to_n)
        elif rel == "progresses_to":
            r = gen_progresses_reason(from_n, to_n)
        elif rel == "relates_to":
            r = gen_relates_reason(from_n, to_n)
        else:
            r = f"「{from_n['title']}」与「{to_n['title']}」相关"
        e["reason"] = r
        filled += 1

    print(f"填充 reason: {filled} 条")
    print(f"跳过 (id 不存在): {skipped} 条")
    # 统计
    with_r = sum(1 for e in edges if e.get("reason"))
    print(f"reason 总覆盖: {with_r}/{len(edges)} = {with_r*100/len(edges):.1f}%")

    # 写入 v3.2
    d["_meta"] = {
        "version": "v3.2",
        "edges_total": len(edges),
        "edges_with_reason": with_r,
        "reason_coverage": round(with_r * 100 / len(edges), 2),
        "enrichments": ["edge_reason"],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=None, separators=(',', ':'))
    print(f"写入 {OUT}")

if __name__ == "__main__":
    main()
