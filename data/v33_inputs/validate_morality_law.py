#!/usr/bin/env python3
"""
Post-validation for V3.3.1 morality_law:
- desc 60-100 字
- ass 150-220 字
- ass 含 {{name}} 正好 3 次
- ass 含 \\n (转义的反斜杠+n) 至少 2 次
- 禁词 (理解/培养/掌握/运用/知识点/课标/教学目标/含义/定义/本概念/该概念/本节/本文/通过本/课标要求/具体含义) = 0
- 模板句 = 0
"""
import json
import re
from pathlib import Path

P = Path("/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/data/graph/morality_law_v33_llm.json")
d = json.loads(P.read_text(encoding="utf-8"))
concepts = d["concepts"]

BANNED = ["理解", "培养", "掌握", "运用", "知识点", "课标", "教学目标",
          "含义", "定义", "本概念", "该概念", "本节", "本文", "通过本",
          "课标要求", "具体含义"]
TEMPLATE = ["独立完成相关题目", "举出一个生活中的例子", "用自己的话解释"]

# 模板 "在 X 课上, {name} 能否" 间接: 我们更严格, 检测 "在..课上" 也算
# 但实际上 description 都不该出现, ass 也不该出现.
# 让我把 "在 X 课上" 也加入禁句. 但"课堂上"不算 (因为是自然词).
TEMPLATE_PATTERNS = [
    r"在.{1,4}课上,.*?\{name\}.*?能否",
    r"用自己的话解释",
    r"独立完成相关题目",
    r"举出一个生活中的例子",
]

issues = {
    "desc_too_short": [],
    "desc_too_long": [],
    "ass_too_short": [],
    "ass_too_long": [],
    "name_count_wrong": [],
    "newline_count_wrong": [],
    "banned_word": [],
    "template_pattern": [],
}

def char_count(s):
    """字数 = 中文字符 + 英文字母 + 数字 + 标点 (粗略)"""
    return len(s)

def count_name(s):
    return s.count("{{name}}")

def count_newline_lit(s):
    # JSON 里的 \n 实际是 chr(10) 换行符 (与 math_v33_llm.json 标杆一致)
    return s.count(chr(10))

desc_lens = []
ass_lens = []

for c in concepts:
    cid = c["id"]
    desc = c["description"]
    ass = c["assessment_prompt"]

    dl = char_count(desc)
    al = char_count(ass)
    desc_lens.append(dl)
    ass_lens.append(al)

    if dl < 60:
        issues["desc_too_short"].append((cid, dl, desc[:60]))
    if dl > 100:
        issues["desc_too_long"].append((cid, dl, desc[:60]))

    if al < 150:
        issues["ass_too_short"].append((cid, al, ass[:80]))
    if al > 220:
        issues["ass_too_long"].append((cid, al, ass[:80]))

    nc = count_name(ass)
    if nc != 3:
        issues["name_count_wrong"].append((cid, nc))

    nl = count_newline_lit(ass)
    if nl < 2:
        issues["newline_count_wrong"].append((cid, nl))

    for w in BANNED:
        if w in desc or w in ass:
            issues["banned_word"].append((cid, w, "desc" if w in desc else "ass"))
            break

    for pat in TEMPLATE_PATTERNS:
        if re.search(pat, ass):
            issues["template_pattern"].append((cid, pat))
            break

# 报告
print(f"=== 总数: {len(concepts)} ===\n")
print(f"description 长度: min={min(desc_lens)}, max={max(desc_lens)}, avg={sum(desc_lens)/len(desc_lens):.1f}")
print(f"assessment 长度: min={min(ass_lens)}, max={max(ass_lens)}, avg={sum(ass_lens)/len(ass_lens):.1f}\n")

print("=== Issues ===")
for k, v in issues.items():
    print(f"{k}: {len(v)}")
    for item in v[:5]:
        print(f"  {item}")
    if len(v) > 5:
        print(f"  ... and {len(v)-5} more")

print(f"\n=== Total failures (any rule violated): {sum(len(v) for v in issues.values())} ===")

# 写详细报告
report_path = Path("/Users/tianxiang/.minimax-agent-cn/projects/v33_validation_morality_law.txt")
with report_path.open("w", encoding="utf-8") as f:
    f.write(f"validation report for morality_law_v33_llm.json\n")
    f.write(f"total concepts: {len(concepts)}\n\n")
    f.write(f"desc_len: min={min(desc_lens)} max={max(desc_lens)} avg={sum(desc_lens)/len(desc_lens):.1f}\n")
    f.write(f"ass_len:  min={min(ass_lens)} max={max(ass_lens)} avg={sum(ass_lens)/len(ass_lens):.1f}\n\n")
    for k, v in issues.items():
        f.write(f"{k}: {len(v)}\n")
        for item in v:
            f.write(f"  {item}\n")
print(f"\nreport -> {report_path}")
