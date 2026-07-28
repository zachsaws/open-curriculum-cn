# 数据来源声明 (PROVENANCE)

> Open Curriculum CN V4.0.1 — 数据来源、license、textIncluded 状态
> 2026-07-28 更新

## 一手数据源 (Primary Sources)

| Slug | Country | Name | Version | Publisher | License | textIncluded |
|---|---|---|---|---|---|:---:|
| cn-compulsory-2022 | CN | 义务教育课程方案和课程标准 | 2022 年版 | 人民教育出版社 | 公开出版物 | ✅ |

来源 URL: https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html

## 二次加工 (Derived Data)

| 文件 | 描述 | 来源 |
|---|---|---|
| data/graph/all_v3.7_p1.json | 知识图谱 (1906 概念 + 4736 关系) - V3.7 P1 final | 14 学科 OCR + LLM enrich (100% 完整度) |
| data/graph/clusters.json | 241 域聚类 + 人话 summary | 自动聚类 + 模板生成 |
| data/graph/curriculum-standards.json | 课标结构化 (1 框架 × 1906 topics) | all_v3.7_p1.json 字段重组 |
| data/exercises/exercises_v1.json | 题目库 (~9,500+ 题) | LLM 自动 (5 道题/概念) + 8 道经典常考手动入库 |

## 自动化流程 (Pipeline)

- **PDF 采集**: `src/extract/download_curricula.py` — 17 本课标 PDF (人教社)
- **OCR 解析**: `tesseract 5.5.2` (chi_sim + eng) @ 180 DPI
- **概念抽取**: `src/pipeline/extract_subjects_v0.6.py` (14 学科按领域拆分)
- **Enrich (三层 fallback)**: `src/pipeline/enrich_subject.py` — content_req / academic_req / bloom / key_points / estimated_minutes
- **关系抽取**: `src/pipeline/expand_relations.py` — prerequisite (学段前向) + progresses_to (学段后向) + relates_to (跨学科)
- **Reason 填充**: `src/pipeline/enrich_v3.2_edge_reasons.py` — 4 维模板 + 跨学科 bridge 字典
- **Cluster summary**: `src/pipeline/enrich_v3.2_cluster_summaries.py` — 14 学科 × 4 阶段 × ~10 领域
- **Assessment prompt**: `src/pipeline/enrich_v3.2_assessment.py` — 14 学科模板 + bloom 分类
- **V3.7 P0 (academic_req + key_points)**: `data/build/build_p0.py` — LLM 串行补 14 学科 100%
- **V3.7 P1 (teaching_voice)**: `data/build/build_p1.py` — LLM 串行生成老师口吻 3 句话
- **V3.7 P3 (audit CI)**: `.github/workflows/audit.yml` — 每次 push/PR 跑 audit + 覆盖率红线
- **V4.0.1 P2 (题目库)**: `data/build/build_p2.py` — 5 道题/概念互补设计 (T1 选/T2 填/T3 简/T4 应用/T5 综合) + Bloom 全覆盖
- **V4.0.1 真题试点**: `data/build/add_real_exams.py` — 8 道经典常考手动入库 (math 3 核心考点)

## License

- **数据库 (all_v3.7_p1.json)**: CC-BY-SA 4.0
- **课标原文 (curriculum-standards.json)**: 中华人民共和国教育部 2022 — 公开出版物
- **AI 生成内容 (cluster summary / edge reason / assessment prompt / teaching_voice / 题目库)**: CC-BY-SA 4.0 (本项目)
- **代码 (src/, web/, api/, data/build/)**: CC-BY-SA 4.0 (本项目)

## 题目库说明 (V4.0.1 新增)

- **LLM 自动生成** (~9,500+ 道)：基于 all_v3.7_p1.json 的概念元数据 (description / key_points / teaching_voice) 生成 5 道题/概念互补设计 (T1 选 / T2 填 / T3 简 / T4 应用真题风 / T5 综合压轴)
- **手动入库** (8 道)：math 3 个核心考点 (勾股定理/一元二次方程/二次函数) 经典常考题，标记 `is_real_exam=true`
- **真真题说明**：中国中考真题版权分散，公开带答案的完整题库难找。手动入库的 8 道是"经典常考题型"而非具体某省某年的真题。后续将探索与出版社/教辅机构合作获取正版授权。

## 排除说明 (Excluded)

V4.0.1 全量, 无排除。
- 早期 V0-V3.6 各版本 (仅做历史保留, 不进入主图)
