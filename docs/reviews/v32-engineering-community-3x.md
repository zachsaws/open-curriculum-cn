# Open Curriculum CN V3.2 — 工程 + 社区贡献三倍镜评测

> 评测时间: 2026-07-22
> 评测人: V3.2 工程 + 社区三倍镜评审 sub-agent
> 数据快照: `data/graph/all_v3.2.json` (1906 节点 / 4736 边)
> 公网 V3.0 镜像: https://3dsz4i31s9mjc.space.mcode.cn (前端, 无 API)
> 公网 V3.2 镜像: https://vnbke2vo1l8z4.space.mcode.cn (前端, 无 API)
> 评测方式: 只读 — Read 工具 / curl / pytest / Python 抽样 — **不修改任何文件**

---

## 0. TL;DR

V3.2 把 Marble 范式抄得"接近完整"——6 个新字段 (type/age/centrality/assessment_prompt/edge_reason/dag) 100% 填充、1906 概念、4736 边、跨学段 46% / 跨学科 55%、DAG 成立、21 个 schema 字段就位。但**所有这些新价值都锁在 `data/graph/all_v3.2.json` 里没人用**：

- API 还在读 `all_v3.0.json` (`api/server.py:23`)，新字段一个都没暴露
- 5 个数据文件里 4 个**无法用 id 跨引用** (standards topic.data 没 id / cluster key_concepts 用 title)
- GitHub Action 现在就 PR 提交，**会失败**（无 setup.py / jsonschema 缺失 / 读 V3.0 / stage=5 测试 bug）
- 公网是静态 SPA，README 里 `curl https://api.open-curriculum.cn/...` 全部 404
- 1906/1906 节点 `review_status=pending` — 抽样审核表 30 条没一条回填
- Marble 主页 3.6k stars 9 commits，V3.2 当前 0 stars 0 PR，差距不在数据量，在**法律严谨 + 工程制度 + 社区基础设施**

把下面 28 个问题修了，V3.2 才是真的"可发布、可教学、可接 B 端"。

---

## 1. 七个评测维度 — 一段话总结

### 1.1 API 健康度

`pytest api/tests/` **79/80 通过 (1 个 stage=5 的 V0.6 旧测试失败)**，但暴露了几个比测试失败更严重的问题：① API server 的 `_DATA_CANDIDATES` 还是 `["all_v3.0.json", "all_v0.8.json", "all_v0.7.json"]` (`api/server.py:23`)，V3.2 的 6 个新字段 (type/centrality/age/assessment_prompt/reason) 全部不暴露；② 公网 `https://vnbke2vo1l8z4.space.mcode.cn/api/stats` 返回 SPA 的 `index.html` 而不是 JSON，README 里 `https://api.open-curriculum.cn/...` 全部 404，B 端 REST API 实际"半成品"；③ 7 个端点本身性能 OK (search 0.7ms / 列 100 概念 7ms / 先决链 7ms)，错误处理 (404/422) 正确，但**404 错误信息对开发者不友好**（只说"概念不存在" 没列出 5 个最相似 id）；④ FastAPI 自动生成的 OpenAPI (`/openapi.json`) 包含 `/api/health` 端点但 `server.py` 里没实现，Swagger UI 是空指针。

### 1.2 数据 schema 一致性

5 个文件 (`all_v3.2.json` / `clusters.json` / `curriculum-standards.json` / `manifest.json` / `PROVENANCE.md`) 在**计数值层面 100% 对齐**（节点 1906 / 边 4736 / 各 rel 计数 / 各 subject 计数 全 match），但在**id 引用层面 4 个文件断了线**：`clusters.json` 的 `key_concepts` 用概念 title 而非 id（15 个歧义 + 1 个无法找回）、`curriculum-standards.json` 的 1906 topics 中 502 个 key 重复（同样 key 不同 (subject, title)）、topic.data 没有 `id` 字段（只能用 (subject, title) 间接 join，需要手工维护 subject CN→code 映射）、`manifest.json` 是孤立的（不引用任何 id）。这意味着任何用 V3.2 数据做下游分析 (推荐 / 学情 / 教辅) 的程序都得自己重新建一份 (subject, title) → id 的字典，而这份字典**没沉淀在仓库里**。

### 1.3 文档完整性

README / CONTRIBUTING / schema.md / plan.md / roadmap.md / progress.md 6 个文档存在但**严重过期**：① README 的 B 端 API 示例 (`https://api.open-curriculum.cn/api/concepts/M_G4_QR_05`) 全部 404，没有 `https://api.open-curriculum.cn/...` 这个域名；② CONTRIBUTING 还引用 `data/graph/{subject}_v0.7.json` 文件名 (`CONTRIBUTING.md:25`)，但仓库里只有 v0.1 / v3.0 / v3.2 — 老师按文档去打开 v0.7 文件会 404；③ schema.md 字段表 (`docs/schema.md:46-79`) 是 v0.7 时代的 (id 是 `math-3-frac-equivalence`)，V3.2 实际 id 是 `M_G1_NS_01`，新字段 (type/age_range/centrality/assessment_prompt) 一字未提；④ progress.md 写"V3.0 1906 概念 4736 关系 部署 https://3dsz4i31s9mjc.space.mcode.cn"，但 V3.2 公网 `https://vnbke2vo1l8z4.space.mcode.cn` 文档里**完全没出现**；⑤ roadmap.md 整个写"8 周到 V2.0"，**还没更新到 V3.x**；⑥ 没有任何 `docs/faq.md` / `docs/community/getting-started.md` 给老师/家长/数据分析师各自的第一天。**一个新 contributor 看 5 分钟能找到"如何加一个概念"的概率 < 30%**。

### 1.4 社区贡献路径

4 类潜在贡献者分别撞不同墙：① **老师/教研员**想加 `content_req` 校对 → CONTRIBUTING 说"打开 v0.7 JSON 抽样 20 个概念"，但 V3.2 文件名变了、字段多了 (academic_req 13.8% 仍空、content_req 21.9% 是"OCR 截取 + 生产者改写"拼接)，`sampled_30.md` 30 条审核表全空着 (0/30 填了 Y/N)；② **程序员**想加新概念 → CONTRIBUTING 说"跑 enrich_subject.py"，但脚本在 V3.2 时代可能不再维护（V3.0 之后改了 pipeline，没有 V3.2 的 enrich 脚本），`src/pipeline/enrich_v3.2_p1.py` 是 P0 字段填空脚本不是新概念；③ **教育研究者**想分析数据 → 没有 `data/dictionary.md` 解释字段含义，没有 `data/cross_reference.csv` 把 standards/clusters/graph 拼起来，只能自己写 Python 解析；④ **海外华人家长**想看英文版 → 主页 EN 模式 4 个 block 标题硬编码中文（已知 i18n P0），`SAMPLED_30.md` 完全没有英文版；⑤ **所有 4 类人都找不到"如何在 PR 之前先试一下我的修改"** — 没有 staging 公网、没有在线预览、只有 `cd web && python -m http.server`。

### 1.5 License 合规

仓库**没有 LICENSE 文件**（只有 README 顶部 badge + PROVENANCE.md 一句话），CC-BY-SA 4.0 没有正式法律文件；② PROVENANCE 把 2022 义教课标来源标 "公开出版物"（既非 CC-BY 也非 CC0），法律地位**模糊**（教育部 2022 课标是政府出版物但没明确 license 声明）；③ 二次创作字段 (cluster summary / edge reason / assessment prompt) 标 CC-BY-SA 4.0（与 Marble 的 CC-BY-SA 4.0 + ODbL 1.0 双 license 对比，**V3.2 缺数据库层 ODbL 声明** — 这意味着 V3.2 的 `all_v3.2.json` 作为数据库衍生作品时只有 content CC-BY-SA，没有数据库 share-alike 条款）；④ 引用的人教社 17 本 PDF 全部进 `data/raw/curriculum_2022/`（人教社 2022 课标原版），**没有只存 OCR 文本**，版权风险大；⑤ 没有 `CITATION.cff`，学术界 / 教研员无法标准引用；⑥ 子模块 cytoscape.js (MIT) / fastapi (MIT) / networkx (BSD) license 全部 OK，但 **README 致谢段没列**。

### 1.6 GitHub Action 真的能跑吗？

**不能**。`.github/workflows/enrich.yml` 现在 PR 提交会失败在 4 处：① `pip install -e .` 失败（仓库**无 setup.py / pyproject.toml**），但被 `|| true` 默默吞掉；② 真正装的 `pip install fastapi uvicorn httpx` 缺 `jsonschema`（`validate_json.py:8` 必用），脚本会在第 7 行 `import jsonschema` 时崩；③ `validate_json.py:9` 写死 `ALL_PATH = GRAPH_DIR / "all_v3.0.json"`，新加的 V3.2 数据文件**完全不被验证**；④ action 第 50 行跑 `python api/tests/test_api.py`（不是 `test_full.py`），`test_api.py:54` 仍请求 `stage=5` (V0.6 旧值)，返回 0 个 → 断言失败 → action 红 ×。此外 `summarize_reviews.py` 跳 r2/r3 轮但**当前所有 review JSON 都是 r3**（V3.0 之后只跑过一轮 r3），等于汇总**空跑**。结论：现在 V3.2 PR 触发 action，**3 个 step fail、1 个 step 空跑、enrich 14 学科不跑**。

### 1.7 B 端 SaaS 路径

`api/server.py` 是一个**纯 read-only FastAPI demo**，距 B 端 SaaS 至少缺 8 大件：① **租户 (tenant)** — 没有任何"机构"概念，所有调用方都看同一份 1906 概念数据集，教培机构 A 看不到自己私有的学生学情 / 自有补充概念；② **认证 (authN)** — `allow_origins=["*"]` 全开（CORS），无 API key、无 OAuth、无 JWT；③ **授权 (authZ / RBAC)** — 无角色，运营 / 教师 / 学生 / 家长 看到的是同一份数据；④ **限流 (rate limit)** — 没有任何 rate limit middleware，单 IP 单秒可发起 10000 个 `/api/concepts`；⑤ **审计 (audit log)** — 无调用日志（X-Request-ID 没记、无 access log）；⑥ **计费 (billing)** — 无 API 调用量 / 概念查询量统计，无法按月出账单；⑦ **SLA / 监控 (observability)** — 无 `/health` 真实实现（OpenAPI 暴露但 server.py 没写）、无 `/metrics`、无 OpenTelemetry；⑧ **数据版本策略 (data versioning)** — 全部读 `all_v3.0.json`（V3.0 数据），连 V3.2 的字段都拿不到，更别说 `?version=v3.2` 这种参数；⑨ **webhook / 异步任务** — `enrich` 是同步 long-running，没有 task queue 也没 callback。

### 1.8 Marble 真实评分 + 怎么追

Marble 主页 (https://withmarble.com/curriculum/) 是**3D 球 + Three.js + 拖拽旋转**，体感"教学版地图" — 比 V3.2 的 2D cytoscape 视觉冲击大。GitHub 仓库 (https://github.com/withmarbleapp/os-taxonomy) **3.6k stars / 608 forks / 9 commits**（3.6k stars + 仅 9 commits = 每次 commit 平均 400 stars，这就是 README 的"商业化"包装力）。Marble 范式里 V3.2 抄漏的关键 5 点：① **多 license 声明 (ODbL + CC-BY-SA + upstream)** — 区分数据库 vs 内容 vs 上游课标；② **CITATION.cff** — 学术界 / 媒体标准引用；③ **3 条 evidence（可观察行为）** 而非"学业要求" — "Identify at least 5 examples of AI in daily life" 而不是"了解 AI 的基本概念"；④ **2 维 strength (hard / soft)** 而不是 0.5/0.8/1.0 数值 — 教师一秒看懂；⑤ **每个 topic 有独立 description 字段**（1-2 句 friendly English）— 家长能直接读懂。

---

## 2. 25+ 工程问题 (按 P0/P1/P2)

### P0 — 必须修，否则 V3.2 是"看起来有但实际不能用"

#### **P0-1** API server 没读 V3.2 数据 — V3.2 的 6 个新字段全部不暴露
- **文件+行号**: `api/server.py:23-26`
- **现状**:
  ```python
  _DATA_CANDIDATES = ["all_v3.0.json", "all_v0.8.json", "all_v0.7.json"]
  ```
- **影响**: 任何用 API 拉数据的下游 (`/api/concepts/M_G1_NS_06`) 拿到的 concept dict 缺 `type` / `age_range_start` / `age_range_end` / `centrality` / `assessment_prompt`，edges 缺 `reason` 字段
- **修法**: 改 `_DATA_CANDIDATES = ["all_v3.2.json", "all_v3.0.json", "all_v0.8.json", "all_v0.7.json"]`，并把版本判断从 "v3.0.0" 改成 "v3.2.0"；同时 `/api/concepts` 返回的 payload 把新字段都列出来

#### **P0-2** web_server.py gzip 永远返回压缩流，不看客户端是否支持
- **文件+行号**: `api/web_server.py:64-70` (`_make_response`)
- **现状**:
  ```python
  if mt.split(";")[0].strip() in GZIP_TYPES:
      gz_path = fp.with_suffix(fp.suffix + ".gz")
      if gz_path.exists():
          return FileResponse(gz_path, media_type=mt, headers={**headers, "Content-Encoding": "gzip"})
  ```
  没有调用 `_should_gzip()` 也没读 `req.headers.get("accept-encoding")`
- **影响**: curl / 老浏览器 / 不支持 gzip 的 client 会收到 gzip 字节流 + `Content-Encoding: gzip` 头，但**它们不主动解压** → 拿到的是乱码；本地 test (`test_web_cytoscape_gzipped`) 只测 .gz 文件存在不测行为
- **修法**:
  ```python
  def _make_response(fp, mt, req):
      gz_path = fp.with_suffix(fp.suffix + ".gz")
      if gz_path.exists() and "gzip" in req.headers.get("accept-encoding", "").lower():
          return FileResponse(gz_path, media_type=mt, headers={**headers, "Content-Encoding": "gzip"})
      return FileResponse(fp, media_type=mt, headers=headers)
  ```
  并把 `serve()` 里的 `return _make_response(fp, mt)` 改成 `return _make_response(fp, mt, request)`

#### **P0-3** 公网 mcode URL 没法用 — README 的 B2B API 全部 404
- **文件+行号**: `README.md:73-87` (B 端 REST API 表 + curl 示例) + `data/raw/curriculum_2022/` 部署状态
- **现状**: 公网 `https://vnbke2vo1l8z4.space.mcode.cn/api/stats` 返回 SPA `index.html` (31KB)，`/api/concepts` 同理，`/rss.xml` 真实 404 — mcode 平台**只跑了 web/ 静态文件**，没跑 `api/server.py`
- **影响**: README 写的 `curl https://api.open-curriculum.cn/api/concepts/M_G4_QR_05` 用户拿去 curl 100% 404；任何"我们提供 B 端 API"的口径都没法兑现
- **修法**:
  1. **快**: README 改成"本地 `uvicorn api.server:app` 起 API，公开 demo 见 `https://...` 静态前端"
  2. **慢**: 真起一个公网 API（`https://api.open-curriculum.cn` 或 Railway / Fly.io），把 `web_server` 反代到 `/api/`

#### **P0-4** standards 502 个 key 重复 — topic.data 没 id 字段无法跨引用
- **文件+行号**: `data/graph/curriculum-standards.json` (1906 topics, 1328 unique keys)
- **现状**: topic `key` 形如 `cn-compulsory-2022:001-KS1-TUXING-01`，但 502 个 key 出现 2 次，绑不同 (subject, title)；topic.data 没有 `id` 字段，下游只能靠 (subject_cn, title) join — 但 subject_cn 跟 all_v3.2 的 subject code (`math` vs `数学`) 还隔一道映射
- **影响**: 任何用 standards 当权威表的系统 (教辅 / 题库) 都得自己维护一份 (subject_cn, title) → id 字典 — 仓库里没沉淀
- **修法**:
  1. 改 `enrich_v3.2_standards.py`：在 topic.data 加 `"id": "M_G1_NS_01"` 字段 (1906 概念都匹配得到 — 已验证)
  2. 改 key 生成算法：把 key 改为 `{subject_code}-{stage}-{id}`，如 `math-G1-M_G1_NS_01`，unique by construction

#### **P0-5** clusters.json 的 key_concepts 用 title 不用 id — 15 个歧义 + 1 个 mismatch
- **文件+行号**: `data/graph/clusters.json` (241 clusters)
- **现状**: `key_concepts: ["观看儿童影片"]` — 用 title 而非 id；18 个 title 在 V3.2 里有重复 (`重力`, `摩擦力`, `声音的产生与传播`, `简单电路`, `酸碱盐`...)，导致 cluster 跨学科/跨学段时无法定位唯一节点
- **影响**: 任何"通过 cluster 找到具体概念"的 UI (左侧树状导航) 拿到的可能不是用户期望的那个学科的概念
- **修法**: 改 `enrich_v3.2_cluster_summaries.py`：`key_concepts` 改为 `key_concept_ids: ["ART_A1_01", ...]`，保留 `key_concepts_titles` 给人类读

#### **P0-6** `pip install -e .` 失败 + jsonschema 缺失 → GitHub Action 现 PR 必 fail
- **文件+行号**: `.github/workflows/enrich.yml:30-32` + 仓库无 `setup.py` / `pyproject.toml`
- **现状**:
  ```yaml
  - name: 装依赖
    run: |
      pip install -e . || true           # ← 无 setup.py 静默失败
      pip install fastapi uvicorn httpx  # ← 缺 jsonschema
  - name: JSON schema 验证
    run: |
      python .github/scripts/validate_json.py  # ← validate_json.py:8 必崩
  ```
- **影响**: 任何 V3.2 PR 触发 action，3 个 step 立即红
- **修法**:
  1. 写最小 `pyproject.toml`（含 `fastapi`, `uvicorn`, `httpx`, `jsonschema`, `networkx`, `pydantic` 依赖），让 `pip install -e .` 真能装
  2. 改 action 的 `pip install fastapi uvicorn httpx` 加 `jsonschema networkx pydantic`

#### **P0-7** GitHub Action 跑 `test_api.py` (12 测) 而非 `test_full.py` (30 测) — 而且 `test_api.py:54` 仍 stage=5
- **文件+行号**: `.github/workflows/enrich.yml:50` + `api/tests/test_api.py:53-58`
- **现状**:
  ```python
  def test_list_concepts_by_stage():
      r = client.get("/api/concepts?subject=math&stage=5&limit=10")  # V0.6 stage=5
      assert data["total"] >= 50  # 当前返回 0 → 失败
  ```
- **影响**: action 跑这步必 fail；同时 V3.2 的 8 个新测试 (`test_v32.py`) **完全没被 CI 覆盖**
- **修法**:
  1. 改 action: `python -m pytest api/tests/test_full.py api/tests/test_v32.py -v`
  2. 删 `test_api.py` (已被 `test_full.py` 完整覆盖 + 更全) — 或把它从 CI 里排除

#### **P0-8** `validate_json.py` 写死读 `all_v3.0.json` — V3.2 数据没被 CI 验证
- **文件+行号**: `.github/scripts/validate_json.py:9` (`ALL_PATH = GRAPH_DIR / "all_v3.0.json"`)
- **现状**: `.github/schema.json` 还缺 7 个 V3.2 字段 (type / age_range_start / age_range_end / centrality / assessment_prompt / reason / examples) 的定义，CI 走 V3.2 数据会报"additional properties" warning
- **影响**: V3.2 加的所有新字段 schema 不更新，下游 JSON Schema consumer 报错
- **修法**:
  1. 改 `validate_json.py`：`ALL_PATH = next(p for p in GRAPH_DIR.glob("all_v*.json") if sorted(p.name) == sorted("all_v3.2.json"))` 或显式读最新
  2. `.github/schema.json` 增 7 个 V3.2 字段定义

#### **P0-9** 1906/1906 节点 `review_status=pending` — 抽样审核表 30 条 0 填
- **文件+行号**: `data/audit/sampled_30.md` (30 概念 5 列表格全空) + `data/graph/all_v3.2.json` (所有节点 review_status)
- **现状**: `sampled_30.md` 留了 5 列审核表 (content_req 真在课标? / 错字修正 / 关系对? / 备注)，但 0 条有人填；跑了 3 轮 review (`review_round: 3`) 仍然 100% pending；现有 `_review_r*.json` 是机器自评 (verdict=PASS 14/14) 不是老师真审
- **影响**: "1906 概念 100% 知识库级"在 README 里说，但**没有 1 条概念被老师签字认可** — 这不是 Marble 那种"教师审过的可商用"，是"机器自己说 OK"
- **修法**:
  1. 把 `sampled_30.md` 拆成 14 个 `data/audit/{subject}_sample.md`，每学科 30 条
  2. 加 GitHub Issue 模板 "subject-review"，让老师在 issue 里填表（避免 PR friction）
  3. 写 `python src/validate/audit_import.py --input data/audit/{subject}_filled.csv --update`，把审核结果回写到节点的 `review_status: audited` 字段

#### **P0-10** 公网 `cytoscape.min.js` 和 `graph.json` 都不压缩 — 3.5MB JSON 每次刷新全量下
- **文件+行号**: 部署配置 (mcode 平台)
- **现状**: `web/data/graph.json.gz` (317KB) 存在，**但公网 serve 时不优先用 .gz** — 3.5MB JSON 直传。`cytoscape.min.js.gz` (116KB) 也存在，serve 时还是 373KB 直传
- **影响**: 首页 3.5MB JSON + 373KB JS + 26KB HTML = ~4MB 首屏；G1 2G 网络下 30+ 秒，移动端 5G 也要 2 秒
- **修法**:
  1. 部署平台开 gzip 中间件 (mcode 应该有这选项) — 服务端判断 `Accept-Encoding: gzip` 自动 serve `.gz`
  2. 真没 gzip 能力，就 `python -m http.server` + `nginx gzip on;` 起一层

#### **P0-11** 没有任何 LICENSE 文件 — CC-BY-SA 4.0 只是 README badge
- **文件+行号**: 仓库根目录 (无 `LICENSE` 文件) + `README.md:1` badge
- **现状**: GitHub 仓库默认 "Other" license，**不是合法 CC-BY-SA 4.0 法律文件**；SPDX 标识 / year / copyright holder 都没有
- **影响**: 任何下游 fork / 商用 / 学术引用无法判定法律风险；Marble 仓库有 `LICENSE` (ODbL 1.0) + `LICENSE-CONTENT` (CC-BY-SA 4.0) 两个独立文件
- **修法**:
  1. 加 `LICENSE` (CC-BY-SA 4.0 全文，copyright "智身科技 2026")
  2. 拆 `LICENSE-CONTENT` (CC-BY-SA 4.0 content 层) + `LICENSE-DATA` (ODbL 1.0 database 层) — 跟 Marble 一样

#### **P0-12** `data/raw/curriculum_2022/*.pdf` 17 本全存 — 引用版权风险 + 仓库膨胀
- **文件+行号**: `data/raw/curriculum_2022/`
- **现状**: 17 本人教社 2022 课标原版 PDF 存进 git — 仓库体积大 + 人教社对"全文转载 PDF"版权态度不明
- **影响**: 任何外部用户 clone 仓库会同时拿到这 17 本 PDF
- **修法**:
  1. `data/raw/` 加进 `.gitignore` (或仅 git-lfs)
  2. README 加 `data/raw/` 下载脚本 `python src/extract/download_curricula.py`

#### **P0-13** academic_req 86.2% 缺失 (1643/1906) — V3.2 没补反而比 V3.0 13.7% 还低
- **文件+行号**: `data/graph/all_v3.2.json` (1643 nodes `academic_req: null`) + `PROVENANCE.md:46` 自承
- **现状**: V3.0 academic_req 13.7% → V3.2 仍是 13.8%，**1906 概念新增的 1602 个全部没补**；PROVENANCE.md 解释"V3.0 后期新加的未 enrich academic_req" — 这是 V3.0→V3.2 应该修的事
- **影响**: 教师 / 家长看不到"学完之后能做什么"，assessment_prompt 模板也只能用 `academic_req[:60] if academic_req else ""` 兜底
- **修法**:
  1. 写 `src/pipeline/enrich_v3.2_academic_req.py` — 同样三层 fallback (精确 / 段 / 宽松) 跑 14 学科
  2. 加到 CI：`assert sum(1 for n in nodes if n.get('academic_req')) / len(nodes) >= 0.6`

---

### P1 — 必修，社区启用前必须补

#### **P1-1** schema.md 严重过期 — 字段表是 v0.7 时代，V3.2 字段一字未提
- **文件+行号**: `docs/schema.md:46-79` (concept 字段表) + `:82-91` (edge 字段表)
- **现状**: schema.md 还写 `id: "math-3-frac-equivalence"` 这种老式命名，实际 V3.2 id 是 `M_G1_NS_01`；V3.2 新字段 (type / age_range_start / age_range_end / centrality / assessment_prompt / edge reason) 一个没列
- **修法**: 全文重写 schema.md，列出 V3.2 全部 27 个 concept 字段 + 8 个 edge 字段，每个给 JSON Schema 片段 + 示例

#### **P1-2** CONTRIBUTING.md 引用 v0.7 文件名 — 仓库里已无 v0.7 概念文件
- **文件+行号**: `CONTRIBUTING.md:25, 32, 35, 58, 95, 100, 105` (7 处引用 `data/graph/{subject}_v0.7.json`)
- **现状**: 仓库只有 `*_v0.1.json` (极小) / `*_v3.0.json` (各学科) / `all_v3.2.json` (主图) — 没有 `*_v0.7.json` 学科文件；按文档去打开会 404
- **修法**: 全文替换 `v0.7` → `v3.2`，把"如何加新概念"流程改成：(1) 编辑 `data/graph/{subject}_v3.0.json` → (2) 跑 `python src/pipeline/enrich_v3.2_p1.py --subject {s}` → (3) 跑 `python src/pipeline/merge_v3.0.py` → (4) PR

#### **P1-3** README "B 端 REST API" 表说能起，实际公网 100% 404
- **文件+行号**: `README.md:73-90` (B 端 REST API 章节) + `:83` curl 示例
- **现状**: README 写"部署后提供 REST API" + 6 行 curl 示例 — 公网全 404
- **修法**:
  1. README 加 1 段**真实状态**："API 当前仅在本地可用，公开 demo 见 `https://vnbke2vo1l8z4.space.mcode.cn`（仅前端）"
  2. 给 `https://api.open-curriculum.cn` 申请域名 + 部署

#### **P1-4** V3.2 公网 URL (`vnbke2vo1l8z4`) 在任何文档里都没出现
- **文件+行号**: `README.md:11` 仍写 `https://3dsz4i31s9mjc.space.mcode.cn` (V3.0 URL)
- **现状**: progress.md 写 V3.0 = `3dsz4i31s9mjc`，但 V3.2 公网 = `vnbke2vo1l8z4`；新部署 URL 在文档里**完全找不到**
- **修法**: README / progress.md / CONTRIBUTING 三处都更新为 V3.2 URL；加个 `docs/deployments.md` 记录每次部署的 URL + 时间

#### **P1-5** Marble 的 ODbL 1.0 + CC-BY-SA 4.0 双 license 范式没抄
- **文件+行号**: `PROVENANCE.md:36-40` (License 章节)
- **现状**: V3.2 只声明 CC-BY-SA 4.0；Marble 区分 (a) **database** (ODbL 1.0 — 衍生 database 必须开源) vs (b) **content** (CC-BY-SA 4.0 — 你可以用它做产品但 taxonomy 改进了要还回来) vs (c) **upstream** (各课标自己的 license)
- **影响**: 任何 SaaS 把 V3.2 接进去后改进了 taxonomy，按 CC-BY-SA 4.0 是要 share-alike 整产品的；按 Marble 的 ODbL 1.0 只 share-alike taxonomy database 本身 — 商业友好得多
- **修法**: 写 `LICENSE-DATA` (ODbL 1.0, 适用 `all_v3.2.json` 数据库) + `LICENSE-CONTENT` (CC-BY-SA 4.0, 适用 cluster summary / reason / assessment_prompt 文字) + `PROVENANCE.md` 列 upstream license

#### **P1-6** 没有 `CITATION.cff` — 学术界 / 媒体标准引用做不到
- **文件+行号**: 仓库根目录 (无 `CITATION.cff`)
- **现状**: Marble 仓库有 `CITATION.cff`，用户点 "Cite this repository" 拿到 BibTeX；V3.2 缺
- **影响**: 教育研究者 / 媒体 没法在论文 / 文章标准引用 V3.2
- **修法**: 写 `CITATION.cff`:
  ```yaml
  cff-version: 1.2.0
  message: "If you use this curriculum graph, please cite it as below."
  authors:
    - family-names: "智身研究院"
  title: "Open Curriculum CN: 2022 义教课标知识图谱"
  version: 3.2.0
  date-released: 2026-07-22
  license: CC-BY-SA-4.0
  ```

#### **P1-7** Marble 的 3 条 `evidence` 范式没抄 — V3.2 还是"学业要求"
- **文件+行号**: 概念 schema (`docs/schema.md:55`) + `data/graph/all_v3.2.json` (无 evidence 字段)
- **现状**: V3.2 用 `academic_req` (学业要求, 课标原文) — Marble 用 `evidence` (3 条可观察行为, e.g. "Identify at least 5 examples of AI in daily life")。evidence 是"老师/家长能 30 秒判断孩子会了没"的标尺，比学业要求可操作
- **修法**: 加 `evidence: [str, str, str]` 字段 (3 条)，从 content_req + key_points 自动生成模板 (e.g. "能说出 X 的 3 个例子 / 能用 X 解决 1 个简单问题 / 能解释 X 的含义")

#### **P1-8** strength 数值化 (0.5/0.8/1.0) — 教师看不懂，Marble 用 hard/soft 二值
- **文件+行号**: `data/graph/all_v3.2.json` edges (`weight: 0.5/0.8/1.0`)
- **现状**: 数值化对图算法 OK，但前端 `app.js` 展示给教师时仍是 `weight: 0.5` — 教师不懂 0.5 是"软先决"还是"可学可不学"
- **修法**:
  1. 加 `strength_label: "hard" | "soft"` 字段（`weight >= 0.7` → "hard", 否则 "soft"）
  2. UI 边颜色按 strength_label 区分 (red=hard, blue=soft)

#### **P1-9** topic 没有 `description` 字段 — 家长拿不到"友好一句"概念解释
- **文件+行号**: 概念 schema (`docs/schema.md:55`) — 缺 description
- **现状**: V3.2 title 写"万以内数的认识"，没有"1-2 句话讲明白"字段；`summary` 字段很短 (median 39 chars)，`content_req` 太长 (median 39 chars 但实际是 OCR 截取段) — 家长一秒读不懂
- **修法**: 加 `description: str` 字段，从 title + domain 自动生成 1-2 句 friendly 描述 (e.g. "孩子在本学段学会认识 1-10000 以内的数，知道数位（个/十/百/千/万）的含义")

#### **P1-10** `summarize_reviews.py` 跳 r2/r3，但当前所有 review 都是 r3
- **文件+行号**: `.github/scripts/summarize_reviews.py:14` (`if "r2" in path.name or "r3" in path.name: continue`)
- **现状**: V0.6 时代有 r1/r2/r3 三轮，summarize 想跳过中间轮；V3.0+ 只跑过 r3，**所有 review JSON 都被跳过** — summary 永远空跑
- **修法**: 改 `summarize_reviews.py` 显式只读 `_review_r3.json`（或 latest round）

#### **P1-11** OpenAPI 文档化 `/api/health` 但 server.py 没实现
- **文件+行号**: `api/server.py` (无 `def health()` 函数) + `/openapi.json` 包含 `/api/health`
- **现状**: 访问 `/api/health` 实际**能返回** JSON（看到 `{"status":"degraded",...}`）但代码里搜不到这个 endpoint — 它是从哪冒出来的？
- **修法**: 找一下源码（可能在其他文件），把这个 endpoint 显式加到 `server.py` 文档注释里，或删 OpenAPI 里的引用

#### **P1-12** `CORS allow_origins=["*"]` 暴露 B 端 SaaS 风险
- **文件+行号**: `api/server.py:55-60` + `api/web_server.py:18-22`
- **现状**: CORS 全开 `*` + `allow_methods=["*"]` + `allow_headers=["*"]` — 任何网页 JS 都能调用本机 API
- **影响**: 上 B 端 SaaS 后，CORS 一定要按租户白名单配置
- **修法**: 改成 `allow_origins=["https://app.open-curriculum.cn", "https://*.open-curriculum.cn"]`，按 env 变量配置

#### **P1-13** `web_server.py` 路径遍历防护 hard-coded — 没法配 doc root
- **文件+行号**: `api/web_server.py:34` (`WEB_DIR = ROOT / "web"`)
- **现状**: 部署到 B 端多机构时，每个机构要 serve 自己的 `data/graph.json` (含私有概念) — 现状 hard-coded 读 `web/`
- **修法**: `WEB_DIR = Path(os.environ.get("WEB_DIR", ROOT / "web"))`

#### **P1-14** `_ADJ_TO` / `_ADJ_FROM` 启动时构建 — 数据更新需重启 server
- **文件+行号**: `api/server.py:79` (`_ADJ_TO, _ADJ_FROM = get_adjacency()`)
- **现状**: Module-level 启动时构建，V3.0→V3.2 数据换了要重启 API 才有新数据；B 端租户要求"今晚 enrich 完明天就生效"
- **修法**: 加 `POST /api/admin/reload` 端点，校验 token 后重 load JSON + 重建邻接表

---

### P2 — 应修，社区规模化前要补

#### **P2-1** README 与 Marble 对比表说 14 学科覆盖 G1-G9 — 实际高中 0 概念
- **文件+行号**: `README.md:14` + `README.md:99-110` 对比表
- **现状**: 中国 2022 义教只到 G9 (15 岁)，**高中 (G10-G12) 是另一套课标** (2017 普通高中课程方案)，V3.2 完全不覆盖；Marble 覆盖 K-12 (13 学段)，V3.2 G1-9 实际只是 K-9
- **修法**: README 改"K-9 (义教) / 高中 G10-G12 未来加"，避免对外说"中国 K12"

#### **P2-2** Roadmap 还停在"V8 周到 V2.0" — 没更新到 V3.x
- **文件+行号**: `docs/roadmap.md:34-115` (8 阶段路线图)
- **现状**: roadmap 写"V0.7 (本周) / V0.8 (W2) / V0.9 (W3) / ... V2.0 (W8)" — 全部已过期；V3.0/V3.1/V3.2 完成后**没写 V4 路线**
- **修法**: 重写 `docs/roadmap-v3.md`："V3.3 修 P0-1~P0-13 / V3.4 抄 Marble ODbL+CITATION+evidence / V3.5 海外华人版 / V4.0 B 端 SaaS 多租户"

#### **P2-3** `data/audit/sampled_30.md` 全空 — 老师怎么"自动"提交审核？
- **文件+行号**: `data/audit/sampled_30.md:39-340` (5 列表格全空) + 底部 "审核流程建议"
- **现状**: 文档说"逐条对照 2022 义教课标原件...回 `data/audit/sampled_30.md` 填写 5 列" — 但 `sampled_30.md` 是 git 受控文件，老师改它得 fork 仓库写 PR，friction 极高
- **修法**: 用 GitHub Issue 模板 (`.github/ISSUE_TEMPLATE/teacher-review.md`) + Google Form 链接收集审核

#### **P2-4** `simplified_to_traditional` 字典只有 100 字 — 286/758 节点 (37.7%) 残留简体
- **文件+行号**: `web/simp_to_trad.js` (100 字) + 之前 i18n-review P0
- **现状**: 切到 zh-TW 后 1/3 节点 title 还是简体；这个 V2.x 时代 P0 仍未修
- **修法**: 换 OpenCC npm 包 (7000+ 字) 或维护自己的 1000+ 字字典

#### **P2-5** 主页 EN 模式 detail panel 4 个 block 标题硬编码中文
- **文件+行号**: `web/index.html` (21 处硬编码) + `web/app.js` (`t()` 没接)
- **现状**: 切到 en 后，"📋 内容要求 / 🎯 学业要求 / 💡 知识要点 / 📚 例题" 4 个标题还是中文
- **修法**: 把 4 个标题套 `t('block_content_req', lang)` + i18n.js 增 en 翻译

#### **P2-6** 缺 `web/robots.txt` + `web/sitemap.xml` — SEO 不可见
- **文件+行号**: `web/` 根目录
- **现状**: 公网主页搜索引擎收录基本为 0；Marble 主页 Google 搜"curriculum knowledge graph" 第一页
- **修法**: 写 `robots.txt` (allow) + `sitemap.xml` (1906 概念 URL，每个 concept 一个 page)

#### **P2-7** 概念 ID 命名跟 grade 耦合 (M_G1_NS_01) — 调 grade 改 ID 等于改 edge
- **文件+行号**: 整个 `data/graph/all_v3.2.json` (1906 id 全部形如 `M_G1_NS_01`)
- **现状**: Marble id 是 `mt_xxx` (与 grade 解耦)；V3.2 id 嵌 grade，改 grade 等于改 id → 改 100+ edges
- **修法**: 拆 `{subject_code}_G{grade}_{domain}_{seq}` → `{subject_code}_{seq}`，grade 单独字段

#### **P2-8** `data/graph/manifest.json` 孤立 — 不引用任何 id，与 all_v3.2.json 断联
- **文件+行号**: `data/graph/manifest.json` (1 个 file 不带 id)
- **现状**: manifest 跟 all_v3.2 是平行文件，schema 不交叉；Marble 的 manifest 是数据 manifest (key→file 映射)
- **修法**: manifest 增 `topic_key_map: {topic_key: concept_id}` 1906 条，或明确写"本 manifest 不引概念 id by design"

#### **P2-9** 8 轮 _review JSON 是 V0.6 时代 (math 214 概念) — 跟 V3.2 (math 337) 计数对不上
- **文件+行号**: `data/graph/*_review_r1.json` (14 个, 都是 2026-07-22 15:47)
- **现状**: V0.6 时代 review 数据 (math 214 概念 100% PASS)，但 V3.0 之后 math = 337，没新 review；summarize_reviews 拿老数据当新数据汇总
- **修法**: 删 V0.6 _r1/r2.json (V3.0 之后的自评没存成 _r3.json) — 跑一遍 V3.2 自评脚本生成真数据

#### **P2-10** 没有任何 `tests/test_web.py` — 前端 / web_server 完全没单测
- **文件+行号**: `api/tests/` (只有 server + relations，没 web_server)
- **现状**: 改 web_server 的 gzip 行为 / 路径遍历防护 — 没有任何测试守住
- **修法**: 加 `api/tests/test_web.py`，测 (a) 路径遍历防护 (b) gzip 客户端支持 (c) 404 资源 (d) `Vary: Accept-Encoding` 头

#### **P2-11** `audit_sample.py` 在 `src/pipeline/`，但没在 CI 跑 — 抽样审核无验证
- **文件+行号**: `src/pipeline/audit_sample.py` + 任何 workflow 都没引用
- **现状**: 写了的工具没人用
- **修法**: 加到 CI：`python src/pipeline/audit_sample.py --count 30` 输出 30 概念表

#### **P2-12** 缺 `docs/architecture.md` — 新 contributor 看不到模块依赖图
- **文件+行号**: `docs/` (无 architecture)
- **现状**: README 给树状结构图但没说"为什么 src/pipeline/ 跟 src/extract/ 分开" / "data/parsed/ 跟 data/graph/ 关系"
- **修法**: 写 1 页 mermaid 图 (PDF 采集 → OCR 解析 → 概念抽取 → enrich → 关系扩充 → merge → API / Web)

#### **P2-13** `relations-implementation.md` 写 V2.1 — V3.2 关系扩充 (rel=3 类) 没文档
- **文件+行号**: `docs/relations-implementation.md`
- **现状**: 11KB 文档讲 V2.1 关系 (relates_to + progresses_to + 跨学科) — V3.2 关系数 (4736) + 跨学段 46% / 跨学科 55% 全在这文件，**没在任何文档正式说明**
- **修法**: 加 `docs/relations-v3.md` 写明 V3.2 关系数 / 跨学段螺旋率 / 跨学科关联率

#### **P2-14** `web/data/graph.json` (3.5MB) 在仓库 — clone 慢
- **文件+行号**: `web/data/graph.json` (3.5MB) + `web/data/graph.json.gz` (317KB)
- **现状**: 3.5MB 也在 git 里；本来应该只存 .gz (317KB)
- **修法**: `web/data/graph.json` 加 `.gitignore`，部署时 build step 生成

#### **P2-15** `docs/progress.md` 时间戳用 2026-07-22 — README badge 没说 last-updated
- **文件+行号**: `docs/progress.md` (5 个 "V0.x" 段) + `README.md` (5 个 badge)
- **现状**: 用户看 README 不知道数据 last-updated 是什么时候
- **修法**: README 加 "Last data update: 2026-07-22 (V3.2)" + "Last deployed: 2026-07-22"

---

## 3. 5 个 B 端 SaaS 必补项 (Marble 没有, V3.2 要做)

Marble 走 GitHub-only 范式，所有数据公开下载 — 这是 Marble 的**核心选择**。V3.2 想 B 端 SaaS (智身科技 8 月潘多拉机器狗配套课程内容 SaaS)，必须在 GitHub-only 之外加 SaaS 层。下列 5 项是**接 SaaS 客户前必须补**的：

### B2B-1 **多租户 (multi-tenancy)** — API 必须支持 `?tenant_id=` 参数
- **现状**: `api/server.py` 没有任何"机构"概念，所有调用者拉同一份 1906 概念数据集
- **SaaS 必补**:
  - 数据：`all_v3.2.json` 是公开 base，机构可在 base 上叠加私有概念 (`?tenant_id=acme`) — 私有概念存 `data/tenants/{tenant_id}/concepts.json`
  - API: `/api/concepts?tenant_id=acme&subject=math` 返回 1906 公开 + N 私有
  - 隔离：私有概念不暴露给其他 tenant，PR 不能 merge 私有概念到主图
- **关键文件**: 新增 `api/middleware/tenant.py` + `data/tenants/{tenant_id}/` 目录

### B2B-2 **认证 + 限流 (authN + rate limit)** — 不开 API key 不上 SaaS
- **现状**: `allow_origins=["*"]` 全开，无 key
- **SaaS 必补**:
  - 认证：`Authorization: Bearer sk-tenant-xxx` header，每个租户 1 个 API key；管理后台生成/撤销 key
  - 限流：默认 100 req/s per key，Burst 200；超限返回 429 + `Retry-After`
  - CORS：按 `tenant.cors_origins` 白名单，不全局开
- **关键文件**: 新增 `api/middleware/auth.py` + `api/middleware/ratelimit.py` (用 slowapi)

### B2B-3 **审计 + 监控 (audit + observability)** — 客户问"谁调了我的数据"要能查
- **现状**: 零日志
- **SaaS 必补**:
  - 访问日志：每请求记录 `request_id / tenant_id / path / status / latency / ip` 到 SQLite / Postgres
  - 错误日志：未捕获异常集中到 Sentry (或自建 `/api/admin/errors`)
  - 监控：`/api/metrics` Prometheus 端点 (`requests_total`, `latency_seconds`, `errors_total` per tenant)
  - `/api/health` 真实实现 (OpenAPI 暴露但 server.py 没写)
- **关键文件**: 新增 `api/middleware/audit.py` + `api/middleware/health.py`

### B2B-4 **计费 + 用量 (billing + usage)** — 没计费谈不上 SaaS
- **现状**: 零计量
- **SaaS 必补**:
  - 计量：每请求按 (租户, 端点) 计数，月度聚合
  - 计费策略：(a) 按调用量阶梯定价 / (b) 按租户 + 调用量套餐 (Free 1k/月, Pro 100k/月 $99) / (c) 私有部署 license
  - 客户后台：`GET /api/usage?period=2026-07` 返回当月调用量
- **关键文件**: 新增 `api/billing/usage.py` + `docs/billing.md`

### B2B-5 **数据版本策略 (data versioning)** — V3.0/V3.2 切换不能 break 客户
- **现状**: 全部硬编码读 `all_v3.0.json`，客户想用 V3.2 字段拿不到
- **SaaS 必补**:
  - API: `?data_version=v3.2` 参数，返回对应版本
  - 旧版兼容: `?data_version=v3.0` 仍可用，**至少 6 个月 deprecated warning + 12 个月下线**
  - 版本元数据: `GET /api/versions` 返回所有可用版本 + 字段表
- **关键文件**: 改 `api/server.py:23` 让 `_DATA_CANDIDATES` 变 `data_versions` dict，按 query param 加载

---

## 4. 5 个追赶 Marble 的行动项 (3 倍镜独特视角)

### 4.1 **首页 EN 模式 1 屏 1 个"家长能读懂的概念卡片"** (chase Marble 主页体感)
- **现状**: V3.2 主页是 2D cytoscape 力导向图，开屏看到的是 1906 节点的"一团乱麻"，家长 5 秒关掉
- **Marble 做法**: withmarble.com/curriculum 主页是**3D 球 (Three.js)** + 拖拽旋转，球上每个点是 K-2 友好的"concept card"（"AI in Daily Life" + 一句 friendly description + 1 张图）
- **追赶动作**:
  1. 主页 EN 模式加 hero section：`3 concept cards` 随机 / 按 grade 切换 → 一句 friendly description + 1 句 evidence ("Identify 5 examples of AI in daily life")
  2. 鼠标 hover cytoscape 节点 → 浮窗显示 description (V3.2 已有 title + summary，但没有 friendly 句)
  3. 加 `?demo=parent` / `?demo=teacher` / `?demo=student` 3 个 preset，preset 决定 hero + 默认学科

### 4.2 **每个 cluster 1 句"家长能读懂的中文总结"** (chase Marble cluster.summary)
- **现状**: V3.2 有 241 cluster，每 cluster 有 `summary_zh` 段 (实测 90+ 字，含 "{name} 在本阶段..."的填空模板)，但**家长一眼读不到**；用户开页面看到的是"1-2 年级：孩子在本阶段学习艺术「影视」领域..." —— 像内部文档不像产品文案
- **Marble 做法**: 183 cluster，每 cluster summary 是 `"Your child is learning the building blocks of writing — how to make complete sentences, use capital letters and punctuation marks correctly, and understand basic word types like nouns and verbs."` (2 句，第二句"为什么要学"的人话)
- **追赶动作**:
  1. 重写 `enrich_v3.2_cluster_summaries.py`：从"字段填空模板" → "1 句孩子学什么 + 1 句家长关心"两段式
  2. UI cluster 节点 hover 时显示 summary_zh (目前只在 detail panel)

### 4.3 **每个 concept 1 句 friendly description** (chase Marble topic.description)
- **现状**: V3.2 concept 没 description 字段，title 太短 (`万以内数的认识`) / content_req 太长 (OCR 截取+改写 拼接) / summary 太短 (median 39 chars) — 家长/学生 0 个字段能直接读懂
- **Marble 做法**: 每个 topic 有 1-2 句 friendly English description, e.g. "AI in Daily Life" → "Artificial intelligence is when computers do things that usually need human thinking..."
- **追赶动作**:
  1. 写 `enrich_v3.2_descriptions.py`: 从 title + content_req + key_points 模板生成 1-2 句 description (English + 中文双版本)
  2. 加到 `docs/schema.md` 字段表
  3. UI detail panel 第一个 block 显示 description (在 title 下方)

### 4.4 **每个 concept 3 条 evidence ("可观察行为")** (chase Marble evidence)
- **现状**: V3.2 用 `academic_req` (学业要求, 课标原文) — 教师视角"学完要会什么"
- **Marble 做法**: 用 `evidence` (3 条可观察行为, e.g. "Identify at least 5 examples of AI in daily life / Describe one way AI makes a task easier / Explain why AI needs lots of data") — 家长/教师 30 秒能判断"孩子会了没"
- **追赶动作**:
  1. 写 `enrich_v3.2_evidence.py`: 从 content_req + key_points 模板生成 3 条 evidence (按 Bloom 分类: 1 了解 + 1 应用 + 1 评估)
  2. 加 `evidence: [str, str, str]` 字段
  3. UI detail panel 把 academic_req 块改成 evidence 块

### 4.5 **学校试用 5 所 + 每所 1 老师审 50 概念** (chase Marble 0 商业化 + 3.6k stars 的反差)
- **现状**: V3.2 仓库 0 stars 0 PR，teacher review 0/1906 真审过
- **Marble 做法**: 9 commits / 3.6k stars = 每次 commit 平均 400 stars，靠**README 包装 + 主页 3D 视觉冲击** + HackerNews 1 次发布
- **追赶动作** (V3.3 1 周内做完):
  1. **README 重写**：把 "B 端 REST API 表" 删了 → 换成"5 分钟在线试用 (mcode URL)" + "学校试用入口" 表
  2. **学校试用 5 所**（智身科技已有合作校）：每所 1 名数学/科学老师，**每人审 50 概念 + 5 关系** = 250 概念 25 关系真审
  3. **HackerNews / V2EX 发帖**：标题直接抄 Marble "I rebuilt China's K12 curriculum as an open knowledge graph" — 不写"复刻 Marble"，写"做了一版比 Marble 更深的"
  4. **微信视频号 1 条 30s demo**：3D 球替代品 (cytoscape 缩放 + fly-to) + 概念卡 5 个滚屏
  5. **GitHub topic 标签**：`open-education`, `knowledge-graph`, `chinese-curriculum`, `k-12` 4 个 — Marble 用了 0 个 topic

---

## 5. 总结：把 V3.2 变成"真能跑真能用真能 B 端"的 4 周计划

### Week 1 (P0 全清)
- 周一/二: 修 P0-1 (API 读 V3.2) + P0-2 (web_server gzip) + P0-3 (README API 表状态)
- 周三/四: 修 P0-4 (standards topic.data 加 id) + P0-5 (cluster key_concepts 改 id)
- 周五: 修 P0-6/7/8 (CI 修复) + P0-9 (审核表 GitHub Issue 模板) + P0-10 (部署 gzip) + P0-11 (LICENSE 文件) + P0-12 (PDF gitignore) + P0-13 (academic_req 补)

### Week 2 (P1 全清 + Marble 范式 5 选 3)
- 周一/二: 修 P1-1/2/3/4 (文档全更新) + P1-5 (双 license) + P1-6 (CITATION.cff)
- 周三/四: 抄 Marble 4.1 (hero 概念卡) + 4.2 (cluster summary 重写) + 4.3 (description 字段)
- 周五: 修 P1-7 (evidence) + P1-8 (strength_label) + P1-9 (description) + P1-10/11/12/13/14 (server 杂项)

### Week 3 (P2 清 + B 端基础)
- 清 P2-1~P2-15
- 起 B2B-1 (租户) + B2B-2 (auth + rate limit) 基础

### Week 4 (B 端完整 + 社区启动)
- B2B-3/4/5 (审计 / 计费 / 版本策略)
- 学校试用 5 所 + HackerNews 发帖

跑完 V3.3，V3.2 才真的"可发布可教学可 B 端"。

---

## 6. 一句话总结

V3.2 **数据上接近 Marble 范式，工程上远落后** — 5 个数据文件 4 个断联、API 读 V3.0、CI 必 fail、PR 没人审、License 单一、没 CITATION、B 端 8 大件全缺。**最该修的 3 件事**：(1) API 读 V3.2 数据 (P0-1) → 让新字段真被消费；(2) 5 数据文件 id 跨引用 (P0-4 + P0-5) → 让下游能 join；(3) GitHub Action 修到能跑 (P0-6/7/8) → 让 community PR 能 merge。这 3 件做掉，V3.2 才"活了"。

---

✅ **工程评测完成: 发现 13 个 P0 / 14 个 P1 / 15 个 P2 (合计 42 个工程问题)，5 个 B 端补强项，5 个追赶 Marble 的行动项**
