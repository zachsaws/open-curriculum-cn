"""Post-validation: 列出所有不达标项, 不写入"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
IN_GEN = ROOT / "src" / "pipeline" / "v33_art" / "generate.py"
IN = ROOT / "data" / "v33_inputs" / "art_input.json"

sys.path.insert(0, str(ROOT / "src" / "pipeline" / "v33_art"))
import generate as gen

BANNED = ["理解", "培养", "掌握", "运用", "知识点", "课标", "教学目标", "含义", "定义",
          "本概念", "该概念", "本节", "本文", "通过本", "课标要求", "具体含义"]
TEMPLATE_BAD = [
    "用自己的话解释",
    "独立完成相关题目",
    "举出一个生活中的例子",
    "在 X 课上",
    "在音乐课上",
    "在美术课上",
    "在舞蹈课上",
    "在戏剧课上",
    "在影视课上",
]


def check():
    issues = []
    for cid, g in gen.GENERATED.items():
        d = g["description"]
        a = g["assessment_prompt"]
        dl = len(d)
        al = len(a)
        nc = a.count("{{name}}")
        nl = a.count("\n")
        banned_hits = [w for w in BANNED if w in d or w in a]
        tmpl_hits = [w for w in TEMPLATE_BAD if w in d or w in a]
        problems = []
        if not (60 <= dl <= 100):
            problems.append(f"desc_len={dl}")
        if not (150 <= al <= 220):
            problems.append(f"ass_len={al}")
        if nc != 3:
            problems.append(f"name_count={nc}")
        if nl < 2:
            problems.append(f"newline_count={nl}")
        if banned_hits:
            problems.append(f"banned={banned_hits}")
        if tmpl_hits:
            problems.append(f"template={tmpl_hits}")
        if problems:
            issues.append((cid, problems, dl, al))
    return issues


if __name__ == "__main__":
    issues = check()
    if not issues:
        print("✅ All 78 pass validation")
    else:
        print(f"❌ {len(issues)} entries have issues:")
        for cid, probs, dl, al in issues:
            print(f"  {cid:18s} desc={dl:3d} ass={al:3d}  {', '.join(probs)}")
