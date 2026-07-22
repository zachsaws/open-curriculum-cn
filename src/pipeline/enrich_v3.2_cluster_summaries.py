"""
V3.2 P0: 给每个 (subject, stage, domain) 聚类生成人话 summary
- 183 个 cluster (Marble 同级别)
- 模板 + 关键概念
"""
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).parent.parent.parent
IN = ROOT / "data" / "graph" / "all_v3.2.json"
OUT = ROOT / "data" / "graph" / "clusters.json"

SUBJ_ZH = {
    "math": ("数学", "Math"),
    "chinese": ("语文", "Chinese"),
    "english": ("英语", "English"),
    "physics": ("物理", "Physics"),
    "chemistry": ("化学", "Chemistry"),
    "biology": ("生物", "Biology"),
    "history": ("历史", "History"),
    "geography": ("地理", "Geography"),
    "morality_law": ("道德与法治", "Morality & Law"),
    "science": ("科学", "Science"),
    "info_tech": ("信息科技", "Info Tech"),
    "art": ("艺术", "Arts"),
    "pe_health": ("体育与健康", "PE & Health"),
    "labor": ("劳动", "Labor"),
}

STAGE_ZH = {
    (1, 2): ("1-2 年级", "early primary"),
    (3, 4): ("3-4 年级", "mid primary"),
    (5, 6): ("5-6 年级", "late primary"),
    (7, 9): ("7-9 年级", "junior high"),
}

# 领域特征描述模板 (按学科 + 领域预写)
DOMAIN_DESC = {
    ("math", "数与运算"): "孩子从认数、读数、写数开始，逐步掌握整数/分数/小数/百分数的运算，理解运算定律和简便方法。",
    ("math", "数量关系"): "孩子学习用等式、不等式、函数表达数量关系，能用方程和图像解决实际问题。",
    ("math", "图形与几何"): "孩子认识基本平面图形和立体图形，掌握周长、面积、体积的计算，理解图形的变换。",
    ("math", "统计与概率"): "孩子学会收集、整理、描述数据，能读懂图表，理解平均数、概率等基本统计概念。",
    ("math", "综合与实践"): "孩子在跨学科主题活动中综合运用数学知识解决真实问题，培养建模和探究能力。",
    ("chinese", "识字与写字"): "孩子学习汉语拼音、笔画笔顺，识字量逐步达到 1600-3000 字，能规范书写。",
    ("chinese", "阅读与鉴赏"): "孩子学习朗读、默读、浏览，能理解课文内容、体会作者情感，掌握阅读策略。",
    ("chinese", "表达与交流"): "孩子学会口头表达和书面写作，能围绕主题清楚表达，按要求写各类文章。",
    ("chinese", "梳理与探究"): "孩子学习整理语文知识，主动探究语言文字规律，提升语文综合素养。",
    ("english", "听与说"): "孩子学习听懂简单的英语对话，能用英语就熟悉话题进行交流。",
    ("english", "读与写"): "孩子学习阅读英语短文，能写出结构完整的短文，掌握基础语法和词汇。",
    ("english", "综合语言运用"): "孩子在项目式任务中综合运用英语，发展跨文化意识和思辨能力。",
    ("physics", "物质"): "孩子从物体的尺度、质量、密度等基本属性出发，理解物质的多样性和结构。",
    ("physics", "运动和力"): "孩子学习机械运动、力的作用、压强、浮力，理解牛顿三定律。",
    ("physics", "能量"): "孩子理解功、能、热量等概念，认识能量守恒和能量转化的普遍性。",
    ("physics", "电与磁"): "孩子学习电路、电流、电压、磁场，理解电磁相互作用。",
    ("physics", "实验与探究"): "孩子通过科学实验探究物理规律，学习控制变量、记录数据、得出结论。",
    ("chemistry", "物质的多样性"): "孩子认识物质分类、元素、化合物，理解物质的多样性及其微观本质。",
    ("chemistry", "物质的变化与反应"): "孩子学习化学反应类型、化学方程式、反应规律，理解质量守恒。",
    ("chemistry", "化学与社会"): "孩子了解化学在能源、材料、医药、环保等领域的应用与影响。",
    ("biology", "生物体结构与功能"): "孩子认识细胞、组织、器官、系统，理解生物体的结构与功能相适应。",
    ("biology", "生物多样性"): "孩子认识植物、动物、微生物的多样性，理解生物分类和进化。",
    ("biology", "生态系统"): "孩子学习生态系统的组成、食物链、能量流动，理解人与自然和谐共生。",
    ("biology", "健康与疾病"): "孩子了解人体生理结构、健康生活方式和常见疾病的预防。",
    ("biology", "生物技术"): "孩子了解现代生物技术在农业、医药、工业中的应用及其伦理。",
    ("history", "中国古代史"): "孩子了解从先秦到明清的中国古代政治、经济、文化与社会变迁。",
    ("history", "中国近代史"): "孩子学习鸦片战争以来中国人民救亡图存、走向复兴的奋斗历程。",
    ("history", "中国现代史"): "孩子了解新中国成立以来的社会主义建设与改革开放伟大成就。",
    ("history", "世界历史"): "孩子了解世界主要文明的发展、各国现代化的不同路径和全球化进程。",
    ("geography", "地球与地图"): "孩子学习地球的形状、运动、时区，理解地图三要素和读图方法。",
    ("geography", "自然地理"): "孩子了解气候、地形、水文、植被、土壤等自然要素及其相互关系。",
    ("geography", "人文地理"): "孩子学习人口、城市、产业、交通等人文地理现象，理解人地关系。",
    ("geography", "区域地理"): "孩子学习中国和世界主要区域的地理特征，理解区域差异与合作。",
    ("morality_law", "道德教育"): "孩子通过学校生活、家庭生活、社会生活情境学习道德规范和价值判断。",
    ("morality_law", "法治教育"): "孩子了解宪法、未成年人保护法、治安管理处罚法等法律基本常识。",
    ("morality_law", "心理健康"): "孩子学习认识情绪、调适心理、发展健全人格和良好人际交往。",
    ("morality_law", "国情与责任"): "孩子了解国家制度、发展成就，树立社会责任感和家国情怀。",
    ("science", "生命科学"): "孩子认识生命现象、生命结构、健康与卫生，养成科学生活习惯。",
    ("science", "物质科学"): "孩子通过观察和实验认识物质的状态、变化和性质。",
    ("science", "地球与宇宙科学"): "孩子了解地球结构、天气变化、太阳系和宇宙的基本概念。",
    ("science", "技术与工程"): "孩子通过动手实践学习简单的技术设计和工程思维。",
    ("info_tech", "信息与数据"): "孩子学习信息的获取、存储、加工和表达，理解数据的基本概念。",
    ("info_tech", "算法与编程"): "孩子学习算法的概念、流程图的绘制，能用图形化或代码编程解决问题。",
    ("info_tech", "网络与安全"): "孩子了解互联网基本原理，学习安全、文明、合乎伦理地使用网络。",
    ("info_tech", "人工智能初步"): "孩子了解人工智能的基本概念、应用场景和对社会的影响。",
    ("art", "音乐"): "孩子通过演唱、演奏、欣赏、综合性艺术表演感受音乐之美。",
    ("art", "美术"): "孩子通过绘画、雕塑、设计、工艺等体验造型之美。",
    ("art", "舞蹈"): "孩子通过舞蹈基本动作和表演，体验身体表达的艺术。",
    ("art", "戏剧与影视"): "孩子通过戏剧、影视作品欣赏和表演，理解综合艺术。",
    ("pe_health", "基本运动技能"): "孩子学习跑、跳、投、攀爬等基本动作，发展体能。",
    ("pe_health", "专项运动技能"): "孩子在球类、田径、体操、武术等专项运动中发展技能。",
    ("pe_health", "健康知识"): "孩子了解营养、疾病预防、心理健康、安全避险等知识。",
    ("pe_health", "体能与比赛"): "孩子通过体能测试和比赛发展运动能力，培养团队精神和意志品质。",
    ("labor", "日常生活劳动"): "孩子学会整理、打扫、烹饪、缝纫等日常生活劳动技能。",
    ("labor", "生产劳动"): "孩子通过种植、养殖、手工制作等体验生产劳动过程。",
    ("labor", "服务性劳动"): "孩子通过公益劳动、志愿服务等培养社会责任感和奉献精神。",
}

def stage_of(grade):
    if grade <= 2: return (1, 2)
    if grade <= 4: return (3, 4)
    if grade <= 6: return (5, 6)
    return (7, 9)

def main():
    print(f"读 {IN}")
    with open(IN) as f:
        d = json.load(f)
    nodes = d["nodes"]

    # 按 (subject, stage, domain) 聚合
    buckets = defaultdict(list)
    for n in nodes:
        s = n["subject"]
        g = n.get("grade_start", 1)
        stg = stage_of(g)
        dom = n.get("domain", "其他")
        buckets[(s, stg, dom)].append(n)

    clusters = []
    for (s, stg, dom), ns in sorted(buckets.items()):
        # 选最难的 3 个关键概念作为示例
        sorted_n = sorted(ns, key=lambda x: -x.get("difficulty", 1))
        key_concept_ids = [n["id"] for n in sorted_n[:3]]
        key_concepts = [n["title"] for n in sorted_n[:3]]
        # 模板生成
        subj_zh, _ = SUBJ_ZH.get(s, (s, s))
        stg_zh, stg_en = STAGE_ZH[stg]
        base_desc = DOMAIN_DESC.get((s, dom))
        if not base_desc:
            # fallback: 用子领域 key concepts 拼出"这个领域学啥"
            base_desc = _generic_desc(subj_zh, dom, key_concepts, ns)
        # 拼成 final summary (1-3 句)
        summary = f"{stg_zh}：{base_desc}\n本阶段共 {len(ns)} 个核心概念，重点包括「{'」「'.join(key_concepts)}」等。"
        clusters.append({
            "id": f"{s}-G{stg[0]}-{stg[1]}-{slug(dom)}",
            "subject": s,
            "subject_zh": subj_zh,
            "domain": dom,
            "stage_start": stg[0],
            "stage_end": stg[1],
            "concept_count": len(ns),
            "key_concept_ids": key_concept_ids,  # V3.2.2: 跨文件引用
            "key_concepts": key_concepts,
            "key_concepts_titles": key_concepts,  # V3.2.2: 显式命名
            "summary_zh": summary,
            "summary_en": f"Stage {stg_en}: {base_desc}",
        })

    print(f"聚类数: {len(clusters)}")

    out_data = {
        "version": "v3.2",
        "clusterCount": len(clusters),
        "clusters": clusters,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)
    print(f"写入 {OUT}")

    # 抽样 3 个
    for c in clusters[:3]:
        print(f"\\n--- {c['id']} ---")
        print(f"  {c['summary_zh'][:200]}")

def stage_zh_to_zh(stg):
    return {1:"低年级", 2:"低年级", 3:"中年级", 4:"中年级", 5:"高年级", 6:"高年级", 7:"初中", 8:"初中", 9:"初中"}[stg[0]]

def _generic_desc(subj_zh, dom, key_concepts, all_nodes):
    """fallback 模板 — 用 key_concepts 拼出"这个领域学啥"的人话"""
    # 取 key_points 平均
    kps = []
    for n in all_nodes[:5]:
        kp = n.get("key_points", [])
        if isinstance(kp, list):
            kps.extend(kp[:2])
        elif isinstance(kp, str) and kp:
            kps.append(kp[:30])
    if kps:
        # 去重
        seen = set()
        unique = []
        for kp in kps:
            if kp[:20] not in seen:
                seen.add(kp[:20])
                unique.append(kp)
        sample = unique[:3]
        return f"孩子在本阶段学习{subj_zh}「{dom}」领域，包括「{'」「'.join(key_concepts)}」等内容，核心要点涉及「{'; '.join(sample)}」等。"
    return f"孩子在本阶段学习{subj_zh}「{dom}」领域的核心概念，包括「{'」「'.join(key_concepts)}」等内容。"

def slug(s):
    return s.replace(" ", "-").replace("/", "-")[:30]

if __name__ == "__main__":
    main()
