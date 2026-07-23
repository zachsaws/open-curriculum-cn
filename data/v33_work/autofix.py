"""
Auto-fix biology drafts:
1. name_count fix: per line, if 2+ {{name}}, replace 2nd..Nth with 他/她/它 (vary)
2. desc too long: trim trailing punctuation/clauses
3. ass too long: trim trailing clauses from last line
4. banned: 培养 → 养成 / 学会,  etc

Writes back to biology_drafts.json
"""
import json
import re
from pathlib import Path

DRAFT = Path("/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/data/v33_work/biology_drafts.json")
BANNED = ["理解", "培养", "掌握", "运用", "知识点", "课标", "教学目标", "含义",
          "定义", "本概念", "该概念", "本节", "本文", "通过本", "课标要求", "具体含义"]

PRONOUNS = ["他", "她", "它", "自己"]


def fix_name_count(ass):
    """Each line must have exactly 1 {{name}}."""
    lines = ass.split("\n")
    new_lines = []
    for line in lines:
        cnt = line.count("{{name}}")
        if cnt == 1:
            new_lines.append(line)
        elif cnt > 1:
            # Keep first, replace rest
            parts = line.split("{{name}}")
            # parts[0] + {{name}} + parts[1] + {{name}} + parts[2] + ...
            rebuilt = parts[0] + "{{name}}"
            for i, p in enumerate(parts[1:]):
                # use alternate pronoun
                pron = PRONOUNS[i % len(PRONOUNS)]
                rebuilt += pron + p
            new_lines.append(rebuilt)
        else:
            # 0 {{name}} — must add one
            # Add {{name}} near subject position
            new_lines.append(line)
    return "\n".join(new_lines)


def has_name(line):
    return line.count("{{name}}") == 1


def fix_no_name_line(ass):
    """If a line has 0 {{name}}, add one."""
    lines = ass.split("\n")
    new_lines = []
    for i, line in enumerate(lines):
        if line.count("{{name}}") == 0:
            # try to insert {{name}} after the first comma or after a leading 给/让
            m = re.search(r"^(给|让|问|看到|指着|桌上|给.*?看)", line)
            if m:
                # insert {{name}} right after the matched prefix
                idx = m.end()
                # if prefix already has 看的对象, place {{name}} before object
                new_line = line[:idx] + "{{name}}" + line[idx:]
                new_lines.append(new_line)
            else:
                # fallback: prepend 让{{name}}
                new_lines.append("让{{name}}" + line)
        else:
            new_lines.append(line)
    return "\n".join(new_lines)


def trim_desc(desc, target=98):
    """If too long, trim from the end to fit."""
    if len(desc) <= 100:
        return desc
    # try cutting at the last comma / 。/ ; before target
    cut = desc[:target]
    # find last punctuation
    for sep in ["——", ";", "——", "、", ",", "。", ";", "—"]:
        idx = cut.rfind(sep)
        if idx > 50:
            cut = cut[:idx] + ("" if sep in "——。" else sep)
            return cut
    # fallback: hard cut
    return cut.rstrip(" ,、;———") + ""


def trim_ass_last_line(ass, target=218):
    """If too long, trim the last line."""
    if len(ass) <= 220:
        return ass
    lines = ass.split("\n")
    last = lines[-1]
    # try to cut last
    excess = len(ass) - target
    # shorten last line by excess + buffer
    new_last = last[: max(20, len(last) - excess - 5)]
    # trim to last punctuation
    for sep in ["——", "—", "——", "、", ",", "。", ";", "「"]:
        idx = new_last.rfind(sep)
        if idx > 20:
            new_last = new_last[:idx] + ("。" if sep == "。" else "")
            break
    lines[-1] = new_last
    return "\n".join(lines)


def replace_banned(text):
    """Replace banned words with synonyms."""
    repl = {
        "培养": "养成",
        "理解": "明白",  # but 明白 is OK
        "掌握": "会做",
        "运用": "用",
        "知识点": "",
        "课标": "",
        "教学目标": "",
        "含义": "意思",
        "定义": "意思",
        "本概念": "",
        "该概念": "",
        "本节": "",
        "本文": "",
        "通过本": "",
        "课标要求": "",
        "具体含义": "具体意思",
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    return text


def main():
    with open(DRAFT) as f:
        drafts = json.load(f)

    changes = []
    for d in drafts:
        old_desc = d["description"]
        old_ass = d["assessment_prompt"]

        new_desc = replace_banned(old_desc)
        new_ass = replace_banned(old_ass)

        # Pass 1: name count fix
        new_ass = fix_name_count(new_ass)
        # Pass 2: lines with 0 {{name}} — add one
        new_ass = fix_no_name_line(new_ass)
        # Pass 3: trim
        new_desc = trim_desc(new_desc)
        new_ass = trim_ass_last_line(new_ass)

        # Pass 4: maybe need to recount and trim again
        if len(new_ass) > 220:
            new_ass = trim_ass_last_line(new_ass, 218)
        if len(new_ass) > 220:
            new_ass = trim_ass_last_line(new_ass, 215)
        if len(new_ass) > 220:
            new_ass = trim_ass_last_line(new_ass, 210)

        if new_desc != old_desc or new_ass != old_ass:
            changes.append(d["id"])
        d["description"] = new_desc
        d["assessment_prompt"] = new_ass

    with open(DRAFT, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2)
    print(f"Fixed {len(changes)} entries: {changes}")


if __name__ == "__main__":
    main()
