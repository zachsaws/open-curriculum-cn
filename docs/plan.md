# Open Curriculum CN · 完整计划 (V0.7 → V1.0)

> 基于 2022 新课标的中国 K12 知识图谱开源基础设施
> **核心原则**: 标题级 → 知识库级,每概念要有 content_req / academic_req / key_points / bloom / estimated_minutes / src_page
> **运行模式**: 通用 enrich 框架 + 14 学科 sub-agent 循环 + 每轮自评

---

## 🎯 现状盘点 (2026-07-22 14:10)

### 已完成
- V0.6: 758 概念 + 167 关系 + 14 学科 preseed
- V0.7 (数学): 214 概念加 detail 字段 (content_req/academic_req/key_points/bloom/estimated_minutes/src_page)
- 通用框架: enrich_math_v0.7.py 是模板

### 缺口 (按"知识库级"标准)
1. **13 学科还是标题级** — 只有 summary 字段
2. **数学第四学段 (7-9) OCR 解析覆盖低** — 25.7% 匹配率
3. **缺关键 UX** — 搜索框、缺先决根节点高亮
4. **公网还没看到 V0.7 detail 升级效果** — 数学 214 概念全部上线
5. **没形成循环** — 一次性输出，没有评审→修复→重跑的工程化机制

### 用户反馈 (2026-07-22 13:30)
> "数学你点开里边没有细节,好像只有章节"
> → V0.7 已修数学, 但 13 学科还都是章节级

### 用户决策 (2026-07-22 14:10)
> "排序好,设计一个计划;全部都要做,且都要自行评审,形成 agent 循环工程"
> → 必须排完整计划 + 14 学科全做 + 每轮自评 + 工程化循环

---

## 📅 完整路线 (8 周 → V1.0)

### V0.7.1 — 物理化学生物 (W1 末)
**目标**: 3 学科从标题级升知识库级
**子任务**:
- 写 `enrich_subject.py` 通用框架 (参数化 14 学科)
- 物理 loop: enrich → 自评 → 修复 → 重跑 (≤5 轮)
- 化学 loop
- 生物 loop
- 主 agent 收 3 个 JSON, 合并 V0.7.1
- 部署公网
**验收**: 3 学科 content_req 完整率 ≥ 80%, bloom 提取 100%

### V0.7.2 — 语文英语 (W2 末)
**目标**: 2 大学科 (任务群 × 学段 × 技能)
- 语文 loop
- 英语 loop (任务量最大,启发式上限 383 概念)
- 合并 + 部署
**验收**: 2 学科 content_req 完整率 ≥ 75%, examples 提取 ≥ 30%

### V0.7.3 — 历史地理道法科学 (W3 末)
**目标**: 4 学科 (社会学科 + 科学)
- 历史 loop
- 地理 loop
- 道法 loop
- 科学 loop
- 合并 + 部署
**验收**: 4 学科 content_req 完整率 ≥ 70%

### V0.7.4 — 信息科技艺术体育劳动 (W4 末)
**目标**: 4 学科 (综合素养)
- 信息科技 loop
- 艺术 loop
- 体育 loop
- 劳动 loop
- 合并 + 部署
**验收**: 4 学科 content_req 完整率 ≥ 70%

### V0.8 — UX 工具增强 (W5 末)
**目标**: 搜索 + 高亮
- 节点搜索框 (按 ID/标题/标签模糊搜索)
- 缺先决根节点高亮 (画一个外圈提示"无先决,可从这里学起")
- 选中节点时, 自动展开 1-2 层先决/后继邻居
- 学科过滤时, 自动 zoom 到该学科
- 部署
**验收**: 搜索 < 200ms, 高亮可一眼看到入口概念

### V0.9 — 数学第四学段重做 (W6 末)
**目标**: 数学 7-9 概念从 25.7% 提到 60%+
- 改进 OCR 解析器覆盖 P61+ (第四学段 + 跨学段)
- 手动补 7-9 核心概念 (勾股定理/一元二次方程/二次函数/相似/锐角三角函数) 课标原文
- 数学 + 部署
**验收**: 数学 7-9 段 content_req 完整率 ≥ 60%

### V1.0 — 验证 + 公开 (W7-W8 末)
**目标**: 1:1 复刻 Marble 范式 + 公开
- W7: 抽样 200 概念请 5-10 名老师/教研员审核 (邮件/问卷)
- W7: 修审核反馈的问题
- W8: GitHub 公开仓库 + README (中英)
- W8: CONTRIBUTING.md (贡献指南)
- W8: B 端 API 上线 (教培 SaaS 用)
- W8: 公网主站 + RSS
**验收**: 1+ 老师审核通过, GitHub 50+ stars, 5+ 社区 PR

---

## 🔁 Agent 循环工程 (核心机制)

### 单学科 loop (每个学科 1 个)

```
for 学科 in [physics, chemistry, biology, ...]:
  for round in [1..5]:
    1. PRODUCER (coder agent):
       - 读 OCR + 上一轮 JSON (if any)
       - 跑 enrich_subject.py --subject=学科
       - 输出: data/graph/{subject}_v0.7.json
       - 输出: data/graph/{subject}_review.md (自评报告)

    2. VERIFIER (verifier agent):
       - 读 JSON + review.md
       - 抽样 5 个概念: 查 OCR 原文, 确认 content_req 真在课标
       - 查 content_req 长度: < 10 字 → fail
       - 查 bloom 提取: 空 → fail
       - 查 matched_pct: < 25% → fail (要求修解析器)
       - 查 cross_stage_mismatch: 错配 → fail
       - 输出: VERDICT: PASS/FAIL + 修复建议

    3. if VERDICT == FAIL and round < 5:
       - 回到 1, 把修复建议作为输入
    4. if VERDICT == PASS or round == 5:
       - 主 agent 合并到 all_v0.7.json
       - 退出 loop

### 主 agent (mavis) 负责
- 14 个 sub-agent 启动 (run_in_background)
- 接收每个 loop 的最终 JSON + review
- 合并到 all_v0.7.json
- 重新生成 web/data/graph.json
- 部署公网
- 截图验证
- git commit

### 监控
- 每个 sub-agent 设 1h 超时
- 5 轮还没过 → 标黄, 主 agent 介入
- 任何 1 学科 24h 没更新 → 主 agent 提醒

---

## 📁 通用 enrich_subject.py 设计

```python
# src/pipeline/enrich_subject.py
"""
通用学科 enrich — 把 V0.x preseed 升级为 V0.7 知识库级

输入: data/graph/{subject}_v0.6.json + data/parsed/{N}_{name}_ocr.json
输出: data/graph/{subject}_v0.7.json

每个概念加字段:
- content_req: 课标内容要求原文 (匹配到的) 或 summary fallback
- academic_req: 课标学业要求原文 (匹配到的) 或 None
- examples: 课标'例 N' 引用列表
- key_points: 3-5 个知识要点
- bloom: 布鲁姆分类动词
- estimated_minutes: 学习时间
- src_page: 课标 PDF 页码 (链回人教社)
- review_status: pending / passed / failed
"""
```

### 匹配算法 (3 层 fallback)
1. **精确匹配**: V0.6 title/summary 关键词 + 强 stage 优先 → OCR 原文
2. **段匹配**: 同 (stage, domain) 段所有 OCR 条款合并
3. **宽松匹配**: 仅关键词 + 跨学段

### 自评指标
- `content_req_matched_pct`: content_req 含 OCR 原文的概念 % (目标 ≥ 30%)
- `academic_req_matched_pct`: 同上, 学业要求 (目标 ≥ 30%)
- `bloom_coverage_pct`: bloom 字段非空 (目标 100%)
- `key_points_avg`: 平均要点数 (目标 ≥ 2)
- `cross_stage_mismatch_count`: 跨学段错配 (目标 = 0)

---

## 🎨 Web 渲染升级 (V0.7.5+)

### Detail 面板 (已升级)
- 480px 宽
- 4 个新 block: 📋 内容要求 / 🎯 学业要求 / 💡 知识要点 / 📚 例题
- 标签行: bloom + 难度 + 时间 + 子领域

### 待加 (V0.8)
- 搜索框: 按 ID/标题 模糊搜索, 命中后高亮
- 缺先决根节点: 渲染时给无先决节点加"入口"标记 (圆圈外环)
- 1-2 层邻居展开: 选中节点时自动显示先决/后继
- 学科过滤 + 自动 zoom: 点 chip 时 fly to 学科中心

---

## 📊 关键指标 (每周检查)

| 指标 | 当前 | W1 末 | W4 末 | W8 末 |
|---|---:|---:|---:|---:|
| 概念数 | 758 | 758 | 758 | 800+ |
| 知识库级学科数 | 1 (数学) | 4 (数+理+化+生) | 14 | 14 |
| 平均 content_req 完整率 | 25.7% (数学) | 60% | 75% | 80%+ |
| 公网部署版本 | V0.7 | V0.7.1 | V0.7.4 | V1.0 |
| 老师审核概念数 | 0 | 0 | 0 | 200+ |
| GitHub stars | 0 | 0 | 0 | 50+ |
| 社区 PR | 0 | 0 | 0 | 5+ |

---

## ⚠️ 风险 & 应对

| 风险 | 应对 |
|---|---|
| 14 学科 OCR 颗粒度差异大 (4 学科 12-14 条启发式) | 改用"任务群/主题/学段目标" 抽取策略 (已为道法/艺术/劳动准备) |
| sub-agent 并发太多 / 输出质量不一 | 主 agent 抽样 + 强制自评 5 轮 |
| 用户反馈 detail 还不细 (例题/教辅引用) | V0.8+ 加"教辅引用"层, 标注人教版/北师大版 X 册 Y 页 |
| 老师审核 5-10 人响应慢 | 异步 + 简化问卷 (10 题/学科) |
| 1:1 复刻 Marble 但数据更复杂 (16 学科) | 接受 Marble 是 8 主科我们是 14 学科全段, 颗粒度可比对 |

---

## ✅ 自评清单 (每个 sub-agent 必跑)

```yaml
# data/graph/{subject}_review.yaml
subject: physics
round: 1
verdict: PASS  # or FAIL
metrics:
  total_concepts: 63
  content_req_matched_pct: 45.3  # ≥ 30 必过
  academic_req_matched_pct: 38.1
  bloom_coverage_pct: 100
  key_points_avg: 3.2
  cross_stage_mismatch_count: 0
samples_checked:
  - id: P1_01
    title: 三种物态的基本特征
    content_req: "能描述固态、液态和气态三种物态的基本特征"
    ocr_source: P16
    matched: true
  - id: P4_03
    title: 欧姆定律
    content_req: "理解欧姆定律 I=U/R"
    ocr_source: P53
    matched: true
issues_found:
  - "3 个概念匹配到 G3-4 OCR 但概念本身是 G7-8, 学段错配"
fix_applied:
  - "加强 stage 优先权重 (扣 0.5 分) → 重新匹配 → 错配 0"
next_round_needed: false
```

---

## 🚀 立即启动 (下一步)

1. 写通用 `enrich_subject.py` (主 agent 一次性产出)
2. 启动 3 个 sub-agent: 物理 / 化学 / 生物
3. 每个 loop 跑 5 轮自评
4. 主 agent 汇总
5. V0.7.1 部署

启动命令:
```bash
cd /Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn
source .venv/bin/activate
python src/pipeline/enrich_subject.py --subject physics --round 1
python src/pipeline/enrich_subject.py --subject chemistry --round 1
python src/pipeline/enrich_subject.py --subject biology --round 1
```
