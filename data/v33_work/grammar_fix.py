"""
Grammar fix: remove misplaced pronouns (他/她/它/自己) inserted right after {{name}} by
auto-fix pass, and normalize the pronoun at the post-comma position to "自己" (gender-neutral,
matches math PoC style).

Patterns to fix:
  给{{name}}他X,她Y  →  给{{name}}X,自己Y
  给{{name}}她X,他Y  →  给{{name}}X,自己Y
  给{{name}}它X,他Y  →  给{{name}}X,自己Y
  让{{name}}他X,她Y  →  让{{name}}X,自己Y
  看到{{name}}他X,她Y → 看到{{name}}X,自己Y
  ...

Also, even when the original is correct (e.g. {{name}}能不能X), we want to convert
the "pronoun" form to "自己" if used. Otherwise keep {{name}}.
"""
import json
import re
from pathlib import Path

DRAFT = Path("/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/data/v33_work/biology_drafts.json")

# Pattern: 给/让/问/让/桌上/给.*?看/指着/给/给.*?  {{name}}  [pronoun]  ...  ,  [pronoun2]  ...
# We want to:
# 1) Remove [pronoun] right after {{name}}
# 2) Replace [pronoun2] after comma with "自己"

PRON = "他|她|它|自己"

def fix_line(line):
    # Step 1: remove pronoun right after {{name}}
    line = re.sub(r"(\{\{name\}\})(他|她|它|自己)", r"\1", line)
    # Step 2: replace pronoun immediately after a comma with 自己
    line = re.sub(r",(他|她|它|自己)", r",自己", line)
    # Also handle pronoun at start (e.g. "他会不会..." at start of a clause) — unlikely after step 1
    return line


def main():
    with open(DRAFT) as f:
        drafts = json.load(f)

    for d in drafts:
        lines = d["assessment_prompt"].split("\n")
        new_lines = [fix_line(l) for l in lines]
        d["assessment_prompt"] = "\n".join(new_lines)

    with open(DRAFT, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2)
    print("Grammar pass done.")


if __name__ == "__main__":
    main()
