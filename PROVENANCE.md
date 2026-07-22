# 数据来源声明 (PROVENANCE)

> Open Curriculum CN V3.2 — 数据来源、license、textIncluded 状态
> 2026-07-22 生成

## 一手数据源 (Primary Sources)

| Slug | Country | Name | Version | Publisher | License | textIncluded |
|---|---|---|---|---|---|:---:|
| cn-compulsory-2022 | CN | 义务教育课程方案和课程标准 | 2022 年版 | 人民教育出版社 | 公开出版物 | ✅ |

来源 URL: https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html

## 二次加工 (Derived Data)

| 文件 | 描述 | 来源 |
|---|---|---|
| data/graph/all_v3.2.json | 知识图谱 (1906 概念 + 4736 关系) | 14 学科 OCR + 人工 enrich |
| data/graph/clusters.json | 241 域聚类 + 人话 summary | 自动聚类 + 模板生成 |
| data/graph/curriculum-standards.json | 课标结构化 (1 框架 × 1906 topics) | all_v3.2.json 字段重组 |

## 自动化流程 (Pipeline)

- **PDF 采集**: `src/extract/download_curricula.py` — 17 本课标 PDF (人教社)
- **OCR 解析**: `tesseract 5.5.2` (chi_sim + eng) @ 180 DPI
- **概念抽取**: `src/pipeline/extract_subjects_v0.6.py` (14 学科按领域拆分)
- **Enrich (三层 fallback)**: `src/pipeline/enrich_subject.py` — content_req / academic_req / bloom / key_points / estimated_minutes
- **关系抽取**: `src/pipeline/expand_relations.py` — prerequisite (学段前向) + progresses_to (学段后向) + relates_to (跨学科)
- **Reason 填充**: `src/pipeline/enrich_v3.2_edge_reasons.py` — 4 维模板 + 跨学科 bridge 字典
- **Cluster summary**: `src/pipeline/enrich_v3.2_cluster_summaries.py` — 14 学科 × 4 阶段 × ~10 领域
- **Assessment prompt**: `src/pipeline/enrich_v3.2_assessment.py` — 14 学科模板 + bloom 分类

## License

- **数据库 (all_v3.2.json)**: CC-BY-SA 4.0
- **课标原文 (curriculum-standards.json)**: 中华人民共和国教育部 2022 — 公开出版物
- **AI 生成内容 (cluster summary / edge reason / assessment prompt)**: CC-BY-SA 4.0 (本项目)
- **代码 (src/, web/, api/)**: CC-BY-SA 4.0 (本项目)

## 排除说明 (Excluded)

V3.2 全量, 无排除。
- 早期 V0-V2 各版本 (仅做历史保留, 不进入主图)
- 未填字段 (academic_req V3.0 仅 13.7%, 其余概念为 V3.0 后期新加, 未 enrich academic_req)
