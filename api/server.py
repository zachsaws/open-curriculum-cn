"""
B 端 REST API — 2022 新课标知识图谱

启动: uvicorn api.server:app --host 0.0.0.0 --port 8001

V0.8 P0 修复:
  Bug 1: /api/prerequisites 递归爆栈 → 改 iterative + visited
  Bug 2: 邻接表每次请求都重建 → startup 一次构建 + lru_cache
  Bug 3: get_concept 返回的边丢 type 字段 → 加 rel 字段
  Bug 4: find_path 404 时无 progress → 返回 visited_count + suggested_intermediate
"""
import json
import re
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT = Path(__file__).parent.parent
# V3.2: 优先读 all_v3.2.json, 兼容 v3.0 / v0.8 / v0.7
_DATA_CANDIDATES = ["all_v3.2.json", "all_v3.0.json", "all_v0.8.json", "all_v0.7.json"]
DATA_FILE = next(
    (ROOT / "data" / "graph" / n for n in _DATA_CANDIDATES
     if (ROOT / "data" / "graph" / n).exists()),
    ROOT / "data" / "graph" / "all_v3.2.json",
)
if "v3.2" in DATA_FILE.name:
    DATA_VERSION = "v3.2.0"
elif "v3.0" in DATA_FILE.name:
    DATA_VERSION = "v3.0.0"
elif "v0.8" in DATA_FILE.name:
    DATA_VERSION = "v0.8.0"
else:
    DATA_VERSION = "v0.7.5"

# 加载数据
def load_data():
    if not DATA_FILE.exists():
        return None
    with open(DATA_FILE) as f:
        return json.load(f)


DATA = load_data()
if DATA is None:
    raise RuntimeError(f"数据文件不存在: {DATA_FILE}, 请先跑 enrich + merge")

app = FastAPI(
    title="Open Curriculum CN API",
    description="基于 2022 义教新课标的中国 K12 知识图谱 REST API",
    version=DATA_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 邻接表 startup 一次构建 (Bug 2 修复)
# 用 lru_cache 包装, 第一次调用即构建, 后续 O(1) 命中
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_adjacency():
    """返回 (_ADJ_TO, _ADJ_FROM) 两个邻接表 dict
    _ADJ_TO[concept_id] = [from_id, ...]  (先决)
    _ADJ_FROM[concept_id] = [to_id, ...]  (后继)
    """
    adj_to = defaultdict(list)
    adj_from = defaultdict(list)
    for e in DATA["edges"]:
        rel = e.get("rel") or ("prerequisite" if e.get("type", 1) == 1 else "relates_to")
        # 硬先决/同领域跨段 用于先决链 (prerequisite + progresses_to)
        if rel in ("prerequisite", "progresses_to"):
            adj_to[e["to"]].append(e["from"])
            adj_from[e["from"]].append(e["to"])
    return adj_to, adj_from


# 启动时立即构建一次 (而不是 lazy)
_ADJ_TO, _ADJ_FROM = get_adjacency()


# ---------------------------------------------------------------------------
# Bug 1 修复: 递归爆栈 — 改 iterative BFS + iterative depth
# ---------------------------------------------------------------------------
def _bfs_prereqs(concept_id):
    """iterative BFS 找所有先决 (含 visited 防环)"""
    visited = set()
    queue = deque([concept_id])
    while queue:
        cur = queue.popleft()
        for pre in _ADJ_TO.get(cur, []):
            if pre not in visited and pre != concept_id:
                visited.add(pre)
                queue.append(pre)
    return visited


def _iterative_depth(all_prereqs):
    """iterative 计算 depth: 用 Kahn 风格自底向上拓扑"""
    # depth[n] = 0 if n 无先决, else max(depth[pre]) + 1
    depth = {}
    # 按入度分层处理
    in_deg = {nid: 0 for nid in all_prereqs}
    for nid in all_prereqs:
        for pre in _ADJ_TO.get(nid, []):
            if pre in all_prereqs:
                in_deg[nid] += 1

    queue = deque([nid for nid, d in in_deg.items() if d == 0])
    for nid in queue:
        depth[nid] = 0
    while queue:
        cur = queue.popleft()
        d = depth[cur]
        for nxt in _ADJ_FROM.get(cur, []):
            if nxt not in all_prereqs:
                continue
            if nxt not in depth:
                depth[nxt] = d + 1
            else:
                depth[nxt] = max(depth[nxt], d + 1)
            in_deg[nxt] -= 1
            if in_deg[nxt] == 0:
                queue.append(nxt)
    return depth


@app.get("/")
def root():
    return {
        "name": "Open Curriculum CN API",
        "version": DATA_VERSION,
        "data_version": DATA_VERSION,
        "data_file": DATA_FILE.name,
        "subjects": len(set(n["subject"] for n in DATA["nodes"])),
        "concepts": len(DATA["nodes"]),
        "edges": len(DATA["edges"]),
        "endpoints": [
            "/api/stats",
            "/api/subjects",
            "/api/concepts",
            "/api/concepts/{id}",
            "/api/prerequisites/{id}",
            "/api/path",
            "/api/search",
            "/api/health",
            "/rss.xml",
        ],
    }


@app.get("/api/stats")
def stats():
    by_subj = defaultdict(int)
    by_stage = defaultdict(int)
    by_rel = defaultdict(int)
    for n in DATA["nodes"]:
        by_subj[n["subject"]] += 1
        by_stage[n.get("stage", 0)] += 1
    for e in DATA["edges"]:
        by_rel[e.get("rel") or ("prerequisite" if e.get("type", 1) == 1 else "relates_to")] += 1
    return {
        "total_concepts": len(DATA["nodes"]),
        "total_edges": len(DATA["edges"]),
        "by_subject": dict(by_subj),
        "by_stage": {f"G{(s-1)*2+1}-{(s-1)*2+2 if s<4 else 9}": v for s, v in sorted(by_stage.items()) if s > 0},
        "by_rel": dict(by_rel),
    }


@app.get("/api/health")
def health():
    """V3.2 健康检查: 字段填充率 + DAG 状态"""
    nodes = DATA["nodes"]
    edges = DATA["edges"]
    # 字段填充率
    field_stats = {
        "content_req_完整": sum(1 for n in nodes if n.get("content_req") and len(n.get("content_req", "")) > 30),
        "academic_req_填充": sum(1 for n in nodes if n.get("academic_req")),
        "bloom_覆盖": sum(1 for n in nodes if n.get("bloom")),
        "src_page_真实": sum(1 for n in nodes if n.get("src_page") and n["src_page"] != "N/A"),
        "key_points_填充": sum(1 for n in nodes if n.get("key_points") and len(n.get("key_points", [])) > 0),
        "edge_reason_填充": sum(1 for e in edges if e.get("reason")),
        "assessment_prompt_填充": sum(1 for n in nodes if n.get("assessment_prompt")),
        "centrality_填充": sum(1 for n in nodes if n.get("centrality") is not None),
        "type_填充": sum(1 for n in nodes if n.get("type")),
        "age_填充": sum(1 for n in nodes if n.get("age_range_start")),
    }
    # DAG 验证 (prerequisite 边)
    pre = [e for e in edges if e.get("rel") == "prerequisite"]
    in_deg = {n["id"]: 0 for n in nodes}
    adj = {n["id"]: [] for n in nodes}
    for e in pre:
        adj[e["from"]].append(e["to"])
        in_deg[e["to"]] = in_deg.get(e["to"], 0) + 1
    from collections import deque
    q = deque([n for n, d in in_deg.items() if d == 0])
    visited = 0
    while q:
        u = q.popleft()
        visited += 1
        for v in adj[u]:
            in_deg[v] -= 1
            if in_deg[v] == 0:
                q.append(v)
    is_dag = visited == len(nodes)
    return {
        "status": "ok" if is_dag else "degraded",
        "version": DATA_VERSION,
        "data_file": DATA_FILE.name,
        "totals": {
            "concepts": len(nodes),
            "edges": len(edges),
            "prerequisite_edges": len(pre),
        },
        "field_coverage": {k: {"count": v, "pct": round(v * 100 / len(nodes) if k != "edge_reason_填充" else v * 100 / len(edges), 1)} for k, v in field_stats.items()},
        "dag": {
            "is_dag": is_dag,
            "scope": "prerequisite edges only",
            "visited": visited,
            "total": len(nodes),
        },
    }


@app.get("/api/subjects")
def subjects():
    by_subj = defaultdict(lambda: {"count": 0, "concepts": []})
    for n in DATA["nodes"]:
        by_subj[n["subject"]]["count"] += 1
    # V2.1 统一学科名 — 与 web/i18n.js SUBJECT_CN_I18N 同步
    # 单一真源: web/i18n.js (前端), API 端保持简中名一致
    SUBJECT_CN = {
        "math": "数学", "chinese": "语文", "english": "英语", "physics": "物理",
        "chemistry": "化学", "biology": "生物", "history": "历史", "geography": "地理",
        "morality_law": "道德与法治", "science": "科学", "info_tech": "信息科技",
        "art": "艺术", "pe_health": "体育与健康", "labor": "劳动",
        "integrated": "综合实践",
    }
    SUBJECT_TW = {
        "math": "數學", "chinese": "語文", "english": "英語", "physics": "物理",
        "chemistry": "化學", "biology": "生物", "history": "歷史", "geography": "地理",
        "morality_law": "道德與法治", "science": "科學", "info_tech": "資訊科技",
        "art": "藝術", "pe_health": "體育與健康", "labor": "勞動",
        "integrated": "綜合實踐",
    }
    SUBJECT_EN = {
        "math": "Math", "chinese": "Chinese", "english": "English", "physics": "Physics",
        "chemistry": "Chemistry", "biology": "Biology", "history": "History",
        "geography": "Geography", "morality_law": "Civics", "science": "Science",
        "info_tech": "Info Tech", "art": "Arts", "pe_health": "PE & Health",
        "labor": "Labor", "integrated": "Integrated Practice",
    }
    SUBJECT_BY_LANG = {"zh-CN": SUBJECT_CN, "zh-TW": SUBJECT_TW, "en": SUBJECT_EN}

    def _names(s: str, lang: str):
        d = SUBJECT_BY_LANG.get(lang, SUBJECT_CN)
        return {
            "name_cn": SUBJECT_CN.get(s, s),
            "name_tw": SUBJECT_TW.get(s, s),
            "name_en": SUBJECT_EN.get(s, s),
            "name": d.get(s, s),
        }

    return {
        s: {**_names(s, lang="zh-CN"), "concept_count": d["count"]}
        for s, d in sorted(by_subj.items())
    }


@app.get("/api/concepts")
def list_concepts(
    subject: Optional[str] = Query(None, description="学科 code"),
    stage: Optional[int] = Query(None, ge=1, le=5, description="学段 1-5 (V0.6 数据中 G7-9=5, 未来 fix 后是 4)"),
    domain: Optional[str] = Query(None, description="领域"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
):
    """列所有概念"""
    results = DATA["nodes"]
    if subject:
        results = [n for n in results if n["subject"] == subject]
    if stage:
        results = [n for n in results if n.get("stage") == stage]
    if domain:
        results = [n for n in results if n.get("domain") == domain]
    total = len(results)
    results = results[offset:offset + limit]
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "concepts": results,
    }


@app.get("/api/concepts/{concept_id}")
def get_concept(concept_id: str):
    """单个概念详情 (V0.8 Bug 3 修复: 边的 rel 字段不再丢失)"""
    n = next((n for n in DATA["nodes"] if n["id"] == concept_id), None)
    if not n:
        raise HTTPException(404, f"概念不存在: {concept_id}")
    # 包含先决/后继 (保留 rel/weight/rationale 等元数据)
    def _edge_full(e):
        out = {"from": e["from"], "to": e["to"]}
        for k in ("rel", "weight", "rationale", "source", "type"):
            if k in e:
                out[k] = e[k]
        return out

    pre = [_edge_full(e) for e in DATA["edges"] if e["to"] == concept_id]
    post = [_edge_full(e) for e in DATA["edges"] if e["from"] == concept_id]
    return {
        **n,
        "prerequisites": pre,
        "unlocks": post,
        "prereq_count": len(pre),
        "unlock_count": len(post),
    }


@app.get("/api/prerequisites/{concept_id}")
def prerequisites(concept_id: str):
    """概念的所有先决 (V0.8 Bug 1 修复: iterative BFS + iterative depth, 不会爆栈)"""
    # 验证节点存在
    if concept_id not in {n["id"] for n in DATA["nodes"]}:
        raise HTTPException(404, f"概念不存在: {concept_id}")

    # 用 startup 预构建的邻接表 (Bug 2 修复)
    # 1) BFS 找所有祖先
    all_prereqs = _bfs_prereqs(concept_id)

    # 2) iterative depth (无递归, 无爆栈)
    depth = _iterative_depth(all_prereqs)

    concepts = [n for n in DATA["nodes"] if n["id"] in all_prereqs]
    concepts.sort(key=lambda n: (depth.get(n["id"], 0), n["id"]))
    return {
        "concept_id": concept_id,
        "total_prereqs": len(all_prereqs),
        "max_depth": max(depth.values()) if depth else 0,
        "concepts": [{"id": n["id"], "title": n["title"], "depth": depth.get(n["id"], 0)} for n in concepts],
    }


@app.get("/api/path")
def find_path(from_id: str, to_id: str):
    """找 from → to 学习路径 (BFS, V0.8 Bug 4 修复: 404 时返回 progress)"""
    if from_id == to_id:
        return {"path": [from_id], "length": 0}

    # 节点存在性检查
    node_ids = {n["id"] for n in DATA["nodes"]}
    if from_id not in node_ids:
        raise HTTPException(404, f"起点不存在: {from_id}")
    if to_id not in node_ids:
        raise HTTPException(404, f"终点不存在: {to_id}")

    # 用 startup 预构建的 _ADJ_FROM (Bug 2 修复)
    # BFS
    queue = deque([(from_id, [from_id])])
    visited = {from_id}
    while queue:
        cur, path = queue.popleft()
        if cur == to_id:
            concepts = [next((n for n in DATA["nodes"] if n["id"] == nid), None) for nid in path]
            return {
                "from": from_id,
                "to": to_id,
                "path": path,
                "concepts": [{"id": c["id"], "title": c["title"]} for c in concepts if c],
                "length": len(path) - 1,
            }
        for nxt in _ADJ_FROM.get(cur, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, path + [nxt]))

    # 404 兜底 (Bug 4 修复: 返回 progress 信息帮教师诊断)
    # 候选中间节点: from 的后继 ∩ to 的先决
    from_succ = set(_ADJ_FROM.get(from_id, []))
    to_prereq = set(_ADJ_TO.get(to_id, []))
    suggested = list(from_succ & to_prereq)[:5]
    raise HTTPException(
        status_code=404,
        detail={
            "error": "no_path",
            "from": from_id,
            "to": to_id,
            "visited_count": len(visited),
            "visited_sample": sorted(visited)[:10],
            "suggested_intermediate": suggested,
            "hint": "考虑用 /api/related/ 查跨学科软关联边 (relates_to)",
        },
    )


@app.get("/rss.xml")
def rss_feed():
    """RSS 2.0 feed — 每周更新"""
    from datetime import datetime, timezone
    updated = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    # 列出最近 enrich 过的概念 (按 src_page 倒序)
    sorted_nodes = sorted(
        [n for n in DATA["nodes"] if n.get("src_page")],
        key=lambda n: (n.get("subject", ""), n.get("src_page", 0)),
    )[:50]
    for n in sorted_nodes:
        title = f"[{n['subject']}] {n.get('title', '')}"
        desc = n.get("content_req", "")[:300]
        items.append(f"""
    <item>
      <title><![CDATA[{title}]]></title>
      <link>https://open-curriculum.cn/#/concept/{n['id']}</link>
      <description><![CDATA[{desc}]]></description>
      <category>{n.get('subject', '')}</category>
      <guid>{n['id']}</guid>
    </item>""")
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>2022 新课标知识图谱 - 最近更新</title>
  <link>https://open-curriculum.cn</link>
  <description>基于 2022 义教新课标的中国 K12 知识图谱开源基础设施</description>
  <language>zh-CN</language>
  <lastBuildDate>{updated}</lastBuildDate>
  {''.join(items)}
</channel>
</rss>"""
    return JSONResponse(content=rss, media_type="application/rss+xml")


@app.get("/api/search")
def search(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    subject: Optional[str] = None,
    limit: int = Query(20, le=100),
):
    """模糊搜索概念 (ID/标题/子领域/描述)"""
    ql = q.lower()
    results = []
    for n in DATA["nodes"]:
        if subject and n["subject"] != subject:
            continue
        if ql in (n.get("title", "") or "").lower() \
           or ql in (n.get("id", "") or "").lower() \
           or ql in (n.get("subdomain", "") or "").lower() \
           or ql in (n.get("domain", "") or "").lower() \
           or ql in (n.get("summary", "") or "").lower():
            results.append(n)
    return {
        "query": q,
        "total": len(results),
        "limit": limit,
        "concepts": results[:limit],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
