# 知识图谱 Schema 定义

## 设计原则

1. **概念（Concept）是最小教学单位**——不是教材章节，不是知识点大类
2. **先决关系（Prerequisite）是有向无环图**——A→B 表示"学 A 之后才能学 B"
3. **每个概念有元数据**——所属学科、学段、起始年级、核心素养、教材版本映射
4. **每条关系有强度（weight 0-1）**——硬先决（必须）vs 软先决（最好）

## Schema

### Concept (节点)

```json
{
  "id": "math-3-frac-equivalence",        // 唯一 ID
  "subject": "math",                       // 学科代码
  "stage": "primary",                      // primary | junior_high
  "grade_start": 3,                        // 起始年级
  "grade_end": 4,                          // 结束年级
  "title": "分数的等价",                   // 中文标题
  "title_en": "Fraction equivalence",      // 英文（可选）
  "domain": "number",                      // 大领域
  "subdomain": "fractions",                // 子领域
  "core_literacy": ["数学抽象", "数学运算"], // 核心素养
  "textbook_versions": ["人教版", "北师大版"],  // 适用教材版本
  "example": "1/2 = 2/4 = 3/6",            // 示例题
  "description": "...",                     // 描述
  "source_refs": ["pep-math-3b-ch3"],       // 出处引用
  "tags": ["分数", "等价", "约分", "通分"],
  "difficulty": 2,                          // 1-5 难度
  "estimated_minutes": 25,                  // 估计学习时间
  "created_at": "2026-07-22T11:30:00Z",
  "updated_at": "2026-07-22T11:30:00Z"
}
```

### Prerequisite Relation (边)

```json
{
  "id": "rel-001",
  "from": "math-1-add-single-digit",      // 前置概念
  "to": "math-1-add-two-digits",          // 后续概念
  "type": "hard",                          // hard | soft
  "weight": 1.0,                           // 0-1
  "rationale": "两位数加法需要一位数加法基础",  // 关系理由
  "source": "2022-math-curriculum",        // 来源
  "confidence": 0.95                       // AI 抽取置信度
}
```

### Exercise (题目) — V4.0 新增

`data/exercises/exercises_v1.json` 包含 ~9,500+ 道题（每概念 5 道 LLM 自动 + N 道真真题）。每道题 schema:

```json
{
  "id": "EX_M_G4_GM_08_001",              // 唯一 ID (EX_<concept_id>_<NNN>)
  "concept_id": "M_G4_GM_08",              // 关联概念
  "type": "multiple_choice",                // multiple_choice | fill_blank | short_answer
  "difficulty": 2,                          // 1-5 难度
  "question": "...",                        // 题干
  "options": ["A. ...", "B. ...", ...],     // 选择题 4 个选项 (仅 multiple_choice)
  "answer": "B",                            // 选择题: "A"|"B"|"C"|"D"; 填空: ["关键词"]; 简答: "参考答案文本"
  "explanation": "...",                     // 解析
  "bloom": "理解",                          // Bloom 认知层级: 记忆|理解|分析|应用|评价
  "is_real_exam": false,                    // 是否真真题 (手动入库时设 true)
  "tags": ["经典题", "常考"]                // 标签 (真真题常有)
}
```

**5 道题槽位互补设计**（V4.0.1 升级）：

| 槽位 | ID 后缀 | 题型 | Bloom | 用途 |
|---|---|---|---|---|
| T1 | `_001` | multiple_choice | 理解 | 基础概念辨析，4 选项考察 4 个不同维度 |
| T2 | `_002` | fill_blank | 记忆 | 关键步骤/关键词记忆 |
| T3 | `_003` | short_answer | 分析 | 解释/描述 |
| T4 | `_004` | short_answer | 应用 | 真实情境，真题风格 |
| T5 | `_005` | short_answer | 评价 | 跨本概念 + 前置/后置概念，真题压轴 |

**真真题高位号**：手动入库的真题用 `_901+`（避开 LLM 槽位），例如 `EX_M_G4_GM_08_901`。

### 学科代码

| code | 中文 | 学段 |
|---|---|---|
| `chinese` | 语文 | 全 |
| `math` | 数学 | 全 |
| `english` | 英语 | 3-9 |
| `science` | 科学 | 1-6（小学科学） |
| `physics` | 物理 | 8-9 |
| `chemistry` | 化学 | 9 |
| `biology` | 生物学 | 7-9 |
| `history` | 历史 | 7-9 |
| `geography` | 地理 | 7-9 |
| `morality_law` | 道德与法治 | 全 |
| `info_tech` | 信息科技 | 3-9 |
| `art` | 艺术 | 全 |
| `pe_health` | 体育与健康 | 全 |
| `labor` | 劳动 | 全 |
| `integrated` | 综合实践活动 | 1-9 |

## 跟 Marble 的字段对齐

| Marble | Open Curriculum CN | 备注 |
|---|---|---|
| `n.t` | `concept.title` | 概念标题 |
| `n.dm` | `concept.domain` | 学科/域 |
| `n.a` | `concept.grade_start` | 起始年龄/年级 |
| `n.q` | `concept.example` | 示例题 |
| `n.col` | 按 domain 自动着色 | 颜色 |
| `n.c` | `concept.difficulty * 节点边数` | 节点大小（复用） |
| `e[0], e[1], e[2]` | `relation.from, relation.to, relation.type` | 边 |
| `groups[]` | `domains[]` | 学科分类 |

### Diagnose (V4.0.2 智能诊断 PoC)

**算法** (客户端 JS + Python API 双实现, 保持一致):

| 输入 | 字段 | 说明 |
|---|---|---|
| 概念 | `concept_id` | 必填, 1906 个概念任选 |
| 5 道题答题 | `answers: [bool]*5` | 主入口, True=对/False=错 |
| 自评答对率 | `score: 0-1` | 副入口, 跟 answers 二选一 |

**输出**:

| 字段 | 类型 | 说明 |
|---|---|---|
| `concept_id` | string | 诊断目标 |
| `concept_title` | string | 概念名 |
| `subject_cn` | string | 学科中文 |
| `difficulty` | int 1-5 | 概念难度 |
| `grade_range` | string | 例 "7-9年级" |
| `score` | float 0-1 | 答对率 |
| `score_pct` | int 0-100 | 答对率 (%) |
| `status` | string | "薄弱" / "巩固" / "已掌握" |
| `weak_threshold` | int | 该难度薄弱线 |
| `consolidate_threshold` | int | 该难度巩固线 |
| `weak_concepts` | array | BFS 先决链 [{id, title, distance, difficulty, subject}, ...] |
| `weak_concepts_count` | int | 先决链总数 |
| `recommend_path` | array | 复习路径 (前 8 个, 按距离+难度排序) |
| `human_explanation` | object | {summary, why, actions[], status_emoji} |

**自适应阈值** (V4.0.2 拍板):

| 难度 | 薄弱线 | 巩固线 | 设计意图 |
|---|---|---|---|
| 1-2 (基础) | 80% | 95% | 简单题答错 1 道就是薄弱 |
| 3 (核心考点) | 70% | 90% | 大部分要会 |
| 4 (拔高) | 60% | 80% | 答对 3/5 已经 OK |
| 5 (压轴) | 50% | 70% | 答对一半算掌握 |

**判分规则**:
- 选择题: 用户选 letter = 正确答案 letter → 对
- 填空题: 模糊匹配 (去标点, 包含/被包含)
- 简答题: 只计"答了没" (字 > 5 算答了)

## 版本

- v1.0 (2026-07-22): 初始 schema
- v1.1 (2026-07-28): V4.0.1 题目库 schema (multiple_choice/fill_blank/short_answer + bloom + is_real_exam)
- v1.2 (2026-07-29): V4.0.2 智能诊断 schema (Diagnose + 自适应阈值)
