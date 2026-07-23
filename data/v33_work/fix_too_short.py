"""
Extend 4 descriptions that are too short (53-59 chars, need 60-100).
"""
import json
from pathlib import Path

DRAFT = Path("/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/data/v33_work/biology_drafts.json")

NEW_DESC = {
    "B_B2_02": "植物有 5 个「进化驿站」:水里没根没叶的海带、墙根矮趴趴的苔藓、长卷卷嫩芽的蕨类、种子裸露的松树、种子有果肉包着的桃。",
    "B_B4_03": "爸爸精子和妈妈卵子结合(受精)→ 在子宫住 280 天(怀孕)→ 从妈妈产道出来(分娩)→ 长到 18 年才算大人。",
    "B_B5_01": "感冒、流感、新冠都由「病原体」——细菌、病毒、真菌——引起。三条传播路:打喷嚏飞沫、脏水脏食物、握手接触,缺一不可。",
    "B_B6_03": "酸奶的秘密是「乳酸菌」:牛奶煮到 40 度左右,加一勺市售酸奶当菌种,盖紧放 6-8 小时,菌把乳糖变乳酸,奶就变酸变稠。",
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
