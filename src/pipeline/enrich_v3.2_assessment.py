"""
V3.2 P0: 给每个概念加 assessment_prompt (带 {{name}} 占位)
- 1906 概念
- 模板基于 (subject, domain, title) + academic_req / key_points / content_req
"""
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent.parent
IN = ROOT / "data" / "graph" / "all_v3.2.json"
OUT = ROOT / "data" / "graph" / "all_v3.2.json"  # 原地写

SUBJ_NAME_ZH = {
    "math": "数学", "chinese": "语文", "english": "英语",
    "physics": "物理", "chemistry": "化学", "biology": "生物",
    "history": "历史", "geography": "地理", "morality_law": "道德与法治",
    "science": "科学", "info_tech": "信息科技", "art": "艺术",
    "pe_health": "体育与健康", "labor": "劳动",
}

# 通用模板: 基于 subject + domain
def gen_assessment(node):
    """生成 assessment_prompt 模板 (带 {{name}})"""
    s = node["subject"]
    subj_zh = SUBJ_NAME_ZH.get(s, s)
    title = node["title"]
    domain = node.get("domain", "")
    g = node.get("grade_start", 1)
    bloom = node.get("bloom", "")
    academic_req = node.get("academic_req", "")
    key_points = node.get("key_points", [])
    # 取 key_points 第一条
    kp = ""
    if isinstance(key_points, list) and key_points:
        kp = str(key_points[0])[:50]
    elif isinstance(key_points, str):
        kp = key_points[:50]
    # 取 academic_req 关键词
    ar = academic_req[:60] if academic_req else ""

    # 场景模板
    templates = [
        # 1. 老师评语 (默认)
        f"在{subj_zh}课上，{{{{name}}}}能否理解「{title}」这一概念，并在{g}年级的练习中独立完成相关题目？",
    ]
    # 2. 行为观察 (基于 bloom + key_points)
    if "理解" in bloom or "认识" in bloom or "了解" in bloom:
        templates.append(f"{{{{name}}}}能不能用自己的话解释「{title}」的含义，并举出一个生活中的例子？")
    if "应用" in bloom or "运用" in bloom or "解决" in bloom:
        templates.append(f"在遇到新问题时，{{{{name}}}}能否运用「{title}」的知识独立解决？")
    if "分析" in bloom or "比较" in bloom or "区分" in bloom:
        templates.append(f"{{{{name}}}}能否比较「{title}」与相关概念的区别，并说出判断依据？")
    if "评价" in bloom or "判断" in bloom or "选择" in bloom:
        templates.append(f"面对不同方案，{{{{name}}}}能否用「{title}」的标准做出合理判断？")
    if "创造" in bloom or "设计" in bloom or "创作" in bloom:
        templates.append(f"{{{{name}}}}能否独立设计一个作品/方案/实验，融入「{title}」的核心要素？")
    # 3. 学科特定模板
    if s == "math":
        templates.append(f"{{{{name}}}}能否独立解答涉及「{title}」的题目，并清晰写出解题步骤？")
    if s == "chinese":
        templates.append(f"{{{{name}}}}能否在阅读/写作中正确使用「{title}」相关知识（如修辞/字词/语法）？")
    if s == "english":
        templates.append(f"在英语对话/阅读中，{{{{name}}}}能否熟练运用「{title}」相关词汇/语法？")
    if s in ("physics", "chemistry", "biology", "science"):
        templates.append(f"{{{{name}}}}能否在实验/探究中正确应用「{title}」，并用科学语言解释现象？")
    if s == "pe_health":
        templates.append(f"{{{{name}}}}能否在体育活动中正确展示「{title}」相关动作/技能？")
    if s == "art":
        templates.append(f"{{{{name}}}}能否在艺术创作中融入「{title}」的元素（如节奏/色彩/造型）？")
    if s == "info_tech":
        templates.append(f"{{{{name}}}}能否独立使用「{title}」相关工具/编程完成一个实际任务？")
    if s == "history":
        templates.append(f"{{{{name}}}}能否用自己的话叙述「{title}」相关的历史事件，并说明其影响？")
    if s == "geography":
        templates.append(f"{{{{name}}}}能否在地图/图表中识别「{title}」相关信息，并解释成因？")
    if s == "morality_law":
        templates.append(f"在生活情境中，{{{{name}}}}能否依据「{title}」相关规范/法律做出正确判断和行为？")
    if s == "labor":
        templates.append(f"{{{{name}}}}能否独立完成「{title}」相关的劳动任务（如整理/制作/服务）？")

    # 默认 fallback
    if len(templates) == 1:
        templates.append(f"{{{{name}}}}能否在学习和生活中展示对「{title}」的理解和应用？")

    # 拼成完整 prompt: 1 个核心 + 1-2 个细节
    return "\n".join(templates[:3])

def main():
    print(f"读 {IN}")
    with open(IN) as f:
        d = json.load(f)
    nodes = d["nodes"]

    filled = 0
    skipped = 0
    for n in nodes:
        if n.get("assessment_prompt"):
            continue
        try:
            n["assessment_prompt"] = gen_assessment(n)
            filled += 1
        except Exception as e:
            skipped += 1
            print(f"  err {n['id']}: {e}")

    print(f"填充 assessment_prompt: {filled}/{len(nodes)}")
    with_p = sum(1 for n in nodes if n.get("assessment_prompt"))
    print(f"总覆盖: {with_p}/{len(nodes)} = {with_p*100/len(nodes):.1f}%")

    # 写回
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=None, separators=(',', ':'))
    print(f"写回 {OUT}")

    # 抽样
    import random
    sample = random.sample([n for n in nodes if n.get("assessment_prompt")], 3)
    for n in sample:
        print(f"\\n--- {n['id']} ({n['subject']} - {n['title']}) ---")
        print(n['assessment_prompt'])

if __name__ == "__main__":
    main()
