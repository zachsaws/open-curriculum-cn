# 2022 新课标知识图谱 · Open Curriculum CN

> 基于教育部 2022 义务教育课程标准的中国 K12 知识图谱开源基础设施
> 复刻 [Marble](https://withmarble.com/curriculum/) 的范式，但用中国数据，做得比 Marble 更深。

[![License: CC-BY-SA 4.0](https://img.shields.io/badge/License-CC--BY--SA%204.0-blue.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
[![Concepts: 758](https://img.shields.io/badge/concepts-758-green.svg)]()
[![Subjects: 14](https://img.shields.io/badge/subjects-14-green.svg)]()
[![Coverage: G1--G9](https://img.shields.io/badge/coverage-G1--G9-blue.svg)]()

🔗 **在线演示**: [2022 新课标知识图谱](https://ft796n45xf84x.space.mcode.cn)

## 数据范围

- **14 学科** × **1-9 年级** 全学段
- **758 概念** + **167 先决关系** + **12 跨学科软关系**
- **每个概念** 都带 `content_req`（课标内容要求原文）/ `academic_req`（课标学业要求）/ `bloom`（布鲁姆动词）/ `key_points` / `estimated_minutes` / `src_page`（链回人教社 PDF）

| 学科 | 概念 | OCR 匹配 | 完整率 |
|---|---:|---:|---:|
| 数学 | 214 | 100% | 100% |
| 语文 | 75 | 100% | 100% |
| 英语 | 71 | 0%* | 100% |
| 物理 | 63 | 100% | 100% |
| 化学 | 37 | 100% | 100% |
| 生物 | 36 | 100% | 100% |
| 历史 | 43 | 100% | 100% |
| 地理 | 43 | 100% | 100% |
| 道法 | 39 | 100% | 100% |
| 科学 | 41 | 100% | 100% |
| 信息科技 | 28 | 100% | 100% |
| 艺术 | 22 | 100% | 100% |
| 体育 | 25 | 100% | 100% |
| 劳动 | 21 | 100% | 100% |

*英语 OCR 无"内容要求"段标，匹配靠关键词覆盖；其余字段（content_req/academic_req/bloom/key_points）100% 完整。

## 数据来源

- 教育部 2022 义教课程方案 + 16 学科课程标准 (PDF)
- 人教社官方下载: <https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html>
- OCR 工具: `tesseract 5.5.2` (chi_sim + eng) @ 180 DPI

## 快速开始

```bash
git clone https://github.com/your-org/open-curriculum-cn
cd open-curriculum-cn

# 装 Python 依赖
python -m venv .venv
source .venv/bin/activate
pip install aiohttp pymupdf playwright

# 装 tesseract (macOS)
brew install tesseract tesseract-lang

# 跑 enrich (数学 214 概念)
python src/pipeline/enrich_subject.py --subject math --round 1

# 跑全部 14 学科
for s in math chinese english physics chemistry biology history geography morality_law science info_tech art pe_health labor; do
  python src/pipeline/enrich_subject.py --subject $s --round 1
done

# 合并
python src/pipeline/merge_v0.7_all.py

# 本地看
cd web && python -m http.server 8000
# 打开 http://127.0.0.1:8000
```

## B 端 REST API

部署后提供 REST API（详见 `api/server.py`）:

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/concepts` | GET | 列所有概念（支持分页/学科/学段过滤） |
| `/api/concepts/{id}` | GET | 单个概念详情 |
| `/api/subjects` | GET | 学科列表 + 概念数 |
| `/api/path?from=X&to=Y` | GET | 找 X→Y 学习路径 |
| `/api/prerequisites/{id}` | GET | 概念 X 的所有先决链 |
| `/api/stats` | GET | 统计信息 |

### 示例

```bash
# 找一元二次方程详情
curl https://api.open-curriculum.cn/api/concepts/M_G4_QR_05

# 列数学 G7-9 概念
curl 'https://api.open-curriculum.cn/api/concepts?subject=math&stage=4'

# 找"分数"到"一元二次方程"的学习路径
curl 'https://api.open-curriculum.cn/api/path?from=M_G2_NS_05&to=M_G4_QR_05'
```

## 仓库结构

```
open-curriculum-cn/
├── data/
│   ├── raw/curriculum_2022/   # 17 本 PDF (人教社下载)
│   ├── parsed/                # OCR 解析 (17 本 × 9K-120K 字符)
│   └── graph/                 # 知识图谱 JSON (14 学科)
│       ├── all_v0.7.json      # 总图 (758 概念, 167 关系)
│       ├── {subject}_v0.7.json   # 学科 V0.7
│       └── {subject}_review_r1.json  # 自评报告
├── src/
│   ├── extract/               # PDF 下载 + OCR
│   ├── pipeline/              # enrich / merge / scan_ceiling
│   └── validate/              # Playwright 截图
├── web/                       # 静态前端 (cytoscape.js 2D)
│   ├── index.html
│   ├── app.js                 # 工具 (搜索/高亮/邻居展开)
│   ├── cytoscape.min.js
│   └── data/graph.json
├── api/                       # B 端 REST API (FastAPI)
│   ├── server.py
│   └── tests/
├── docs/                      # 设计文档 + 路线图
│   ├── schema.md
│   ├── plan.md
│   ├── progress.md
│   └── roadmap.md
├── .github/
│   └── workflows/             # GitHub Action: PR 触发自动 enrich
└── README.md
```

## 与 Marble 的对比

| 维度 | Marble | Open Curriculum CN |
|---|---|---|
| 数据源 | 美国 Common Core (8 主科) | 中国 2022 义教课标 (14 学科) |
| 概念数 | 1,590 | 758 (持续增长到 ~1800) |
| 学段 | K-12 (13 学段) | G1-G9 (4 学段 × 14 学科) |
| 可视化 | 3D 力导向 (Three.js) | 2D 力导向 (cytoscape.js) |
| 数据详情 | 概念标题 | 概念标题 + 内容要求 + 学业要求 + 知识要点 + 布鲁姆动词 + 学习时间 + 课标页码 |
| License | 商业 | CC-BY-SA 4.0 (开源) |
| 社区 | 商业 | GitHub 公开 PR |

## 路线图

- [x] V0.6: 758 概念, 14 学科 preseed
- [x] V0.7: 14 学科 enrich 到"知识库级"
- [x] V0.8: 工具增强 (搜索/高亮/邻居)
- [x] V0.9: 数学第四学段重做 (P61+ @行格式)
- [x] V1.0: README + CONTRIBUTING + B 端 API (本文档)
- [x] V1.5: GitHub Action 自动 enrich + JSON 验证
- [x] V2.0: 繁体 + 英文 UI (i18n) + RSS feed

## 贡献

参见 [CONTRIBUTING.md](CONTRIBUTING.md)。

我们欢迎:
- 新概念 PR（按 V0.7 字段格式）
- 课标原文校对（标错字 / 标错 OCR）
- 关系图谱补充（缺失的先决/后继）
- 教师审核（请先看 [docs/teacher-review.md](docs/teacher-review.md)）

## License

CC-BY-SA 4.0 — 署名 + 相同方式共享。
允许商用 / 修改 / 再发布，但必须署"Open Curriculum CN 贡献者"且同样开源。

## 致谢

- 教育部 / 人教社 2022 义教课程标准
- [Marble](https://withmarble.com/) 范式启发
- tesseract OCR / cytoscape.js / FastAPI
