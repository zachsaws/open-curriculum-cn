"""
V0.8 关系图谱补全 — 在 V0.7 基础上:

1. 给现有 167 条边加 `rel` 字段 (拆分 type 语义)
   - type=1 (硬先决, 同领域同段)  → rel="prerequisite"
   - type=0 (跨学科/软关联)        → rel="relates_to"
     (其中同学科跨段的 2 条, 语义上更接近 progresses_to, 已在下方按
      (同领域且跨段) 自动归为 progresses_to)

2. 补 35 条跨学段螺旋 (progresses_to) — 同领域跨学段先决链
   - math 23 条 (数与运算/图形几何/数量关系/统计概率/综合实践 5 域各 3-5 条)
   - chinese 6 条 (识字 + 阅读 两条主链)
   - english 6 条 (语音 + 语法 两条主链)

3. 补 88+ 条跨学科关联 (relates_to)
   - 用户精确 31 条 (M_G3_NS_15, P_P2_29 不存在, 跳过 / 替代)
   - 抽样 review 候选 60+ 条覆盖 17 学科对

输入: data/graph/all_v0.7.json
输出: data/graph/all_v0.8.json (+ 备份 all_v0.7.bak.json)
"""
import json
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GRAPH_DIR = ROOT / "data" / "graph"
SRC = GRAPH_DIR / "all_v0.7.json"
BAK = GRAPH_DIR / "all_v0.7.bak.json"
OUT = GRAPH_DIR / "all_v0.8.json"


# ---------------------------------------------------------------------------
# 新增 1: 跨学段 (progresses_to) — 35 条, 同领域跨学段先决链
# ---------------------------------------------------------------------------
# 每条: (from, to, rationale, weight, source)
# 来源: docs/reviews/relation-graph-review.md §2 (math 23) + §4 (cn 6 + en 6)
PROGRESSES_TO = [
    # ---- math 数与运算 (5) ----
    ("M_G1_NS_07", "M_G2_NS_03", "整数加减法 → 多位数乘除法 (G1-2 整数运算螺旋到 G3-4)", 0.95, "2022-math-NS"),
    ("M_G2_NS_09", "M_G3_QR_02", "整数四则混合运算 → 简易方程 (代数思维起点)", 0.90, "2022-math-NS"),
    ("M_G3_QR_02", "M_G4_QR_01", "简易方程 → 一元一次方程 (G5-6 → G7-9 螺旋)", 0.95, "2022-math-NS"),
    ("M_G1_NS_01", "M_G2_NS_01", "万以内数的认识 → 万以上数的认识 (G1-2 → G3-4 数感螺旋)", 0.95, "2022-math-NS"),
    ("M_G3_NS_01", "M_G4_NS_16", "分数意义 → 分式 (分数的代数推广, G5-6 → G7-9)", 0.90, "2022-math-NS"),

    # ---- math 图形与几何 (5) ----
    ("M_G1_GM_01", "M_G2_GM_04", "辨认立体图形 → 三角形分类 (从立体到平面, G1-2 → G3-4)", 0.85, "2022-math-GM"),
    ("M_G2_GM_04", "M_G3_GM_01", "三角形分类 → 圆的特征 (从直线形到曲线形)", 0.85, "2022-math-GM"),
    ("M_G3_GM_01", "M_G4_GM_17", "圆的特征 → 圆心角/弧/弦/扇形 (G5-6 → G7-9 圆知识深化)", 0.95, "2022-math-GM"),
    ("M_G1_GM_07", "M_G2_GM_13", "长度单位 → 长方形面积 (度量从一维到二维)", 0.95, "2022-math-GM"),
    ("M_G3_GM_07", "M_G4_GM_22", "圆柱表面积 → 立体图形表面积与体积 (G5-6 → G7-9 立体几何螺旋)", 0.85, "2022-math-GM"),

    # ---- math 数量关系 (5) ----
    ("M_G1_QR_05", "M_G2_QR_04", "认识时间 → 路程=速度×时间 (时间单位是速度公式前置)", 0.85, "2022-math-QR"),
    ("M_G2_QR_04", "M_G3_NS_13", "速度公式 → 正比例 (速度是比例的现实原型)", 0.95, "2022-math-QR"),
    ("M_G3_NS_13", "M_G4_QR_09", "正比例 → 一次函数 (正比例是函数的特例)", 0.95, "2022-math-QR"),
    ("M_G1_QR_01", "M_G2_NS_15", "用数或符号表达变化规律 → 用字母表示运算律 (G1-2 → G3-4 代数起点)", 0.90, "2022-math-QR"),
    ("M_G2_NS_15", "M_G4_NS_12", "用字母表示运算律 → 代数式 (G3-4 → G7-9 代数抽象)", 0.85, "2022-math-QR"),

    # ---- math 统计与概率 (5) ----
    ("M_G1_ST_01", "M_G2_ST_04", "数据分类 → 平均数 (从分类到度量集中趋势)", 0.85, "2022-math-ST"),
    ("M_G2_ST_04", "M_G3_ST_04", "平均数 → 中位数 (集中趋势量螺旋增加)", 0.85, "2022-math-ST"),
    ("M_G3_ST_04", "M_G4_ST_07", "中位数 → 极差/方差/标准差 (集中趋势 → 离散程度, G5-6 → G7-9)", 0.90, "2022-math-ST"),
    ("M_G3_ST_06", "M_G4_ST_09", "可能性定性描述 → 概率意义 (定性到定量)", 0.95, "2022-math-ST"),
    ("M_G3_ST_07", "M_G4_ST_10", "等可能事件 → 古典概型 (G5-6 → G7-9 概率精确化)", 0.95, "2022-math-ST"),

    # ---- math 综合与实践 (3) ----
    ("M_G2_PR_01", "M_G3_PR_01", "主题活动:曹冲称象 → 校园中的数学 (G3-4 → G5-6 实践主题螺旋)", 0.80, "2022-math-PR"),
    ("M_G3_PR_01", "M_G4_PR_01", "校园中的数学 → 项目式学习 (G5-6 → G7-9 综合实践深化)", 0.85, "2022-math-PR"),
    ("M_G1_QR_02", "M_G2_QR_02", "用数和运算解决简单问题 → 常见数量关系 (G1-2 → G3-4 抽象化)", 0.85, "2022-math-QR"),

    # ---- chinese 识字 (3) + 阅读 (3) — 6 条 ----
    ("CN_C1_AL_01", "CN_C2_AL_01", "认识常用字(身体行为天地自然) → 独立识字与写字 (G1-2 → G3-4)", 0.95, "2022-chinese-AL"),
    ("CN_C2_AL_01", "CN_C3_AL_01", "独立识字 → 主动通过多种方式独立识字 (G3-4 → G5-6)", 0.90, "2022-chinese-AL"),
    ("CN_C3_AL_01", "CN_C4_AL_01", "主动识字 → 策划开展语言文字活动 (G5-6 → G7-9 螺旋)", 0.85, "2022-chinese-AL"),
    ("CN_C1_LR_01", "CN_C2_LR_01", "阅读儿歌童话 → 阅读表现自然社会的作品 (G1-2 → G3-4 文学螺旋)", 0.90, "2022-chinese-LR"),
    ("CN_C2_LR_01", "CN_C3_LR_01", "表现自然社会 → 革命传统作品 (G3-4 → G5-6 阅读深度螺旋)", 0.85, "2022-chinese-LR"),
    ("CN_C3_LR_01", "CN_C4_LR_01", "革命传统作品 → 文学欣赏 (G5-6 → G7-9 文学阅读能力螺旋)", 0.90, "2022-chinese-LR"),

    # ---- english 语音 (3) + 语法 (3) — 6 条 ----
    ("EN_E1_PH_01", "EN_E2_PH_01", "26 个英文字母的认读 → 元音字母发音规则 (G1-2 → G3-4)", 0.95, "2022-english-PH"),
    ("EN_E2_PH_01", "EN_E3_PH_01", "元音字母发音规则 → 国际音标认读 (G3-4 → G5-6)", 0.95, "2022-english-PH"),
    ("EN_E3_PH_01", "EN_E4_PH_01", "国际音标认读 → 重音/节奏/语调综合运用 (G5-6 → G7-9 螺旋)", 0.90, "2022-english-PH"),
    ("EN_E1_GR_02", "EN_E2_GR_01", "一般现在时 → 现在进行时 (G1-2 → G3-4 时态螺旋)", 0.95, "2022-english-GR"),
    ("EN_E2_GR_01", "EN_E3_GR_01", "现在进行时 → 现在完成时 (G3-4 → G5-6 时态螺旋)", 0.90, "2022-english-GR"),
    ("EN_E3_GR_01", "EN_E4_GR_03", "现在完成时 → 状语从句 (G5-6 → G7-9 语法综合)", 0.85, "2022-english-GR"),
]


# ---------------------------------------------------------------------------
# 新增 2: 跨学科 (relates_to) — 100+ 条, 软关联
# ---------------------------------------------------------------------------
# 格式: (from, to, rationale, weight, source)
# 来源 1: 用户精确 31 条 (任务 §跨学科关系)
# 来源 2: docs/reviews/relation-graph-review.md §3 (88 条候选) 抽样
# 备注: M_G3_NS_15 用户意图"比例", 数据中实为 M_G3_NS_12 (比例), 已替换
# 备注: P_P2_29 用户意图"解直角三角形", 数据中不存在, 该条跳过
RELATES_TO = [
    # ---------- math → physics (10) ----------
    ("M_G2_QR_04", "P_P2_04", "速度公式 → 物理速度概念 (G3-4 math 公式 → G8 physics)", 0.90, "2022-cross-MP"),
    ("M_G2_GM_07", "P_P2_12", "面积 → 压强 p=F/S (G3-4 面积是 G8 压强先决)", 0.85, "2022-cross-MP"),
    ("M_G2_GM_13", "P_P2_17", "长方形面积 → 杠杆 (力臂×力的几何基础)", 0.80, "2022-cross-MP"),
    ("M_G2_NS_15", "P_P2_22", "用字母表示运算律 → 机械效率 (字母表达式迁移)", 0.70, "2022-cross-MP"),
    ("M_G3_NS_13", "P_P2_04", "正比例 → 速度 (v=s/t 是正比例)", 0.85, "2022-cross-MP"),
    ("M_G4_QR_07", "P_P2_04", "函数 → 速度 (速度公式是函数原型)", 0.80, "2022-cross-MP"),
    ("M_G4_QR_09", "P_P4_01", "一次函数 → 简单电路 (U=IR 是一次函数)", 0.80, "2022-cross-MP"),
    ("M_G4_QR_11", "P_P2_23", "二次函数 → 动能势能 (E=mv²/2 或 E=mgh)", 0.75, "2022-cross-MP"),
    ("M_G4_GM_29", "P_P2_17", "锐角三角函数 → 杠杆 (三角比用于力臂计算)", 0.70, "2022-cross-MP"),
    ("M_G3_NS_11", "P_P4_02", "比的意义 → 电流/电压/电阻 (U/I 是比)", 0.80, "2022-cross-MP"),
    # review 候选补充
    ("M_G2_GM_13", "P_P2_20", "长方形面积 → 功 (W=F·s 的几何理解)", 0.70, "2022-cross-MP"),
    ("M_G2_GM_13", "P_P2_21", "长方形面积 → 功率 (P=W/t 距离/时间应用)", 0.70, "2022-cross-MP"),
    ("M_G1_GM_07", "P_P1_07", "长度单位 → 密度 (ρ=m/V 需长度/体积单位)", 0.80, "2022-cross-MP"),

    # ---------- math → chemistry (10) ----------
    ("M_G3_NS_09", "CH_C3_06", "百分数 → 化学式计算 (质量分数是百分数应用)", 0.90, "2022-cross-MC"),
    ("M_G3_NS_11", "CH_C3_03", "比的意义 → 化学式 (化学式是元素质量比)", 0.85, "2022-cross-MC"),
    ("M_G3_NS_13", "CH_C4_07", "正比例 → 化学反应中的能量 (热量计算 Q=cmΔt)", 0.75, "2022-cross-MC"),
    ("M_G4_QR_09", "CH_C3_03", "一次函数 → 化学式 (浓度-体积关系)", 0.70, "2022-cross-MC"),
    # review 候选
    ("M_G3_NS_09", "CH_C2_05", "百分数 → 常见的酸 (浓度是百分数)", 0.80, "2022-cross-MC"),
    ("M_G3_NS_12", "CH_C3_04", "比例 → 化学方程式 (方程式配平是比例)", 0.90, "2022-cross-MC"),
    ("M_G2_NS_15", "CH_C3_03", "用字母表示运算律 → 化学式 (字母+数字表示)", 0.70, "2022-cross-MC"),
    ("M_G3_NS_05", "CH_C3_06", "分数乘除法 → 化学式计算 (1/2 H₂O 等系数)", 0.80, "2022-cross-MC"),
    ("M_G2_ST_04", "CH_C3_05", "平均数 → 相对原子质量 (加权平均)", 0.60, "2022-cross-MC"),
    ("M_G4_QR_07", "CH_C3_04", "函数 → 化学方程式 (反应速率函数关系)", 0.70, "2022-cross-MC"),

    # ---------- math → biology (11) ----------
    ("M_G2_ST_05", "B_B3_03", "平均数 → 能量流动 (能量逐级递减是平均/百分比)", 0.80, "2022-cross-MB"),
    ("M_G3_NS_13", "B_B3_01", "正比例 → 生态系统 (种群数量模型)", 0.75, "2022-cross-MB"),
    ("M_G3_NS_12", "B_B4_05", "比例 → 基因传递 (孟德尔 3:1 1:1 比例)", 0.90, "2022-cross-MB"),  # 替代用户 M_G3_NS_15
    # review 候选
    ("M_G2_ST_05", "B_B3_01", "平均数 → 生态系统 (种群数量用平均数)", 0.80, "2022-cross-MB"),
    ("M_G2_ST_02", "B_B2_01", "条形统计图 → 生物分类 (分类图表是数据可视化)", 0.60, "2022-cross-MB"),
    ("M_G4_ST_08", "B_B4_07", "随机事件 → 性别决定 (50% 概率)", 0.70, "2022-cross-MB"),
    ("M_G4_ST_10", "B_B4_06", "古典概型 → 基因传递 (孟德尔分离定律是概率)", 0.90, "2022-cross-MB"),
    ("M_G3_NS_08", "B_B3_03", "负数 → 能量流动 (能量收支正负)", 0.50, "2022-cross-MB"),
    ("M_G3_NS_13", "B_B1_04", "正比例 → 结构层次 (细胞→组织→器官 是包含关系)", 0.50, "2022-cross-MB"),
    ("M_G4_QR_07", "B_B1_07", "函数 → 呼吸系统 (呼吸速率函数)", 0.60, "2022-cross-MB"),
    ("M_G2_GM_13", "B_B1_01", "面积 → 细胞 (细胞表面积/体积比)", 0.65, "2022-cross-MB"),

    # ---------- math → info_tech (8) ----------
    ("M_G3_NS_11", "IT_I2_05", "比的意义 → 循环结构 (循环变量步长是比)", 0.75, "2022-cross-MI"),
    ("M_G4_QR_09", "IT_I3_03", "一次函数 → 变量与数据类型 (函数即变量映射)", 0.80, "2022-cross-MI"),
    ("M_G3_ST_05", "IT_I1_04", "平均数 → 数据可视化 (平均数是描述统计基础)", 0.85, "2022-cross-MI"),
    # review 候选
    ("M_G2_ST_02", "IT_I1_04", "条形统计图 → 数据可视化 (统计图是 IT 基础)", 0.90, "2022-cross-MI"),
    ("M_G2_ST_05", "IT_I1_05", "平均数 → 数据分析与预测", 0.80, "2022-cross-MI"),
    ("M_G2_QR_04", "IT_I1_05", "速度公式 → 数据分析与预测 (建模原型)", 0.70, "2022-cross-MI"),
    ("M_G3_QR_01", "IT_I3_03", "用字母表示数 → 变量与数据类型 (变量概念在 math 先出)", 0.90, "2022-cross-MI"),
    ("M_G4_QR_07", "IT_I3_04", "函数 → 函数与模块 (数学函数是编程函数先决)", 0.90, "2022-cross-MI"),

    # ---------- math → geography (8) ----------
    ("M_G2_ST_05", "G_G10_06", "平均数 → 中国农业 (农业产量/人均数据)", 0.80, "2022-cross-MG"),
    ("M_G3_NS_13", "G_G3_01", "正比例 → 人口 (人口增长模型)", 0.75, "2022-cross-MG"),
    # review 候选
    ("M_G2_QR_04", "G_G2_02", "速度公式 → 气温与降水 (距离/速度用于地理测算)", 0.70, "2022-cross-MG"),
    ("M_G2_GM_13", "G_G10_03", "长方形面积 → 中国地形 (国土面积计算)", 0.80, "2022-cross-MG"),
    ("M_G2_ST_04", "G_G2_02", "平均数 → 气温与降水 (气候数据用平均)", 0.80, "2022-cross-MG"),
    ("M_G2_ST_02", "G_G3_01", "条形统计图 → 人口 (人口数据图)", 0.80, "2022-cross-MG"),
    ("M_G2_GM_13", "G_G1_05", "面积 → 等高线 (面积/比例尺)", 0.70, "2022-cross-MG"),
    ("M_G3_ST_01", "G_G10_06", "复式条形统计图 → 中国农业 (农业数据)", 0.60, "2022-cross-MG"),

    # ---------- math → history (2) ----------
    ("M_G2_ST_01", "H_H1_CA_01", "数据收集 → 早期中华文明 (史料数据收集)", 0.50, "2022-cross-MH"),
    ("M_G3_QR_04", "H_H2_CM_01", "列举策略 → 鸦片战争 (历史事件因果列举)", 0.40, "2022-cross-MH"),

    # ---------- chinese → history (7) ----------
    ("CN_C2_AL_01", "H_H1_CA_05", "独立识字 → 汉代 (汉代文字演变)", 0.70, "2022-cross-CH"),
    ("CN_C2_LR_01", "H_H1_CA_07", "阅读自然社会 → 隋唐盛世 (文学反映社会)", 0.80, "2022-cross-CH"),
    # review 候选
    ("CN_C3_LR_01", "H_H2_CM_01", "革命传统文艺作品 → 鸦片战争 (文学反映历史)", 0.80, "2022-cross-CH"),
    ("CN_C3_LR_01", "H_H2_CM_05", "革命传统作品 → 辛亥革命 (同上)", 0.80, "2022-cross-CH"),
    ("CN_C4_LR_01", "H_H1_CA_10", "文学欣赏 → 古代科技文化 (文学反映科技史)", 0.70, "2022-cross-CH"),
    ("CN_C4_TH_01", "H_H4_WB_04", "思辨性阅读 → 启蒙运动 (思辨能力迁移)", 0.60, "2022-cross-CH"),
    ("CN_C3_BO_01", "H_H1_CA_07", "整本书阅读 → 隋唐盛世 (经典名著时代背景)", 0.70, "2022-cross-CH"),

    # ---------- chinese → english (4) ----------
    ("CN_C1_AL_05", "EN_E1_PH_01", "汉语拼音 → 英文字母 (拼音/字母系统迁移)", 0.90, "2022-cross-CE"),
    ("CN_C2_PR_02", "EN_E2_TX_02", "获取整合信息 → 提取关键信息 (G3-4 阅读策略同段)", 0.80, "2022-cross-CE"),
    ("CN_C2_WR_01", "EN_E2_SK_03", "写清楚一件事 → 书写简单短文 (写作能力迁移)", 0.80, "2022-cross-CE"),
    ("CN_C1_LR_01", "EN_E1_TX_01", "阅读儿歌童话 → 听说对话故事 (语篇阅读能力)", 0.70, "2022-cross-CE"),

    # ---------- english → chinese (2) — 用户精确列表里的方向 ----------
    ("EN_E3_CU_02", "CN_C2_AL_01", "中外文化 → 汉字 (跨文化理解中文字)", 0.70, "2022-cross-EC"),
    ("EN_E3_TP_02", "CN_C3_WR_01", "世界与科技 → 记实作文 (科技题材写作)", 0.65, "2022-cross-EC"),

    # ---------- physics → chemistry (7) ----------
    ("P_P1_09", "CH_C6_02", "原子结构 → 原子结构 (物理先讲, 化学复用)", 0.90, "2022-cross-PC"),
    ("P_P4_03", "CH_C3_04", "欧姆定律 → 化学方程式 (定量关系迁移)", 0.70, "2022-cross-PC"),
    # review 候选
    ("P_P1_08", "CH_C6_01", "分子动理论 → 分子与原子 (分子概念物理先出)", 0.80, "2022-cross-PC"),
    ("P_P1_07", "CH_C1_02", "密度 → 纯净物与混合物 (物质属性认识)", 0.70, "2022-cross-PC"),
    ("P_P1_03", "CH_C4_01", "物态变化 → 物质的变化 (物理变化→化学变化衔接)", 0.90, "2022-cross-PC"),
    ("P_P5_02", "CH_C4_02", "能量守恒 → 质量守恒 (守恒定律跨学科)", 0.80, "2022-cross-PC"),
    ("P_P2_22", "CH_C3_06", "机械效率 → 化学式计算 (效率概念迁移)", 0.50, "2022-cross-PC"),

    # ---------- physics → biology (1) ----------
    ("P_P2_15", "B_B1_07", "流体压强与流速 → 血液循环 (血压流速)", 0.85, "2022-cross-PB"),

    # ---------- biology → chemistry (4) ----------
    ("B_B1_01", "CH_C6_01", "细胞 → 分子与原子 (生物体由分子构成)", 0.75, "2022-cross-BC"),
    # review 候选
    ("B_B1_04", "CH_C3_01", "结构层次 → 元素 (生物体由元素组成)", 0.70, "2022-cross-BC"),
    ("B_B1_07", "CH_C2_05", "呼吸系统 → 常见的酸 (CO₂ 溶于水是碳酸)", 0.60, "2022-cross-BC"),
    ("B_B3_04", "CH_C4_02", "物质循环 → 质量守恒 (碳循环是守恒实例)", 0.90, "2022-cross-BC"),

    # ---------- info_tech → art (5) ----------
    ("IT_I6_01", "ART_A5_02", "AI 基础 → 短视频创作 (AI 用于创作)", 0.80, "2022-cross-IA"),
    ("IT_I1_04", "ART_A2_05", "数据可视化 → 美术欣赏 (数据可视化是设计技能)", 0.65, "2022-cross-IA"),
    # review 候选
    ("IT_I6_02", "ART_A5_02", "机器学习 → 短视频创作", 0.70, "2022-cross-IA"),
    ("IT_I1_04", "ART_A2_07", "数据可视化 → 设计基础", 0.70, "2022-cross-IA"),
    ("IT_I3_04", "ART_A2_05", "函数与模块 → 美术欣赏 (模块化思维迁移)", 0.55, "2022-cross-IA"),

    # ---------- science → physics (6) ----------
    ("SC_S2_MS_05", "P_P3_05", "光的反射 → 光的反射定律 (小学科学→初中物理)", 0.90, "2022-cross-SP"),
    ("SC_S2_MS_05", "P_P3_07", "光的反射 → 折射", 0.80, "2022-cross-SP"),
    ("SC_S2_MS_05", "P_P3_08", "光的反射 → 凸透镜", 0.80, "2022-cross-SP"),
    ("SC_S3_MS_05", "P_P2_17", "简单机械 → 杠杆", 0.90, "2022-cross-SP"),
    ("SC_S3_MS_05", "P_P2_19", "简单机械 → 斜面", 0.90, "2022-cross-SP"),
    ("SC_S3_MS_04", "P_P4_01", "简单电路 → 简单电路", 0.90, "2022-cross-SP"),

    # ---------- science → other (2) ----------
    ("SC_S1_TE_01", "M_G1_QR_07", "制作模型 → 模型意识 (模型认知跨学科)", 0.70, "2022-cross-SX"),
    ("SC_S3_LS_01", "B_B5_01", "微生物 → 传染病 (微生物是传染病源)", 0.80, "2022-cross-SB"),

    # ---------- pe_health → biology (5) ----------
    ("PE_PE3_02", "B_B1_07", "中长跑 → 呼吸系统 (运动与呼吸)", 0.90, "2022-cross-PB"),
    ("PE_PE3_02", "B_B1_08", "中长跑 → 血液循环 (运动与心肺)", 0.90, "2022-cross-PB"),
    ("PE_PE3_02", "B_B1_09", "中长跑 → 泌尿系统 (运动与代谢)", 0.80, "2022-cross-PB"),
    ("PE_PE5_04", "B_B4_03", "青春期健康 → 人的生殖 (健康与生殖)", 0.90, "2022-cross-PB"),
    ("PE_PE5_07", "B_B5_04", "急救 → 用药与急救 (急救知识跨学科)", 0.90, "2022-cross-PB"),

    # ---------- pe_health → physics (3) ----------
    ("PE_PE3_01", "P_P2_04", "短跑 → 速度 (跑步速度)", 0.80, "2022-cross-PP"),
    ("PE_PE3_04", "P_P2_20", "跳高跳远 → 功 (跳的能量)", 0.70, "2022-cross-PP"),
    ("PE_PE3_04", "P_P2_23", "跳高跳远 → 动能与势能 (势能转化)", 0.80, "2022-cross-PP"),

    # ---------- art → math (2) ----------
    ("ART_A1_01", "M_G1_QR_01", "音乐节奏 → 用数或符号表达规律 (节奏=规律)", 0.60, "2022-cross-AM"),
    ("ART_A2_07", "M_G4_GM_11", "设计基础 → 平行四边形 (设计几何)", 0.50, "2022-cross-AM"),

    # ---------- labor → other (4) ----------
    ("L_L1_04", "B_B5_01", "公共卫生 → 传染病 (公共卫生与疾病)", 0.80, "2022-cross-LB"),
    ("L_L3_02", "B_B1_06", "简单烹饪 → 消化系统 (烹饪与消化)", 0.70, "2022-cross-LB"),
    ("L_L3_02", "CH_C5_02", "简单烹饪 → 化学与健康 (烹饪与食品化学)", 0.60, "2022-cross-LC"),
    ("L_L1_03", "PE_PE5_03", "家务劳动 → 运动与健康 (劳动与健康)", 0.60, "2022-cross-LP"),

    # ---------- geography → biology (2) ----------
    ("G_G2_03", "B_B3_06", "主要气候类型 → 生物圈 (气候决定生物分布)", 0.80, "2022-cross-GB"),
    ("G_G2_03", "B_B2_02", "主要气候类型 → 植物主要类群 (气候→植被)", 0.80, "2022-cross-GB"),

    # ---------- morality_law → other (3) ----------
    ("ML_ML_G2_04", "B_B3_04", "爱护环境 → 物质循环 (环保意识)", 0.70, "2022-cross-MLB"),
    ("ML_ML_G9_01", "H_H3_CR_04", "改革开放 → 改革开放 (同步进行)", 0.90, "2022-cross-MLH"),
    ("ML_ML_G9_04", "H_H4_WC_06", "国际责任 → 经济全球化 (国际责任)", 0.80, "2022-cross-MLH"),
]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def stage_key(node):
    """返回节点的 (subject, stage) 用于判断是否同学科跨段"""
    return (node.get("subject"), node.get("stage"))


def classify_existing_edge(edge, node_map):
    """给现有 edge 分配 rel 字段

    规则:
    - type=1 (硬先决, 默认)        → prerequisite
    - type=0 (跨学科/软关联)
        - 跨学科 (from 学科 != to 学科)  → relates_to
        - 同领域跨段 (同一学科, 跨 stage) → progresses_to
        - 同学科同段 (少见, 兜底)        → relates_to
    """
    t = edge.get("type", 1)
    if t == 1:
        return "prerequisite"
    # type=0 分流
    f = node_map.get(edge["from"])
    to = node_map.get(edge["to"])
    if not f or not to:
        return "relates_to"  # 兜底
    if f.get("subject") != to.get("subject"):
        return "relates_to"
    if f.get("stage") != to.get("stage"):
        return "progresses_to"
    return "relates_to"


def main():
    # 1. 加载 V0.7
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    node_map = {n["id"]: n for n in data["nodes"]}
    existing_edges = data["edges"]

    # 2. 备份
    shutil.copy2(SRC, BAK)
    print(f"📦 备份: {BAK.name}")

    # 3. 给现有边加 rel 字段 (不破坏 from/to/type)
    rel_counts = defaultdict(int)
    for e in existing_edges:
        rel = classify_existing_edge(e, node_map)
        e["rel"] = rel
        rel_counts[rel] += 1
    print(f"\n现有 {len(existing_edges)} 条边加 rel 字段:")
    for r, c in rel_counts.items():
        print(f"  {r}: {c}")

    # 4. 准备新边: 收集所有候选
    candidates = []
    for from_id, to_id, rationale, weight, source in PROGRESSES_TO:
        candidates.append({
            "from": from_id, "to": to_id, "rel": "progresses_to",
            "rationale": rationale, "weight": weight, "source": source,
        })
    for from_id, to_id, rationale, weight, source in RELATES_TO:
        candidates.append({
            "from": from_id, "to": to_id, "rel": "relates_to",
            "rationale": rationale, "weight": weight, "source": source,
        })

    # 5. 验证 + 去重
    existing_keys = {(e["from"], e["to"]) for e in existing_edges}
    new_edges = []
    skipped = defaultdict(int)
    seen_new = set()
    for c in candidates:
        # 自环
        if c["from"] == c["to"]:
            skipped["self_loop"] += 1
            continue
        # 悬空
        if c["from"] not in node_map:
            skipped[f"missing_from:{c['from']}"] += 1
            continue
        if c["to"] not in node_map:
            skipped[f"missing_to:{c['to']}"] += 1
            continue
        # 重复 (from, to) 跳过
        key = (c["from"], c["to"])
        if key in existing_keys or key in seen_new:
            skipped["duplicate"] += 1
            continue
        seen_new.add(key)
        new_edges.append(c)

    print(f"\n新增候选 {len(candidates)} 条, 实际新增 {len(new_edges)} 条, 跳过 {sum(skipped.values())} 条")
    if skipped:
        for k, v in skipped.items():
            print(f"  {k}: {v}")

    # 6. 合并
    data["edges"].extend(new_edges)

    # 7. 写 V0.8
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 8. 统计
    final_counts = defaultdict(int)
    for e in data["edges"]:
        final_counts[e.get("rel", "?")] += 1

    # 跨学科 / 跨学段 统计
    cross_subj = sum(
        1 for e in data["edges"]
        if node_map.get(e["from"], {}).get("subject") != node_map.get(e["to"], {}).get("subject")
    )
    cross_stage = sum(
        1 for e in data["edges"]
        if node_map.get(e["from"], {}).get("subject") == node_map.get(e["to"], {}).get("subject")
        and node_map.get(e["from"], {}).get("stage") != node_map.get(e["to"], {}).get("stage")
    )
    same_domain = len(data["edges"]) - cross_subj - cross_stage

    print(f"\n✅ 写入 {OUT.name}: {len(data['nodes'])} 概念 + {len(data['edges'])} 边")
    print(f"\n按 rel 分布:")
    for r in ["prerequisite", "progresses_to", "relates_to"]:
        print(f"  {r}: {final_counts.get(r, 0)}")
    print(f"\n按结构分布:")
    print(f"  同领域同段 (intra-domain): {same_domain}")
    print(f"  同领域跨段 (跨学段螺旋):   {cross_stage}")
    print(f"  跨学科 (relates_to):       {cross_subj}")


if __name__ == "__main__":
    main()
