"""
V3.2 P0: 把 14 学科的课标框架结构化为独立 curriculum-standards.json

Marble 格式: { slug, country, name, version, sourceUrl, textIncluded, license, topicCount, topics: [{key, code, data}] }
V3.1: 把每个节点 src_page 字段重新聚类为标准格式
"""
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent.parent
IN = ROOT / "data" / "graph" / "all_v3.2.json"
OUT = ROOT / "data" / "graph" / "curriculum-standards.json"

# 教育部 2022 义教课标 PDF 来源 (人教社官方)
CURRICULA = [
    {
        "slug": "cn-compulsory-2022",
        "country": "CN",
        "name": "义务教育课程方案和课程标准 (2022 年版)",
        "version": "2022",
        "sourceUrl": "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html",
        "textIncluded": True,
        "license": "中华人民共和国教育部 2022 义教课程标准 — 公开出版物",
        "publisher": "人民教育出版社",
    },
]

SUBJ_META = {
    "math": ("数学", "Mathematics", "001"),
    "chinese": ("语文", "Chinese", "002"),
    "english": ("英语", "English", "003"),
    "physics": ("物理", "Physics", "004"),
    "chemistry": ("化学", "Chemistry", "005"),
    "biology": ("生物", "Biology", "006"),
    "history": ("历史", "History", "007"),
    "geography": ("地理", "Geography", "008"),
    "morality_law": ("道德与法治", "Morality & Law", "009"),
    "science": ("科学", "Science", "010"),
    "info_tech": ("信息科技", "Info Tech", "011"),
    "art": ("艺术", "Arts", "012"),
    "pe_health": ("体育与健康", "PE & Health", "013"),
    "labor": ("劳动", "Labor", "014"),
}

STAGE_CODE = {1: "KS1", 2: "KS1", 3: "KS2", 4: "KS2", 5: "KS3", 6: "KS3", 7: "KS4", 8: "KS4", 9: "KS4"}

def main():
    print(f"读 {IN}")
    with open(IN) as f:
        d = json.load(f)
    nodes = d["nodes"]

    # 按 subject 分组
    by_subj = defaultdict(list)
    for n in nodes:
        by_subj[n["subject"]].append(n)

    # 每个 subject 写一个 curriculum
    curricula_out = []
    note = ("中国 2022 义教课标 — 14 学科 1906 概念, 全部 textIncluded。\n"
            "每个 topic.code 用 {SUBJ_CODE}-KS{n}-D{domain_idx} 格式, 例如 M-KS1-NS-01。\n"
            "topic.data 包含 title/description/subject/domain/grade_start 等课标上下文。")

    codes_only = []
    for slug, country, name, version, sourceUrl, textIncluded, license, publisher in [
        (c["slug"], c["country"], c["name"], c["version"], c["sourceUrl"], c["textIncluded"], c["license"], c["publisher"])
        for c in CURRICULA
    ]:
        topics = []
        for subj, ns in by_subj.items():
            subj_zh, subj_en, subj_code = SUBJ_META.get(subj, (subj, subj, "X"))
            # 按 (stage, domain) 排序
            sorted_n = sorted(ns, key=lambda n: (n.get("grade_start", 1), n.get("domain", ""), n["id"]))
            for n in sorted_n:
                g = n.get("grade_start", 1)
                ks = STAGE_CODE.get(g, "KS1")
                dom = n.get("domain", "其他")
                # V3.2.2: 用 (subject_code-stage-id) 作 key, 跟 all_v3.2.json 的节点 id 对齐
                # 旧 key 形如 cn-compulsory-2022:001-KS1-TUXING-01, 502 个重复
                # 新 key 形如 cn-compulsory-2022:math-G1-M_G1_NS_01, unique by id
                nid = n["id"]
                topic_code = f"{subj_code}-{ks}-{nid.split('_')[1]}-{nid}"
                topics.append({
                    "key": f"{slug}:{topic_code}",
                    "code": topic_code,
                    "data": {
                        "id": nid,  # V3.2.2: 跨文件引用 id
                        "title": n.get("title", ""),
                        "description": n.get("content_req", "")[:200],
                        "subject": subj_zh,
                        "domain": dom,
                        "grade_start": n.get("grade_start", 1),
                        "grade_end": n.get("grade_end", 9),
                        "difficulty": n.get("difficulty", 1),
                        "bloom": n.get("bloom", ""),
                        "src_page": n.get("src_page", ""),
                        "key_points": n.get("key_points", [])[:3],
                    },
                })
        curricula_out.append({
            "slug": slug,
            "country": country,
            "name": name,
            "version": version,
            "sourceUrl": sourceUrl,
            "textIncluded": textIncluded,
            "license": license,
            "publisher": publisher,
            "topicCount": len(topics),
            "topics": topics,
        })

    out = {
        "note": note,
        "codesOnlySources": codes_only,
        "curriculumCount": len(curricula_out),
        "curricula": curricula_out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=None, separators=(',', ':'))
    print(f"写入 {OUT}")
    print(f"  curricula: {len(curricula_out)}")
    for c in curricula_out:
        print(f"  {c['slug']}: {c['topicCount']} topics")

if __name__ == "__main__":
    main()
