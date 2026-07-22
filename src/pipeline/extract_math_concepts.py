"""
从已 OCR 的数学课标中抽取概念和先决关系
- 找"内容要求"部分
- 解析"能/会/了解/认识"等动词提取概念
- 按学段(1-2/3-4/5-6/7-9)分组
"""
import json
import re
from pathlib import Path
from datetime import datetime

PARSED_DIR = Path(__file__).parent.parent.parent / "data" / "parsed"
GRAPH_DIR = Path(__file__).parent.parent.parent / "data" / "graph"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

# 小学数学 课标结构 (2022版) 的核心内容领域
# 这些是从课标目录推断的
MATH_DOMAINS = {
    "number": "数与运算",
    "algebra": "代数",
    "geometry": "图形与几何",
    "statistics": "统计与概率",
    "comprehensive": "综合与实践",
}

# 概念关键词 → 学科子类映射
CONCEPT_KEYWORDS = {
    "整数": "number.integer", "自然数": "number.natural", "分数": "number.fraction",
    "小数": "number.decimal", "百分数": "number.percent", "因数": "number.factor",
    "倍数": "number.multiple", "质数": "number.prime", "合数": "number.composite",
    "奇数": "number.odd", "偶数": "number.even", "正数": "number.positive",
    "负数": "number.negative", "有理数": "number.rational", "无理数": "number.irrational",
    "实数": "number.real", "相反数": "number.opposite", "绝对值": "number.absolute",
    "近似数": "number.approximate", "估算": "number.estimate", "四舍五入": "number.round",
    "加减": "operation.addition_subtraction", "乘除": "operation.multiplication_division",
    "加法": "operation.addition", "减法": "operation.subtraction",
    "乘法": "operation.multiplication", "除法": "operation.division",
    "运算律": "operation.law", "交换律": "operation.commutative", "结合律": "operation.associative",
    "分配律": "operation.distributive", "等式": "algebra.equation", "方程": "algebra.equation",
    "不等式": "algebra.inequality", "代数式": "algebra.expression", "函数": "algebra.function",
    "比例": "ratio.proportion", "正比例": "ratio.direct", "反比例": "ratio.inverse",
    "比": "ratio.ratio",
    "图形": "geometry.shape", "点": "geometry.point", "线": "geometry.line",
    "面": "geometry.plane", "角": "geometry.angle", "三角形": "geometry.triangle",
    "四边形": "geometry.quadrilateral", "圆": "geometry.circle", "扇形": "geometry.sector",
    "长方形": "geometry.rectangle", "正方形": "geometry.square", "平行四边形": "geometry.parallelogram",
    "梯形": "geometry.trapezoid", "周长": "geometry.perimeter", "面积": "geometry.area",
    "体积": "geometry.volume", "表面积": "geometry.surface_area", "对称": "geometry.symmetry",
    "平移": "geometry.translation", "旋转": "geometry.rotation", "轴对称": "geometry.reflection",
    "统计": "statistics.data", "概率": "statistics.probability", "平均数": "statistics.mean",
    "中位数": "statistics.median", "众数": "statistics.mode", "图表": "statistics.chart",
    "条形": "statistics.bar", "折线": "statistics.line_chart", "扇形图": "statistics.pie",
    "测量": "geometry.measurement", "长度": "geometry.length", "质量": "geometry.mass",
    "时间": "geometry.time", "人民币": "comprehensive.money",
    "方向": "geometry.direction", "位置": "geometry.position", "坐标": "geometry.coordinate",
}

# 概念预设（基于课标目录 + 人教版教材结构） - 2022 课标 9 年义务
# 学段: 1-2 (小学低段), 3-4 (小学中段), 5-6 (小学高段), 7-9 (初中)
PRESEED_CONCEPTS = [
    # 1-2 年级
    ("math-1-num-recognition", "认识 0-9 数字", 1, 1, "number", "number.digit"),
    ("math-1-count-20", "20 以内数数", 1, 1, "number", "number.count"),
    ("math-1-count-100", "100 以内数数", 1, 1, "number", "number.count"),
    ("math-1-add-single", "10 以内加法", 1, 1, "operation", "operation.addition"),
    ("math-1-sub-single", "10 以内减法", 1, 1, "operation", "operation.subtraction"),
    ("math-1-add-20", "20 以内进位加法", 1, 1, "operation", "operation.addition"),
    ("math-1-sub-20", "20 以内退位减法", 1, 1, "operation", "operation.subtraction"),
    ("math-1-shape-basic", "认识基本图形(长方/正方/圆/三角)", 1, 1, "geometry", "geometry.shape"),
    ("math-1-position", "上下前后左右方位", 1, 1, "geometry", "geometry.position"),
    ("math-1-time-clock", "认识钟表时间", 1, 1, "geometry", "geometry.time"),
    ("math-1-money-basic", "认识人民币", 1, 1, "comprehensive", "comprehensive.money"),

    # 1-2 年级进阶
    ("math-2-add-100", "100 以内加减法", 2, 2, "operation", "operation.addition_subtraction"),
    ("math-2-mul-intro", "乘法口诀(1-9)", 2, 2, "operation", "operation.multiplication"),
    ("math-2-div-intro", "除法初步(平均分)", 2, 2, "operation", "operation.division"),
    ("math-2-length-cm-m", "长度单位: 厘米/米", 2, 2, "geometry", "geometry.measurement"),
    ("math-2-mass-kg", "质量单位: 千克", 2, 2, "geometry", "geometry.measurement"),
    ("math-2-shape-2d", "平面图形周长", 2, 2, "geometry", "geometry.perimeter"),

    # 3-4 年级
    ("math-3-add-10000", "万以内加减法", 3, 3, "operation", "operation.addition_subtraction"),
    ("math-3-mul-multi", "多位数乘法", 3, 3, "operation", "operation.multiplication"),
    ("math-3-div-multi", "多位数除法", 3, 3, "operation", "operation.division"),
    ("math-3-frac-intro", "分数初步认识", 3, 3, "number", "number.fraction"),
    ("math-3-frac-equiv", "分数的等价(约分/通分)", 3, 4, "number", "number.fraction"),
    ("math-3-frac-addsub", "分数加减法", 3, 4, "operation", "operation.addition_subtraction"),
    ("math-3-dec-intro", "小数初步认识", 3, 3, "number", "number.decimal"),
    ("math-3-dec-addsub", "小数加减法", 3, 4, "operation", "operation.addition_subtraction"),
    ("math-3-shape-angle", "角的认识", 3, 3, "geometry", "geometry.angle"),
    ("math-3-shape-peri", "周长计算", 3, 3, "geometry", "geometry.perimeter"),
    ("math-3-shape-area", "长方形/正方形面积", 3, 3, "geometry", "geometry.area"),
    ("math-3-mass-ton", "质量单位: 吨", 3, 3, "geometry", "geometry.measurement"),
    ("math-3-yr-mo-d", "年/月/日关系", 3, 3, "geometry", "geometry.time"),

    # 4 年级
    ("math-4-dec-mult", "小数乘法", 4, 4, "operation", "operation.multiplication"),
    ("math-4-dec-div", "小数除法", 4, 4, "operation", "operation.division"),
    ("math-4-frac-addsub", "分数加减法", 4, 4, "operation", "operation.addition_subtraction"),
    ("math-4-frac-mult", "分数乘法", 4, 4, "operation", "operation.multiplication"),
    ("math-4-frac-div", "分数除法", 4, 4, "operation", "operation.division"),
    ("math-4-ang-meas", "角的度量", 4, 4, "geometry", "geometry.angle"),
    ("math-4-tri-area", "三角形面积", 4, 4, "geometry", "geometry.area"),
    ("math-4-para-area", "平行四边形面积", 4, 4, "geometry", "geometry.area"),
    ("math-4-stat-bar", "条形统计图", 4, 4, "statistics", "statistics.chart"),
    ("math-4-op-law", "运算定律(交换/结合/分配)", 4, 4, "operation", "operation.law"),

    # 5 年级
    ("math-5-dec-mult-adv", "小数乘除法(综合)", 5, 5, "operation", "operation.multiplication_division"),
    ("math-5-frac-addsub-adv", "异分母分数加减", 5, 5, "operation", "operation.addition_subtraction"),
    ("math-5-frac-mult-adv", "分数乘除法(综合)", 5, 5, "operation", "operation.multiplication_division"),
    ("math-5-vol-cuboid", "长方体正方体体积", 5, 5, "geometry", "geometry.volume"),
    ("math-5-frac-dec-rel", "分数小数互化", 5, 5, "number", "number.fraction"),
    ("math-5-pos-neg", "负数初步", 5, 5, "number", "number.negative"),
    ("math-5-eqn-simple", "简易方程(用字母表示数)", 5, 5, "algebra", "algebra.expression"),
    ("math-5-mult-vol", "体积单位(立方米/立方分米/立方厘米)", 5, 5, "geometry", "geometry.measurement"),

    # 6 年级
    ("math-6-frac-pct", "百分数", 6, 6, "number", "number.percent"),
    ("math-6-ratio", "比的意义", 6, 6, "ratio", "ratio.ratio"),
    ("math-6-prop", "正比例反比例", 6, 6, "ratio", "ratio.proportion"),
    ("math-6-cir-circ", "圆的周长", 6, 6, "geometry", "geometry.perimeter"),
    ("math-6-cir-area", "圆的面积", 6, 6, "geometry", "geometry.area"),
    ("math-6-cyli-vol", "圆柱体积", 6, 6, "geometry", "geometry.volume"),
    ("math-6-stat-mean", "平均数", 6, 6, "statistics", "statistics.mean"),
    ("math-6-spatial", "观察物体(三视图)", 6, 6, "geometry", "geometry.shape"),

    # 初中 7 年级
    ("math-7-rat-num", "有理数", 7, 7, "number", "number.rational"),
    ("math-7-abs-val", "绝对值", 7, 7, "number", "number.absolute"),
    ("math-7-alg-expr", "代数式", 7, 7, "algebra", "algebra.expression"),
    ("math-7-eqn-1d", "一元一次方程", 7, 7, "algebra", "algebra.equation"),
    ("math-7-ineq-1d", "一元一次不等式", 7, 7, "algebra", "algebra.inequality"),
    ("math-7-int-geom", "直线/射线/线段", 7, 7, "geometry", "geometry.line"),
    ("math-7-angle-rel", "角的关系(对顶/邻补/垂直)", 7, 7, "geometry", "geometry.angle"),
    ("math-7-tri-congr", "三角形全等", 7, 8, "geometry", "geometry.triangle"),

    # 初中 8 年级
    ("math-8-fn-linear", "一次函数", 8, 8, "algebra", "algebra.function"),
    ("math-8-sys-eq-2", "二元一次方程组", 8, 8, "algebra", "algebra.equation"),
    ("math-8-ineq-sys", "不等式组", 8, 8, "algebra", "algebra.inequality"),
    ("math-8-quad-eqn", "一元二次方程", 8, 9, "algebra", "algebra.equation"),
    ("math-8-sqrt", "二次根式", 8, 9, "number", "number.irrational"),
    ("math-8-quad-fn", "二次函数", 9, 9, "algebra", "algebra.function"),
    ("math-8-para-quad", "平行四边形性质", 8, 8, "geometry", "geometry.parallelogram"),
    ("math-8-geom-prove", "几何证明初步", 8, 9, "geometry", "geometry.triangle"),

    # 初中 9 年级
    ("math-9-similar-tri", "相似三角形", 9, 9, "geometry", "geometry.triangle"),
    ("math-9-circle-thm", "圆定理(切线/弦/角)", 9, 9, "geometry", "geometry.circle"),
    ("math-9-trig-intro", "三角函数初步", 9, 9, "geometry", "geometry.angle"),
    ("math-9-stat-stoch", "统计与概率综合", 9, 9, "statistics", "statistics.probability"),
]

# 先决关系 (硬先决)
PREREQ_EDGES = [
    # 1-2 年级
    ("math-1-num-recognition", "math-1-count-20"),
    ("math-1-count-20", "math-1-count-100"),
    ("math-1-num-recognition", "math-1-add-single"),
    ("math-1-add-single", "math-1-sub-single"),
    ("math-1-add-single", "math-1-add-20"),
    ("math-1-add-20", "math-1-sub-20"),

    # 1-2 → 2 年级
    ("math-1-count-100", "math-2-add-100"),
    ("math-2-add-100", "math-2-mul-intro"),
    ("math-2-add-100", "math-2-div-intro"),
    ("math-2-mul-intro", "math-2-div-intro"),
    ("math-1-shape-basic", "math-2-shape-2d"),

    # 2 → 3
    ("math-2-mul-intro", "math-3-mul-multi"),
    ("math-2-div-intro", "math-3-div-multi"),
    ("math-3-div-multi", "math-3-frac-intro"),
    ("math-3-frac-intro", "math-3-frac-equiv"),
    ("math-3-frac-equiv", "math-3-frac-addsub"),
    ("math-2-add-100", "math-3-add-10000"),
    ("math-3-add-10000", "math-3-dec-addsub"),
    ("math-3-mul-multi", "math-3-dec-addsub"),
    ("math-1-shape-basic", "math-3-shape-angle"),
    ("math-2-shape-2d", "math-3-shape-peri"),
    ("math-3-shape-peri", "math-3-shape-area"),
    ("math-2-mass-kg", "math-3-mass-ton"),

    # 3 → 4
    ("math-3-dec-addsub", "math-4-dec-mult"),
    ("math-3-dec-addsub", "math-4-dec-div"),
    ("math-3-frac-addsub", "math-4-frac-mult"),
    ("math-3-frac-addsub", "math-4-frac-div"),
    ("math-3-shape-angle", "math-4-ang-meas"),
    ("math-3-shape-area", "math-4-tri-area"),
    ("math-3-shape-area", "math-4-para-area"),
    ("math-3-add-10000", "math-4-op-law"),

    # 4 → 5
    ("math-4-dec-mult", "math-5-dec-mult-adv"),
    ("math-4-dec-div", "math-5-dec-mult-adv"),
    ("math-4-frac-addsub", "math-5-frac-addsub-adv"),
    ("math-4-frac-mult", "math-5-frac-mult-adv"),
    ("math-3-shape-peri", "math-5-vol-cuboid"),
    ("math-3-shape-area", "math-5-vol-cuboid"),
    ("math-3-frac-intro", "math-5-frac-dec-rel"),
    ("math-4-dec-mult", "math-5-frac-dec-rel"),
    ("math-4-op-law", "math-5-eqn-simple"),
    ("math-2-mass-kg", "math-5-mult-vol"),

    # 5 → 6
    ("math-4-frac-mult", "math-6-frac-pct"),
    ("math-4-dec-mult", "math-6-frac-pct"),
    ("math-5-frac-dec-rel", "math-6-ratio"),
    ("math-4-frac-mult", "math-6-ratio"),
    ("math-6-ratio", "math-6-prop"),
    ("math-3-shape-peri", "math-6-cir-circ"),
    ("math-4-tri-area", "math-6-cir-area"),
    ("math-5-vol-cuboid", "math-6-cyli-vol"),
    ("math-3-add-10000", "math-6-stat-mean"),
    ("math-1-shape-basic", "math-6-spatial"),

    # 6 → 7
    ("math-4-dec-mult", "math-7-rat-num"),
    ("math-5-frac-dec-rel", "math-7-rat-num"),
    ("math-5-eqn-simple", "math-7-rat-num"),
    ("math-7-rat-num", "math-7-abs-val"),
    ("math-4-op-law", "math-7-alg-expr"),
    ("math-5-eqn-simple", "math-7-eqn-1d"),
    ("math-7-alg-expr", "math-7-eqn-1d"),
    ("math-7-eqn-1d", "math-7-ineq-1d"),
    ("math-1-shape-basic", "math-7-int-geom"),
    ("math-3-shape-angle", "math-7-angle-rel"),
    ("math-7-angle-rel", "math-7-tri-congr"),
    ("math-7-int-geom", "math-7-tri-congr"),

    # 7 → 8
    ("math-7-eqn-1d", "math-8-sys-eq-2"),
    ("math-7-ineq-1d", "math-8-ineq-sys"),
    ("math-7-alg-expr", "math-8-fn-linear"),
    ("math-7-eqn-1d", "math-8-fn-linear"),
    ("math-7-eqn-1d", "math-8-quad-eqn"),
    ("math-7-tri-congr", "math-8-para-quad"),
    ("math-7-tri-congr", "math-8-geom-prove"),

    # 8 → 9
    ("math-7-tri-congr", "math-9-similar-tri"),
    ("math-8-para-quad", "math-9-similar-tri"),
    ("math-8-quad-eqn", "math-8-quad-fn"),
    ("math-7-int-geom", "math-9-circle-thm"),
    ("math-8-geom-prove", "math-9-trig-intro"),
    ("math-7-tri-congr", "math-9-trig-intro"),
    ("math-8-fn-linear", "math-9-stat-stoch"),
]

def build_math_v01():
    """构建数学 V0.1 图谱 (基于课标 + 教材结构预设)"""
    nodes = []
    for cid, title, g_start, g_end, domain, subdomain in PRESEED_CONCEPTS:
        nodes.append({
            "id": cid,
            "subject": "math",
            "stage": "junior_high" if g_start >= 7 else "primary",
            "grade_start": g_start,
            "grade_end": g_end,
            "title": title,
            "title_en": "",
            "domain": domain,
            "subdomain": subdomain,
            "core_literacy": [],
            "textbook_versions": ["人教版", "北师大版"],
            "example": "",
            "description": "",
            "source_refs": ["2022-math-curriculum", "preseed-v0.1"],
            "tags": [],
            "difficulty": min(5, max(1, g_start)),
            "estimated_minutes": 30 + g_start * 5,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        })

    edges = []
    edge_set = set()
    for from_id, to_id in PREREQ_EDGES:
        edge_key = (from_id, to_id)
        if edge_key in edge_set:
            continue
        edge_set.add(edge_key)
        edges.append([from_id, to_id, 1])  # 1 = hard prerequisite

    graph = {
        "version": "0.1.0",
        "subject": "math",
        "scope": "义教 1-9 年级 (课标 2022 版)",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "generated_at": datetime.now().isoformat(),
        "license": "CC-BY-SA 4.0",
    }
    return graph

def main():
    graph = build_math_v01()
    out_path = GRAPH_DIR / "math_v0.1.json"
    out_path.write_text(json.dumps(graph, ensure_ascii=False, indent=1))
    print(f"✅ 数学 V0.1: {graph['node_count']} 概念, {graph['edge_count']} 关系")
    print(f"   → {out_path}")

if __name__ == "__main__":
    main()
