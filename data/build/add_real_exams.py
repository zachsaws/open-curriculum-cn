#!/usr/bin/env python3
"""
V4.0.1 真题试点 — 手动入库 8 道经典常考题
覆盖 math 3 个核心考点:
  - M_G4_GM_08 勾股定理 (3 道)
  - M_G4_QR_05 一元二次方程 (3 道)
  - M_G4_QR_11 二次函数 (2 道)

每题加 is_real_exam=True + tags 标 "经典题".

注: 这些是"经典常考题型", 不是某年某省的具体真题
   (中国中考真题版权分散, 公开带答案的完整题库难找).
   题型来自教学经验, 标记 is_real_exam=True 仅表示"经典常考".
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DST = ROOT / 'data' / 'exercises' / 'exercises_v1.json'

# 8 道经典题 (题型为 multiple_choice / fill_blank / short_answer)
REAL_EXAMS = [
    # ===== M_G4_GM_08 勾股定理 =====
    {
        'concept_id': 'M_G4_GM_08',
        'type': 'multiple_choice',
        'difficulty': 2,
        'bloom': '理解',
        'question': '已知直角三角形的两条直角边长分别为 6 和 8, 则斜边长为 ( )',
        'options': ['A. 10', 'B. 12', 'C. 14', 'D. 100'],
        'answer': 'A',
        'explanation': '勾股定理: 斜边² = 6² + 8² = 36 + 64 = 100, 所以斜边 = √100 = 10. 这是最经典的 6-8-10 直角三角形 (3-4-5 的 2 倍). D 是把平方结果 100 误当答案.',
    },
    {
        'concept_id': 'M_G4_GM_08',
        'type': 'fill_blank',
        'difficulty': 2,
        'bloom': '应用',
        'question': '一架 5 米长的梯子靠墙放置, 梯子底端距墙 3 米, 则梯子顶端距地面 ____ 米 (用勾股定理).',
        'answer': ['4'],
        'explanation': '把梯子、墙、地面看成一个直角三角形: 梯子是斜边 (5米), 梯子底端到墙的距离是一条直角边 (3米), 梯子顶端到地面的高度是另一条直角边. 5² = 3² + 高² → 高² = 25 - 9 = 16 → 高 = 4 米.',
    },
    {
        'concept_id': 'M_G4_GM_08',
        'type': 'short_answer',
        'difficulty': 3,
        'bloom': '应用',
        'question': '一根旗杆在地面上的影子长 12 米, 同时旁边一根 2 米高的竹竿影子长 3 米. 求旗杆的实际高度 (用勾股定理列式, 假设旗杆垂直).',
        'answer': '同一时刻太阳光线角度相同, 竹竿和旗杆的影子长度与实际高度成正比. 竹竿 2 米对应影子 3 米, 则比例 = 2/3. 旗杆实际高度 = 旗杆影子 × 2/3 = 12 × 2/3 = 8 米. 因为旗杆垂直于地面, 太阳光线、旗杆、地面构成直角三角形, 但本题用比例法更直接.',
        'explanation': '1. 能识别"同一时刻太阳光线相同"这一隐含条件;\n2. 知道"物体高度与影子长度成正比"这一规律 (因为太阳光线角度相同);\n3. 列出比例式 2/3 = 旗杆/12, 解出旗杆 = 8 米.\n注: 本题也可构造直角三角形, 但比例法是更常用的速解法.',
    },

    # ===== M_G4_QR_05 一元二次方程 =====
    {
        'concept_id': 'M_G4_QR_05',
        'type': 'multiple_choice',
        'difficulty': 1,
        'bloom': '理解',
        'question': '方程 x² = 16 的解是 ( )',
        'options': ['A. x = 4', 'B. x = -4', 'C. x = ±4', 'D. x = 8'],
        'answer': 'C',
        'explanation': 'x² = 16 是 x² - 16 = 0, 即 (x-4)(x+4) = 0, 所以 x = 4 或 x = -4. 直接开平方不要漏掉负根, 这是经典错误. A/B 只取了一个根, D 把 16 当 4² = 16 直接加 4 的错误.',
    },
    {
        'concept_id': 'M_G4_QR_05',
        'type': 'fill_blank',
        'difficulty': 2,
        'bloom': '应用',
        'question': '用因式分解法解方程 x² - 5x + 6 = 0, 则 x₁ = ____, x₂ = ____ (按从小到大顺序).',
        'answer': ['2', '3'],
        'explanation': '因式分解: x² - 5x + 6 = (x-2)(x-3) = 0, 所以 x = 2 或 x = 3. 常数项 6 拆成 (-2)×(-3) = 6, 一次项系数 -5 = -2 + (-3).',
    },
    {
        'concept_id': 'M_G4_QR_05',
        'type': 'short_answer',
        'difficulty': 3,
        'bloom': '应用',
        'question': '某商品原价 100 元, 因库存积压连续两次降价, 每次降价的百分率相同, 降价后价格为 81 元. 求每次降价的百分率.',
        'answer': '设每次降价的百分率为 x, 第一次降价后价格 = 100(1-x), 第二次降价后 = 100(1-x)². 由 100(1-x)² = 81, 得 (1-x)² = 0.81. 开平方: 1-x = ±0.9. 因 x 是百分率 (0 < x < 1), 故 1-x = 0.9, x = 0.1 = 10%. 所以每次降价 10%.',
        'explanation': '1. 能正确列出一元二次方程 100(1-x)² = 81 (核心: 连续两次降价用乘法);\n2. 能化简为 (1-x)² = 0.81;\n3. 知道 1-x 不能取负值 (因为 x < 1), 排除 1-x = -0.9 的增根;\n4. 最终求得 x = 10%.\n注: 增长率/降价率问题是中考常考应用题, 关键是把"连续两次"对应到 (1±x)².',
    },

    # ===== M_G4_QR_11 二次函数 =====
    {
        'concept_id': 'M_G4_QR_11',
        'type': 'multiple_choice',
        'difficulty': 2,
        'bloom': '理解',
        'question': '抛物线 y = x² - 2x - 3 的顶点坐标是 ( )',
        'options': ['A. (1, -4)', 'B. (-1, 0)', 'C. (1, 0)', 'D. (2, -3)'],
        'answer': 'A',
        'explanation': '配方: y = x² - 2x - 3 = (x-1)² - 4. 顶点式 (x-h)² + k 的顶点是 (h, k), 所以顶点为 (1, -4). 也可以用顶点公式 x = -b/(2a) = 2/2 = 1, 代入 y = 1-2-3 = -4. B/C/D 都不对.',
    },
    {
        'concept_id': 'M_G4_QR_11',
        'type': 'short_answer',
        'difficulty': 3,
        'bloom': '应用',
        'question': '一座拱桥的形状是抛物线 y = -0.1x² + 4, 河流方向是 x 轴, 桥面方向是 y 轴. 求: (1) 拱桥最高点的高度; (2) 拱桥与水面 (y=0) 的交点横坐标 (即桥的跨度).',
        'answer': '(1) 拱桥最高点即顶点. 配方: y = -0.1x² + 4 = -0.1(x-0)² + 4, 顶点 (0, 4). 所以拱桥最高点高度 = 4 米.\n(2) 桥与水面 y=0 的交点: 0 = -0.1x² + 4 → x² = 40 → x = ±√40 = ±2√10 ≈ ±6.32. 所以桥的跨度 = 2×2√10 = 4√10 ≈ 12.65 米.',
        'explanation': '1. 能识别 a<0 抛物线开口向下, 顶点是最高点;\n2. 配方求顶点坐标 (0, 4) — 拱桥最高 4 米;\n3. 令 y=0 解二次方程求 x, 正确取舍 (用 ± 号, 不漏负根);\n4. 跨度是两个交点横坐标之差 = 2×√40 = 4√10 米.',
    },
]


def main():
    # 加载已有
    out_data = json.load(open(DST))
    existing_ids = {ex['id'] for ex in out_data.get('exercises', [])}
    print(f'📂 已有 {len(existing_ids)} 题')

    # 真真题用 _901+ 高位号, 避开 LLM 跑的 _001-_005
    # 每个概念从 901 开始编号
    concept_real_count = {}
    for ex in out_data['exercises']:
        if ex.get('is_real_exam'):
            cid = ex['concept_id']
            concept_real_count[cid] = concept_real_count.get(cid, 0) + 1

    n_added = 0
    for ex in REAL_EXAMS:
        cid = ex['concept_id']
        n = concept_real_count.get(cid, 0) + 1
        ex_id = f"EX_{cid}_9{n:02d}"  # _901, _902, _903
        item = {
            'id': ex_id,
            'concept_id': cid,
            'type': ex['type'],
            'difficulty': ex['difficulty'],
            'question': ex['question'],
            'answer': ex['answer'],
            'explanation': ex['explanation'],
            'bloom': ex['bloom'],
            'is_real_exam': True,
            'tags': ['经典题', '常考'],
        }
        if ex['type'] == 'multiple_choice':
            item['options'] = ex['options']
        out_data['exercises'].append(item)
        existing_ids.add(ex_id)
        concept_real_count[cid] = n
        n_added += 1
        print(f'  ✅ {ex_id}: {ex["question"][:30]}...')

    # 保存
    with open(DST, 'w', encoding='utf-8') as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)
    print(f'\\n✅ 新增 {n_added} 道经典题, 总 {len(out_data["exercises"])} 题')


if __name__ == '__main__':
    main()
