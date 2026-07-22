"""
B 端 REST API — 2022 新课标知识图谱

启动: uvicorn api.server:app --host 0.0.0.0 --port 8001
"""
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "graph" / "all_v0.7.json"

app = FastAPI(
    title="Open Curriculum CN API",
    description="基于 2022 义教新课标的中国 K12 知识图谱 REST API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载数据
def load_data():
    if not DATA_FILE.exists():
        return None
    with open(DATA_FILE) as f:
        return json.load(f)


DATA = load_data()
if DATA is None:
    raise RuntimeError(f"数据文件不存在: {DATA_FILE}, 请先跑 enrich + merge")


@app.get("/")
def root():
    return {
        "name": "Open Curriculum CN API",
        "version": "1.0.0",
        "data_version": "v0.7.5",
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
            "/rss.xml",
        ],
    }


@app.get("/api/stats")
def stats():
    by_subj = defaultdict(int)
    by_stage = defaultdict(int)
    for n in DATA["nodes"]:
        by_subj[n["subject"]] += 1
        by_stage[n.get("stage", 0)] += 1
    return {
        "total_concepts": len(DATA["nodes"]),
        "total_edges": len(DATA["edges"]),
        "by_subject": dict(by_subj),
        "by_stage": {f"G{(s-1)*2+1}-{(s-1)*2+2 if s<4 else 9}": v for s, v in sorted(by_stage.items()) if s > 0},
    }


@app.get("/api/subjects")
def subjects():
    by_subj = defaultdict(lambda: {"count": 0, "concepts": []})
    for n in DATA["nodes"]:
        by_subj[n["subject"]]["count"] += 1
    SUBJECT_CN = {
        "math": "数学", "chinese": "语文", "english": "英语", "physics": "物理",
        "chemistry": "化学", "biology": "生物", "history": "历史", "geography": "地理",
        "morality_law": "道德与法治", "science": "科学", "info_tech": "信息科技",
        "art": "艺术", "pe_health": "体育与健康", "labor": "劳动",
    }
    return {
        s: {"name_cn": SUBJECT_CN.get(s, s), "concept_count": d["count"]}
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
    """单个概念详情"""
    n = next((n for n in DATA["nodes"] if n["id"] == concept_id), None)
    if not n:
        raise HTTPException(404, f"概念不存在: {concept_id}")
    # 包含先决/后继
    pre = [{"from": e["from"], "to": e["to"]} for e in DATA["edges"] if e["to"] == concept_id]
    post = [{"from": e["from"], "to": e["to"]} for e in DATA["edges"] if e["from"] == concept_id]
    return {
        **n,
        "prerequisites": pre,
        "unlocks": post,
        "prereq_count": len(pre),
        "unlock_count": len(post),
    }


@app.get("/api/prerequisites/{concept_id}")
def prerequisites(concept_id: str):
    """概念的所有先决 (递归到根)"""
    # 邻接表
    adj = defaultdict(list)
    for e in DATA["edges"]:
        if e.get("type", 1) == 1:  # 只硬先决
            adj[e["to"]].append(e["from"])

    # BFS 找所有祖先
    all_prereqs = set()
    queue = [concept_id]
    while queue:
        cur = queue.pop()
        for pre in adj.get(cur, []):
            if pre not in all_prereqs and pre != concept_id:
                all_prereqs.add(pre)
                queue.append(pre)

    # 找 max depth
    depth = {}
    def get_depth(nid):
        if nid in depth:
            return depth[nid]
        if nid not in adj:
            return depth.setdefault(nid, 0)
        ps = adj[nid]
        d = max((get_depth(p) for p in ps), default=-1) + 1
        return depth.setdefault(nid, d)

    for n in all_prereqs:
        get_depth(n)

    concepts = [n for n in DATA["nodes"] if n["id"] in all_prereqs]
    concepts.sort(key=lambda n: (depth.get(n["id"], 0), n["id"]))
    return {
        "concept_id": concept_id,
        "total_prereqs": len(all_prereqs),
        "max_depth": max((depth.values() or [0])),
        "concepts": [{"id": n["id"], "title": n["title"], "depth": depth.get(n["id"], 0)} for n in concepts],
    }


@app.get("/api/path")
def find_path(from_id: str, to_id: str):
    """找 from → to 学习路径 (BFS)"""
    if from_id == to_id:
        return {"path": [from_id], "length": 0}

    # 邻接表
    adj = defaultdict(list)
    for e in DATA["edges"]:
        if e.get("type", 1) == 1:
            adj[e["from"]].append(e["to"])

    # BFS
    from collections import deque
    queue = deque([(from_id, [from_id])])
    visited = {from_id}
    while queue:
        cur, path = queue.popleft()
        if cur == to_id:
            # 填充详情
            concepts = [next((n for n in DATA["nodes"] if n["id"] == nid), None) for nid in path]
            return {
                "from": from_id,
                "to": to_id,
                "path": path,
                "concepts": [{"id": c["id"], "title": c["title"]} for c in concepts if c],
                "length": len(path) - 1,
            }
        for nxt in adj.get(cur, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, path + [nxt]))
    raise HTTPException(404, f"找不到从 {from_id} 到 {to_id} 的路径")


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
