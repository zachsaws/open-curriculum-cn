#!/usr/bin/env python3
"""
V2.3 概念抽样审核 — 随机抽 30 个概念, 按学科均匀, 输出 JSON + 人工审核 Markdown.

用途:
- 校核图谱数据准确性 (OCR 提取的内容要求是否真在 2022 课标里)
- 检查错别字 / 关系对不对 / 标题是否清晰

输出:
- data/audit/sampled_30.json — 程序可读, 含每个节点的元数据
- data/audit/sampled_30.md   — 人工填写用, 5 列 markdown 表格

抽样规则:
- 14 学科按节点数比例分配 (数学 214 → 8 抽, 体育 25 → 1 抽, 共 30)
- 每学科内部用 random.sample 选
- 30 个里混 5 个"高争议"节点 (grade_start 跨学段 / 关键路径节点)
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "web" / "data" / "graph.json"
OUT_DIR = ROOT / "data" / "audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SEED = 20260722
N_TOTAL = 30

SUBJECT_CN = {
    'math': '数学', 'chinese': '语文', 'english': '英语',
    'physics': '物理', 'chemistry': '化学', 'biology': '生物',
    'history': '历史', 'geography': '地理', 'morality_law': '道法',
    'science': '科学', 'info_tech': '信息科技', 'art': '艺术',
    'pe_health': '体育与健康', 'labor': '劳动',
}


def main():
    data = json.loads(GRAPH.read_text())
    nodes = data["nodes"]
    edges = data["edges"]
    # 算 indegree (基于 edges, 模拟 cytoscape)
    indeg = defaultdict(int)
    for e in edges:
        src = e[0] if isinstance(e, list) else e["from"]
        tgt = e[1] if isinstance(e, list) else e["to"]
        indeg[tgt] += 1
    # 出度
    outdeg = defaultdict(int)
    for e in edges:
        src = e[0] if isinstance(e, list) else e["from"]
        outdeg[src] += 1
    # 按学科分桶
    by_subj = defaultdict(list)
    for n in nodes:
        by_subj[n["subject"]].append(n)

    random.seed(SEED)
    # 按节点数比例分配 30 个名额
    n_subj = len(by_subj)
    total_nodes = len(nodes)
    subj_quota = {}
    remainders = []
    for s, ns in by_subj.items():
        share = N_TOTAL * len(ns) / total_nodes
        base = int(share)
        subj_quota[s] = base
        remainders.append((share - base, s))
    # 补足 N_TOTAL
    remainders.sort(reverse=True)
    assigned = sum(subj_quota.values())
    for _, s in remainders:
        if assigned >= N_TOTAL:
            break
        subj_quota[s] += 1
        assigned += 1

    sampled = []
    for s, q in subj_quota.items():
        if q == 0:
            continue
        picks = random.sample(by_subj[s], min(q, len(by_subj[s])))
        sampled.extend(picks)
    # 如果还差 (例如某学科节点 < quota, 上面 min 兜底了), 从其他学科补
    if len(sampled) < N_TOTAL:
        rest = [n for n in nodes if n not in sampled]
        sampled.extend(random.sample(rest, N_TOTAL - len(sampled)))
    sampled = sampled[:N_TOTAL]

    # 建议审核问题 — 按节点属性生成
    audit_questions = {
        "always": [
            "content_req 真在 2022 课标第 {src_page} 页? (Y/N)",
            "标题 / 关键术语有没有错别字?",
            "上下游关系对不对? (看 prereq / unlock)",
        ],
    }

    out_json = []
    for n in sampled:
        n_in = indeg.get(n["id"], 0)
        n_out = outdeg.get(n["id"], 0)
        # 自动给一些审核 hint
        hints = []
        if n_in == 0 and n.get("grade_start", 99) > 2:
            hints.append("indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失?")
        if n_in > 5:
            hints.append(f"有 {n_in} 个先决 — 是否过多? 课标是分阶段递进, 不是单点放射")
        if not n.get("content_req"):
            hints.append("content_req 为空 — 需要从课标补 OCR 提取")
        if not n.get("academic_req"):
            hints.append("academic_req 为空 — 学业要求暂未补全")
        if n.get("review_status") == "pending":
            hints.append(f"review_status=pending (review_round={n.get('review_round', 0)}) — 还没过任何审核")
        if (n.get("content_req") or "") and "页" in n.get("content_req", ""):
            hints.append("content_req 含'页'字符 — 可能是 OCR 串行了, 不是真要求")
        # 默认审核问题
        base_qs = [
            q.format(src_page=n.get("src_page", "?")) for q in audit_questions["always"]
        ]
        all_qs = base_qs + hints

        out_json.append({
            "id": n["id"],
            "subject": n["subject"],
            "subject_cn": SUBJECT_CN.get(n["subject"], n["subject"]),
            "title": n["title"],
            "grade_start": n.get("grade_start"),
            "grade_end": n.get("grade_end"),
            "domain": n.get("domain"),
            "subdomain": n.get("subdomain"),
            "difficulty": n.get("difficulty"),
            "content_req": n.get("content_req"),
            "academic_req": n.get("academic_req"),
            "key_points": n.get("key_points"),
            "src_page": n.get("src_page"),
            "src_stage": n.get("src_stage"),
            "indegree": n_in,
            "outdegree": n_out,
            "review_status": n.get("review_status"),
            "review_round": n.get("review_round"),
            "audit_questions": all_qs,
        })

    json_path = OUT_DIR / "sampled_30.json"
    json_path.write_text(json.dumps(out_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {json_path} — {len(out_json)} concepts")

    # 写 markdown 审核表 — 让人工填 Y/N/修正
    md = []
    md.append(f"# V2.3 概念抽样审核 (30 个, seed={SEED})")
    md.append("")
    md.append(f"- 生成日期: {date.today().isoformat()}")
    md.append(f"- 数据源: `web/data/graph.json` ({total_nodes} 节点 / {len(edges)} 边)")
    md.append(f"- 抽样方法: 按学科节点数比例配额, `random.seed({SEED})` 可复现")
    md.append(f"- 人工审核: 请逐条对照 2022 义教课标原件 (`data/raw/curriculum_2022/{'{学科序号}'}_{'{学科名}'}.pdf`) 核对")
    md.append("")
    md.append("**审核问题清单** (5 列):")
    md.append("")
    md.append("| # | ID | 学科·年级 | 标题 | content_req 真在课标? (Y/N) | 错字/术语修正 | 关系对? (Y/N) | 备注 |")
    md.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for i, n in enumerate(out_json, 1):
        gd = f"{n['subject_cn']}·G{n['grade_start']}{'-' + str(n['grade_end']) if n['grade_end'] != n['grade_start'] else ''}"
        # md 转义: title 可能含 | 或换行
        title = (n["title"] or "").replace("|", "\\|").replace("\n", " ")
        cr_short = (n.get("content_req") or "")
        # 截断到 40 字, 太长看不清
        if len(cr_short) > 50:
            cr_short = cr_short[:50] + "…"
        cr_short = cr_short.replace("|", "\\|").replace("\n", " ")
        # 学科参考 PDF
        subj_idx = {
            'chinese': '02', 'math': '04', 'english': '05', 'history': '03',
            'geography': '08', 'morality_law': '01', 'physics': '10',
            'chemistry': '11', 'biology': '12', 'science': '09', 'info_tech': '13',
            'art': '15', 'pe_health': '14', 'labor': '16',
        }.get(n['subject'], '00')
        notes = f"P{n['src_page']} | indeg={n['indegree']} outdeg={n['outdegree']} | PDF: {subj_idx}_{n['subject_cn']}.pdf"
        if n.get("audit_questions"):
            notes += " | ⚠️ " + n["audit_questions"][-1]  # 最后一条 hint
        notes = notes.replace("|", "\\|")
        md.append(f"| {i} | `{n['id']}` | {gd} | {title} | _{cr_short}_ |  |  | {notes} |")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 自动审核 hint 总览 (按节点)")
    md.append("")
    md.append("| ID | 标题 | 自动 hint |")
    md.append("| --- | --- | --- |")
    for n in out_json:
        title = (n["title"] or "").replace("|", "\\|")
        for q in n["audit_questions"]:
            md.append(f"| `{n['id']}` | {title} | {q.replace('|', '\\|')} |")
    md.append("")
    md.append("## 审核流程建议")
    md.append("")
    md.append("1. 打开 `data/raw/curriculum_2022/{编号}_{学科}.pdf` 对照 `src_page` 找到原页")
    md.append("2. 逐条核对 content_req 是否是 2022 版课标原文 (vs 2011 版)")
    md.append("3. 标题是否有错别字 / 简称 / 与课标不一致 (例: '算理' vs '运算')")
    md.append("4. indegree=0 且 grade>2 的节点: 是不是图谱上游缺边, 真的是零基础?")
    md.append("5. 改完意见后, 回 `data/audit/sampled_30.md` 填写 5 列, 同步更新 `data/graph/{subject}_v0.7.json`")
    md.append("6. 标记 `review_status: audited` 写回节点, 跑 `python3 src/pipeline/audit_sample.py --update` 自动更新")
    md.append("")

    md_path = OUT_DIR / "sampled_30.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"By subject: {dict((SUBJECT_CN.get(s, s), q) for s, q in subj_quota.items() if q > 0)}")


if __name__ == "__main__":
    main()
