# Marble (v1, 2026-07-08) vs V3.1 (2026-07-22) — 全面对比评测

> Marble 数据来源: https://github.com/withmarbleapp/os-taxonomy (Initial release 2026-07-08)
> V3.1 数据来源: 本项目 `data/graph/all_v3.0.json` + 公网 https://7s3jrfv6hekuu.space.mcode.cn

## 1. 整体规模对比

| 维度 | Marble v1 | V3.1 | 差距 | 评价 |
|---|---:|---:|---|---|
| 概念数 | 1,590 | **1,906** | +316 (+19.9%) | ✅ 超出 |
| 关系数 | 3,221 | **4,736** | +1,515 (+47%) | ✅ 超出 |
| 学段 | K-2 (5-11 岁) | G1-G9 (6-15 岁) | 国内多 3 段 | ✅ 超出 |
| 学科数 | 8 | 14 | +6 | ✅ 超出 |
| 域聚类 (cluster) | 183 | **0** | -183 | ❌ **大缺** |
| 课标框架数 | 7 | 1 (中国 2022 义教) | 国际 vs 国内 | ⚠️ 范围不同 |
| License | ODbL-1.0 + CC-BY-SA 4.0 | CC-BY-SA 4.0 | 单一 | ⚠️ 严谨性 |

## 2. 概念 (Topic) 字段对比

| 字段 | Marble v1 | V3.1 | 差距 | 严重度 |
|---|---|---|---|---|
| `id` | `mt_xxx` 短码 | `M_G1_NS_01` 含学科+学段+域 | ⚠️ V3.1 更结构化但更长 | P2 |
| `type` | CONCEPTUAL / (可能还有 PROCEDURAL 等) | 无 | ❌ 缺类型分类 | **P1** |
| `subject` | "Computing" 等 (首字母大写) | "info_tech" snake_case | ⚠️ 命名风格不同 | P2 |
| `domain` | "Artificial Intelligence" 完整英文名 | "数与运算" 中文 | ✅ 中文用户友好 | — |
| `name` | "AI in Daily Life" | "万以内数的认识" | ✅ 等价 | — |
| `description` | 1-2 句 friendly English (家长能读懂) | 无独立 description 字段 (title 承担) | ⚠️ 部分 | P2 |
| `ageRangeStart`/`End` | age 5-11 | `grade_start`/`grade_end` 1-9 | ⚠️ 缺 age 映射 | **P1** |
| `centrality` | 0.0274 (graph metric) | 无 | ❌ 缺中心度 | **P1** |
| `evidence` | **3 条可观察行为** (e.g. "Identify at least 5 examples of AI...") | `academic_req` (学业要求, 类似但来自课标) | ⚠️ orientation 不同 | P2 |
| `assessmentPrompt` | **"Could {{name}} point out several things..." 模板** | 无 | ❌ **完全缺** | **P0** |
| `standards` | 课标对齐数组 | `src_page` 字段 | ⚠️ V3.1 简单化 | P1 |

## 3. 关系 (Dependency) 字段对比

| 字段 | Marble v1 | V3.1 | 差距 | 严重度 |
|---|---|---|---|---|
| `topicId` | ✓ | `to` | ✅ 等价 | — |
| `prerequisiteId` | ✓ | `from` | ✅ 等价 | — |
| `strength` | **"hard" / "soft"** (必填) | `weight` 0.5/0.8/1.0 | ⚠️ V3.1 数值化但没映射 hard/soft | P2 |
| `reason` | **人话必填** (e.g. "Must understand vibrations make sound before finding volume patterns") | **0% 填充** | ❌ **核心价值缺失** | **P0** |

**关系 reason 缺失**是 V3.1 最大的差距。Marble 把"为什么这两个概念有这个先决关系"写成人话，是知识图谱从"一堆节点和线"变成"可理解的知识"的关键。

## 4. Cluster (域聚类) — V3.1 完全没有

| 字段 | Marble v1 | V3.1 |
|---|---|---|
| `subject` | "English" | — |
| `domain` | "Grammar & Punctuation" | — |
| `ageRangeStart` | 5 (K) | — |
| `summary` | **"Your child is learning the building blocks of writing — how to make complete sentences, use capital letters and punctuation marks correctly, and understand basic word types like nouns and verbs."** (家长友好的总结) | — |

**183 域人话总结**，每个年龄段每个领域都有一段 1-3 句的 friendly summary，老师/家长一眼看懂。V3.1 完全没有。

## 5. Curriculum Standards (课标框架) — V3.1 散在节点字段

Marble 把 7 个课标框架独立成文件：
- `slug`: "uk-nc-2013"
- `country`: "GB"
- `name`: "The national curriculum in England: Key stages 1 and 2 framework document"
- `version`: "September 2013"
- `sourceUrl`: PDF URL
- `textIncluded`: true/false
- `license`: 各自的 upstream license
- `topics`: [{ key, code, data: { title, domain, subject, keyStage, description } }]

V3.1 把课标数据散在每个节点的 `src_page` / `src_stage` 字段，**没有独立的课标框架文件**。这是 V3.1 差 Marble 的"严谨性" — Marble 把"数据来源"作为一等公民，V3.1 还在"塞进节点"。

## 6. Manifest + Provenance — V3.1 完全没有

Marble `manifest.json`:
- `dataset` / `taxonomyVersion` / `generatedAt` / `codesOnlySources` / `counts` / `files` / `excluded`

V3.1 没有任何 manifest，docs/progress.md 算半个但不是结构化 JSON。

Marble 有 `PROVENANCE.md` 单独写清楚每个课标的来源、license、textIncluded 状态。V3.1 散在 docs。

## 7. UI / 可视化对比

| 维度 | Marble v1 | V3.1 | 评价 |
|---|---|---|---|
| 主可视化 | **3D 球** (Three.js / WebGL, "Drag to spin") | 2D 力导向 (cytoscape.js) | ⚠️ Marble 视觉冲击强 |
| 概念卡片 | 有 (但 GitHub 看不到前端) | ✅ 有 (完整 8 块) | — |
| 概念地图模式 | 无 (只有 3D 球) | ✅ V3.1 新加 | ✅ V3.1 超出 |
| 树状导航 | 无 | ✅ V3.1 新加 | ✅ V3.1 超出 |
| 键盘快捷键 | 不详 | ✅ 9 个 | ✅ V3.1 超出 |
| i18n (3 语言) | 不详 (主页英文) | ✅ zh-CN/zh-TW/en + 简繁字典 | ✅ V3.1 超出 |
| B 端 REST API | 无 (只 GitHub 数据) | ✅ 7 端点 FastAPI | ✅ V3.1 超出 |
| RSS feed | 不详 | ✅ /rss.xml | ✅ V3.1 超出 |

## 8. 评测结论 — 差项清单（按严重度排序）

| # | 差项 | Marble 怎么做的 | V3.1 现状 | 严重度 |
|---|---|---|---|---|
| 1 | **Edge reason (人话)** | 3221 边每条 1 句话 | 0/4736 边填充 | **P0** |
| 2 | **Cluster summary (域人话)** | 183 域每段 1-3 句 summary | 0 域有 | **P0** |
| 3 | **Assessment prompt 模板** | 1590 概念每条 1 句带 {{name}} | 0 概念有 | **P0** |
| 4 | **Curated standards.json** | 7 框架独立 JSON + code 对齐 | 散在 src_page 字段 | **P0** |
| 5 | Manifest 元数据 | dataset/version/counts/excluded | 无 | **P1** |
| 6 | Provenance 来源声明 | PROVENANCE.md 独立文件 | 散在 docs | **P1** |
| 7 | type 字段 (CONCEPTUAL/PROCEDURAL/...) | type 必填 | 无 type | **P1** |
| 8 | centrality 中心度 | 数值化 | 无 | **P1** |
| 9 | age 映射 (5-11) | ageRangeStart/End | 只有 grade | **P1** |
| 10 | DAG 验证脚本 | "Directed edges of a DAG" | 无验证 | **P1** |
| 11 | 3D 球可视化 | Three.js WebGL | 2D cytoscape | P2 |
| 12 | description 字段 | 1-2 句 friendly | 无独立 | P2 |
| 13 | evidence orientation | "可观察行为" (3 条) | "学业要求" (课标) | P2 |
| 14 | 多 license | ODbL-1.0 + CC-BY-SA 4.0 | 单一 CC-BY-SA 4.0 | P2 |
| 15 | strength → hard/soft 映射 | hard/soft 二值 | 0.5/0.8/1.0 数值 | P2 |

## 9. 路线图

### V3.2 (P0 必修, 1-2 天)
- **Edge reason 100% 填充**：写一个 `enrich_relations.py` 给 4736 边自动生成 reason（基于 from→to 的 domain 关系模板）
- **Cluster summary 生成**：给每个 (subject, stage, domain) 三元组写一段人话 summary
- **Assessment prompt 模板**：给每个概念加 `assessment_prompt` 字段（带 {{name}} 占位）
- **Curated curriculum-standards.json**：把 14 学科的课标原文结构化成独立 JSON，V3.1 第一阶段先做数学 + 语文两个

### V3.3 (P1 必补, 2-3 天)
- **Manifest + Provenance**：写 `data/manifest.json` + `PROVENANCE.md`
- **type 字段**：conftest 给 1906 概念分类（CONCEPTUAL/PROCEDURAL/FACTUAL）
- **centrality 计算**：用 networkx 计算每个节点的 degree/closeness/betweenness centrality
- **age 字段**：grade → age 映射（grade 1 = 6 岁, grade 6 = 11 岁, grade 9 = 14 岁）
- **DAG 验证**：写 `validate_dag.py` 验证 all_v3.0.json 的边是 DAG（无环）

### V3.4 (P2 可选, 3-5 天)
- 3D 球可视化 (Three.js)
- description 字段自动生成
- strength → hard/soft 映射
- 多 license 声明 (database ODbL-1.0 + content CC-BY-SA 4.0)

