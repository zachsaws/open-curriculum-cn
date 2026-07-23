"""
Extend the last 2 descriptions that are still too short.
"""
import json
from pathlib import Path

DRAFT = Path("/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/data/v33_work/biology_drafts.json")

NEW_DESC = {
    "B_B4_03": "爸爸精子和妈妈卵子结合(受精)→ 在妈妈子宫住 280 天(怀孕)→ 从产道出来(分娩)→ 一直长到 18 岁才算大人。",
    "B_B5_01": "感冒、流感、新冠都由「病原体」——细菌、病毒、真菌——引起。三条传播路:打喷嚏飞沫、脏水脏食物、握手接触,一条就能扩散。",
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
