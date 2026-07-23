"""
Build & validate biology_v33_llm.json
- Read input, read drafts (id -> desc + assessment)
- Produce final output JSON with all original fields + description + assessment_prompt
- Run post-validation per V3.3.1 spec:
  * desc 60-100
  * ass 150-220
  * {{name}} exactly 3
  * \n at least 2
  * banned = 0
- Print real numbers
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path("/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn")
IN = ROOT / "data" / "v33_inputs" / "biology_input.json"
DRAFT = ROOT / "data" / "v33_work" / "biology_drafts.json"
OUT = ROOT / "data" / "graph" / "biology_v33_llm.json"

BANNED = ["理解", "培养", "掌握", "运用", "知识点", "课标", "教学目标", "含义",
          "定义", "本概念", "该概念", "本节", "本文", "通过本", "课标要求", "具体含义"]

# 模板词
TPL_PATTERNS = [
    r"在.*课上,?\s*\{\{name\}\}",
    r"用自己的话解释.*含义",
    r"独立完成相关题目",
    r"举出一个生活中的例子",
]


def validate_one(c):
    """返回 (errors, desc_len, ass_len, name_count, newline_count, banned_hits, tpl_hits)"""
    errors = []
    desc = c.get("description", "")
    ass = c.get("assessment_prompt", "")

    desc_len = len(desc)
    if not (60 <= desc_len <= 100):
        errors.append(f"desc_len={desc_len} not in [60,100]")

    ass_len = len(ass)
    if not (150 <= ass_len <= 220):
        errors.append(f"ass_len={ass_len} not in [150,220]")

    name_count = ass.count("{{name}}")
    if name_count != 3:
        errors.append(f"name_count={name_count} != 3")

    # 数学 PoC 文件用真实换行, 不用 \n 转义 — 与 PoC 对齐
    newline_count = ass.count("\n")
    if newline_count < 2:
        errors.append(f"\\n count={newline_count} < 2")

    banned_hits = []
    for w in BANNED:
        if w in desc or w in ass:
            banned_hits.append(w)
    if banned_hits:
        errors.append(f"banned hits in desc/ass: {banned_hits}")

    tpl_hits = []
    for pat in TPL_PATTERNS:
        if re.search(pat, ass):
            tpl_hits.append(pat)
    if tpl_hits:
        errors.append(f"template hits in ass: {tpl_hits}")

    return errors, desc_len, ass_len, name_count, newline_count, len(banned_hits), len(tpl_hits)


def main():
    with open(IN) as f:
        concepts = json.load(f)
    with open(DRAFT) as f:
        drafts = json.load(f)

    draft_map = {d["id"]: d for d in drafts}
    print(f"Input: {len(concepts)} concepts")
    print(f"Drafts: {len(drafts)}")

    # Sanity: every input id must have a draft
    missing = [c["id"] for c in concepts if c["id"] not in draft_map]
    if missing:
        print(f"!! Missing drafts for {len(missing)} concepts: {missing[:5]}...")
        sys.exit(1)

    out_concepts = []
    total_rewrite = 0
    fail_list = []
    for c in concepts:
        d = draft_map[c["id"]]
        merged = dict(c)  # copy original
        merged["description"] = d["description"]
        merged["assessment_prompt"] = d["assessment_prompt"]

        # 1st validation
        errors, dl, al, nc, nl, bh, th = validate_one(merged)
        if errors:
            fail_list.append((c["id"], errors))
        out_concepts.append(merged)

    # build output
    out_doc = {
        "version": "v3.3.1-biology",
        "subject": "biology",
        "conceptCount": len(out_concepts),
        "generatedAt": "2026-07-23",
        "concepts": out_concepts,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out_doc, f, ensure_ascii=False, indent=2)
    print(f"Output written: {OUT} ({len(out_concepts)} concepts)")

    # stats
    desc_lens = [len(c["description"]) for c in out_concepts]
    ass_lens = [len(c["assessment_prompt"]) for c in out_concepts]
    name_counts = [c["assessment_prompt"].count("{{name}}") for c in out_concepts]
    nl_counts = [c["assessment_prompt"].count("\n") for c in out_concepts]
    banned_total = 0
    tpl_total = 0
    for c in out_concepts:
        for w in BANNED:
            if w in c["description"] or w in c["assessment_prompt"]:
                banned_total += 1
        for pat in TPL_PATTERNS:
            if re.search(pat, c["assessment_prompt"]):
                tpl_total += 1

    print()
    print("=" * 70)
    print("POST-VALIDATION REPORT")
    print("=" * 70)
    print(f"成功: {len(out_concepts) - len(fail_list)} / {len(out_concepts)}")
    print(f"失败: {len(fail_list)}")
    if fail_list:
        for fid, errs in fail_list:
            print(f"  ✗ {fid}: {errs}")
    print()
    print(f"description 长度: min={min(desc_lens)} max={max(desc_lens)} avg={sum(desc_lens)/len(desc_lens):.1f}")
    print(f"assessment  长度: min={min(ass_lens)} max={max(ass_lens)} avg={sum(ass_lens)/len(ass_lens):.1f}")
    print(f"{{name}} 数量: min={min(name_counts)} max={max(name_counts)} avg={sum(name_counts)/len(name_counts):.2f}")
    print(f"换行数量:    min={min(nl_counts)} max={max(nl_counts)} avg={sum(nl_counts)/len(nl_counts):.2f}")
    print(f"禁词命中: {banned_total}  (应 = 0)")
    print(f"模板句命中: {tpl_total}  (应 = 0)")
    print()
    if not fail_list and banned_total == 0 and tpl_total == 0:
        print("✅ ALL PASS")
    else:
        print("❌ FAILURES PRESENT")
        sys.exit(1)


if __name__ == "__main__":
    main()
