"""
Fix 10 descriptions that were auto-trimmed mid-sentence.
Rewrite with complete sentences that fit in 60-100 chars.
"""
import json
from pathlib import Path

DRAFT = Path("/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/data/v33_work/biology_drafts.json")

NEW_DESC = {
    "B_B2_02": "植物有 5 个「进化驿站」:水里没根的海带、墙根矮趴趴的苔藓、长卷卷嫩芽的蕨类、种子裸露的松树、种子有果肉包的桃。",
    "B_B2_04": "一片森林里住着 1000 种昆虫、200 种鸟、50 种菌,看着乱,其实在互相「撑腰」——缺了任何一环,整片森林都可能塌。",
    "B_B3_01": "一个池塘就是一套完整「公司」:阳光和水是「房东」、浮游植物是「生产部」、鱼虾是「销售部」、细菌是「清洁工」,缺谁都倒闭。",
    "B_B4_01": "一朵桃花开过,会经历 4 件事:雄蕊撒花粉(传粉)、花粉长管子找卵子(受精)、子房膨大成桃、胚珠变核。一颗桃就是这全过程的产物。",
    "B_B4_03": "爸爸精子和妈妈卵子结合(受精)→ 在子宫住 280 天(怀孕)→ 从产道出来(分娩)→ 长到 18 年才成人。",
    "B_B4_09": "地球 46 亿年前没生命;约 35 亿年前海里冒出最简单「原始细胞」,慢慢变细菌、鱼、两栖、爬行、鸟、兽——人只是这进化树上一根小枝。",
    "B_B5_01": "感冒、流感、新冠都由「病原体」——细菌、病毒、真菌——引起。三条传播路:打喷嚏飞沫、脏水脏食物、握手接触。",
    "B_B6_02": "阳台种薄荷要 4 件事:见光(放南窗)、见水(土干浇)、见肥(每月一次)、见温度(15~25 度)。金鱼类似:换水留 1/3 老水、2 分钟吃完为准。",
    "B_B6_03": "酸奶的秘密是「乳酸菌」:牛奶煮到 40 度,加一勺市售酸奶当菌种,盖紧放 6-8 小时,菌把乳糖变乳酸,奶就变酸变稠。",
    "B_G79_CL_02": "DNA 长得像两条相互缠绕的梯子(双螺旋),横档由 A/T/C/G 4 种碱基配对组成——基因就是这一长串碱基里「有意义的句子」。",
}

def main():
    with open(DRAFT) as f:
        drafts = json.load(f)
    for d in drafts:
        if d["id"] in NEW_DESC:
            d["description"] = NEW_DESC[d["id"]]
            print(f"  fixed {d['id']}: {d['description']!r} (len={len(d['description'])})")
    with open(DRAFT, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2)
    print("Done.")

if __name__ == "__main__":
    main()
