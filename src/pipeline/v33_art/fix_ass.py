"""Final fix - longer appends for last 4 entries."""
import sys
sys.path.insert(0, '/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/src/pipeline/v33_art')
import generate

APPENDS = {
    "ART_G12_MU_07": ",自己说 1 句,跳给同桌看 1 次再跳 1 遍?",
    "ART_G12_MU_09": ",1 遍不差,保持 30 秒再改 1 次 30 秒?",
    "ART_G34_MU_01": ",和同学一起,保持 16 拍 1 遍不拖 1 拍?",
    "ART_G34_AR_05": ",自己看 1 次,碗能立 10 秒不倒 1 遍?",
}


def fix():
    fixed = 0
    skipped = []
    for cid, append in APPENDS.items():
        ass = generate.GENERATED[cid]["assessment_prompt"]
        old_len = len(ass)
        ass_stripped = ass.rstrip()
        if not ass_stripped.endswith("?"):
            skipped.append((cid, "no trailing ?"))
            continue
        ass_new = ass_stripped[:-1] + append
        new_len = len(ass_new)
        if 150 <= new_len <= 220:
            nc = ass_new.count("{{name}}")
            if nc != 3:
                skipped.append((cid, f"name count {nc}"))
                continue
            generate.GENERATED[cid]["assessment_prompt"] = ass_new
            fixed += 1
            print(f"  ✓ {cid} ass {old_len}→{new_len}")
        else:
            skipped.append((cid, new_len))
            print(f"  ✗ {cid} would be {new_len}")
    return fixed, skipped


if __name__ == "__main__":
    n, skip = fix()
    print(f"\nFixed {n} entries, skipped {len(skip)}")
    for cid, l in skip:
        print(f"  skipped {cid}: {l}")
