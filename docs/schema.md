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

## 版本

- v1.0 (2026-07-22): 初始 schema
