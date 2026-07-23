# V3.3 — V4.0 路线图（按 7 项目顺序迭代）

> **核心原则**: V3.2.2 表面达标（1906 概念 / 4736 边 / 100% 字段）但**内容质量 D+**，
> sub-agent 自评"覆盖率赢了内容输了"。7 项目顺序节奏 = 先打掉最大的"内容"差距，
> 再做"门面"差距。每个项目独立 commit + 自审 + 测试 + 公网验证后才进下一个。

## 总览

| # | 项目 | 工作量 | 关键验收 | 状态 |
|---|---|---|---|---|
| V3.3.1 | 概念内容 LLM 化 | 5-7d | 50 概念抽样，95% 不含模板痕迹 | ⏳ 准备中 |
| V3.3.2 | OCR 跑题清理 | 0.5d | 1052 跑题 kp < 5% | 待 V3.3.1 |
| V3.3.3 | 3D 球可视化 | 3-5d | 球面拖拽流畅（≥30 FPS 1906 节点） | 待 V3.3.2 |
| V3.3.4 | 教师审核 UI | 2-3d | 节点卡内可编辑，提交后写回 review_status | 待 V3.3.3 |
| V3.3.5 | 真实 EN 翻译 | 3-5d | EN 模式 1906 节点无中文残留 | 待 V3.3.4 |
| V3.3.6 | 数据架构分层 | 1d | 4 文件分层（database / content / visualization），独立 license | 待 V3.3.5 |
| V4.0 | GitHub 公开 + 固定域名 | 0.5d | 用户授权 GitHub token 后，推送 + Pages | 待 V3.3.6 |

---

## V3.3.1 — 概念内容 LLM 化（5-7 人天）

**目标**: 把 1906 概念从"OCR 跑题 + 模板填空"升级到"LLM 生成的人话 + 场景"。

**范围**:
1. **description**: 每节点加 `description` 字段（Marble 风格 1-2 句 friendly English/中文，描述"这是什么 + 怎么用"）
2. **assessment_prompt**: 重写 1906 条，模板去掉，具体场景化（"在 X 情境中，{{name}} 能否 Y？"）
3. **edge reason**: 重写 4736 条，去掉 4 套模板，按具体 from→to 写认知跳跃说明
4. **cluster summary**: 重写 241 条 cluster summary，按 (subject, stage, domain) 写人话

**数据流**:
- 输入: 现有 `all_v3.2.json` 节点的 `title` / `content_req` / `domain` / `key_points` / `subject` / `grade_start` / `bloom`
- 输出: `all_v3.3.json` 新增 `description` 字段 + 重写 `reason` / `assessment_prompt` / cluster `summary_zh`

**LLM 资源策略**:
- 用 mavis 自身的 `task` 工具开 sub-agent 并行
- 14 学科 × ~136 概念 = 14 个 sub-agent（按学科拆，每个 sub-agent 串行处理本学科所有概念）
- 每个 sub-agent 调 LLM 4 次/概念（description + assessment + reason× N + summary）
- 预计 14 × 136 × 4 ≈ 7,600 个 LLM call
- mavis 自身有 LLM 配额，不需要外部 API key

**验收**:
- 50 概念抽样，description / assessment / reason / cluster summary 4 个字段 95% 不含：
  - 模板痕迹（"X 的直接基础" / "在数学课上" / "孩子在本阶段学习"）
  - OCR 跑题片段（"了解符号二" / "请解析这些命名" / "在第一学段"）
- 81 旧测试 + 8 新增 v32 测试 + 5 LLM 质量测试全过
- 公网 smoke test 通过
- commit + push + 部署

**风险**:
- LLM call 量大，可能要分 2-3 批次（先 description，再 assessment，再 reason）
- 不同 sub-agent 质量参差，需要 quality gate 抽样验证
- token 上限：mavis sub-agent 2056 token 限制对短生成 OK，但 description 可能会超

**降级方案**:
- 如果 mavis sub-agent 不可用，回退到规则模板 + 更精细的字典（不是 LLM 化）
- LLM 输出质量不达标，fallback 到"LLM 生成 + 人工标记 sample review"

---

## V3.3.2 — OCR 跑题清理（0.5 人天）

**目标**: 清理 1052 个 key_points 跑题片段（"在第一学段..."、"了解符号二..."、"请解析..."），让 cluster summary 自动更准。

**范围**:
- 写 `clean_ocr_residue.py`
- 启发式规则（黑名单 + 长度 + 关键字）：
  - 含 "在第 X 学段"、"教学情境中"、"考试性质"、"请解析"、"中华优秀传统文化"
  - 长度 < 5 字
  - 完全不包含动词
- 跑全部 1906 节点 key_points
- 重新生成 cluster summary（基于清理后的 key_points）

**验收**:
- 1052 跑题 key_points 清理到 < 5%（< 50 条）
- 50 节点抽样，无 OCR 跑题片段
- 31 + 8 测试全过
- 数据集 hash 变化 < 5%（仅删 OCR 跑题，不改其他）

**风险**:
- 误删正常 key_point（启发式规则可能太激进）
- cluster summary 重新生成依赖 clean_ocr_residue 输出

**降级方案**:
- 保守模式：只删"含 OCR 黑名单关键字 + 长度 < 8 字"的
- 加 30 概念人工抽检

---

## V3.3.3 — 3D 球可视化（3-5 人天）

**目标**: 把 2D cytoscape 力导向升级到 Marble 风格的 3D 球（Three.js WebGL），"Drag to spin" + "Scroll to zoom"。

**范围**:
- 引 Three.js（CDN ~600KB gzip）
- 节点按球面 Fibonacci 分布：
  - 学科按经度（14 学科 = 14 个区间）
  - 学段按纬度（4 学段 = 4 个纬度带）
- 拖拽旋转 + 缩放 + 单击展开先决
- 边渲染：球面弧线（great-circle 距离）
- 性能：1906 节点 ≥ 30 FPS
- 力导向 2D 模式保留当 fallback

**验收**:
- 3D 球加载 < 2 秒
- 拖拽 + 缩放流畅（≥ 30 FPS）
- 移动端基本可用（touch drag + pinch zoom）
- 不破坏现有 2D 模式（toggle 切换）
- smoke test：3D 模式可加载 + 节点可点 + 关系可见

**风险**:
- 移动端 3D 性能可能不够（fallback 自动切 2D）
- 弧线渲染可能让图变花（默认 70% 透明）

**降级方案**:
- 用 InstancedMesh 渲染节点（不是每个 node 一个 mesh）
- 弧线 shader 简化

---

## V3.3.4 — 教师审核 UI（2-3 人天）

**目标**: 节点详情卡内嵌可编辑字段，老师/教研员直接在公网页面改 → 写回 `data/audit/{subject}_filled.csv` → CI 跑 `audit_import.py` 合并回节点 `review_status`。

**范围**:
- 卡片内嵌 contenteditable 或 ProseMirror（推荐 ProseMirror，更专业）
- 字段：description / assessment_prompt / content_req / reason（每条边 1 个）
- 提交按钮 → POST `/api/audit/submit` → 写 `data/audit/{subject}_filled.csv`
- 节点 `review_status` 从 `pending` → `audited` (自动 CI)

**验收**:
- 卡片内编辑 5 个字段全部生效
- 提交后节点 `review_status: audited`
- 抽样 1 节点：用户能成功编辑 + 提交 + 看到状态变化
- 30/30 audit filled 流程通过

**风险**:
- CSRF 防护
- 写入冲突（多人同时编辑）

**降级方案**:
- 用 GitHub Issue 模板（避免直接 POST）
- 锁定同一节点 5 分钟

---

## V3.3.5 — 真实 EN 翻译（3-5 人天）

**目标**: EN 模式 1906 节点不再有中文残留。

**范围**:
- 接 NMT API（DeepL / 百度翻译 / Claude）批量翻译 1906 节点 `title`
- 翻译 1000 关键词
- 翻译 cluster summary_en（241 条）
- 人工抽检 50 条校对
- 回填 `title_en` 字段（`tConcept` 优先用这个）

**验收**:
- 抽样 100 概念 EN 模式无中文残留
- 50 条人工校对，翻译质量 OK
- 31 + 8 + 5 测试全过

**风险**:
- NMT 翻译质量（数学/化学专有名词可能翻错）
- 翻译 API 配额

**降级方案**:
- LLM 翻译（Claude/Anthropic），质量高但贵
- 双语 fallback：EN 模式显示 title + title_en，缺 title_en 显示 pinyin

---

## V3.3.6 — 数据架构分层（1 人天）

**目标**: 4 文件分层（database / content / visualization），独立 license，遵循 Marble 范式。

**范围**:
- `data/database/curricula.json` (ODbL 1.0) — 课标框架结构
- `data/database/concepts.json` (ODbL 1.0) — 1906 概念元数据（id/subject/domain/grade/centrality/cluster_id）
- `data/database/edges.json` (ODbL 1.0) — 4736 边结构
- `data/content/descriptions.json` (CC-BY-SA 4.0) — LLM 生成的 description
- `data/content/assessments.json` (CC-BY-SA 4.0) — LLM 生成的 assessment
- `data/content/reasons.json` (CC-BY-SA 4.0) — LLM 生成的 edge reason
- `data/content/summaries.json` (CC-BY-SA 4.0) — cluster summary
- `data/visualization/graph.json` (CC0 1.0) — 给前端用的 aggregate（自动生成）

**验收**:
- 4 个文件可独立下载
- 3 种 license 各自标注
- 5 文件 schema 各自定义（schema/database-concepts.json / schema/content-descriptions.json / ...）
- 31 + 8 + 5 测试全过

**风险**:
- 拆分后下游消费方（API/前端）需要支持多文件
- 文件数量增加，CI 复杂度上升

**降级方案**:
- 保留 `all_v3.3.json` 作为 aggregate 兼容层
- 4 文件只是 source of truth

---

## V4.0 — GitHub 公开 + 固定域名（0.5 人天）

**目标**: 仓库公开，固定域名，停止"每次部署换 mcode 子域"。

**范围**:
- 用户授权 GitHub token
- 推 GitHub 公开仓库 `your-org/open-curriculum-cn`
- 文档站迁到 GitHub Pages
- README 加 live demo 链接（固定 URL）
- Citation.cff 写明数据来源 / license

**验收**:
- GitHub 仓库公开
- GitHub Pages live demo 可访问
- README 链接稳定
- 100+ stars（社区启动信号）

**风险**:
- 用户授权后才能做
- GitHub Pages 国内访问慢

**降级方案**:
- 仓库只公开到 V3.3.6 数据
- live demo 暂用 mcode 链接

---

## 启动顺序与依赖

```
V3.3.1 内容 LLM 化  ──┐
                       ├──>  V3.3.4 教师审核 UI (审核 LLM 化的内容)
V3.3.2 OCR 清理  ──────┘
                       │
                       v
                  V3.3.3 3D 球 (用 V3.3.1 的 description 数据)
                       │
                       v
                  V3.3.5 EN 翻译 (用 V3.3.1 的中文 description)
                       │
                       v
                  V3.3.6 数据分层 (4 文件分离 LLM 化后的内容)
                       │
                       v
                  V4.0 GitHub 公开
```

---

## 整体质量目标

V3.2.2 → V4.0 后：
- 1906 概念全部 LLM 生成人话 description（不是模板/OCR 跑题）
- 4736 边全部具体认知跳跃说明（不是 "X 的直接基础"）
- 241 cluster 全部人话 summary（不是 fallback 模板）
- 3D 球 + 教师审核 + EN 翻译 + 4 文件分层
- 公开 GitHub 仓库 + 固定域名

**vs Marble v1 真实差距**:
- V3.2.2: 覆盖率 100% / 内容 D+
- V4.0: 覆盖率 100% / 内容 B+（仍有人工 review gap，但 8 成以上可商用）
