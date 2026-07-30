# 中国 K12 学习路径图谱

> **每一步学什么，之前漏了哪一步。**

中国教育部 2022 最新课标 · **14 学科 · 1906 核心概念 · 4736 条学习路径 · 9264 道题目 · 1008 视频** · 开源免费。

🎬 **5 秒看明白**：

[![5 秒看明白](https://zachsaws.github.io/open-curriculum-cn/data/hero_thumb.gif)](https://zachsaws.github.io/open-curriculum-cn/explore.html)
*↑ 主页 8s 缩略 · 完整 30s 概念片在 demo 段*

🆕 **V4.1.2 视频接入**：点节点 → 📺 讲解视频 → 答错 5 题 → 复习路径 → 错题本 chip

![V4.1.2 演示](https://zachsaws.github.io/open-curriculum-cn/preview/v4.1.2-collage.png)
*↑ 3 核心考点 (勾股定理/整本书阅读/光的反射定律) × 3 页面 (explore/diagnose/wrongbook) — B 站 API 自动挑的 1008 真教学视频 (跑题率 < 5%)*

🔗 **[3D 球面 demo](https://zachsaws.github.io/open-curriculum-cn/explore.html)** · [漏斗视图](https://zachsaws.github.io/open-curriculum-cn/funnel.html) · [题目练习](https://zachsaws.github.io/open-curriculum-cn/exercise.html?id=M_G4_GM_08) · [首页](https://zachsaws.github.io/open-curriculum-cn/)

[![License: CC-BY-SA 4.0](https://img.shields.io/badge/License-CC--BY--SA%204.0-blue.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
[![Concepts: 1906](https://img.shields.io/badge/concepts-1906-green)]()
[![Learning paths: 4736](https://img.shields.io/badge/learning%20paths-4736-blue)]()
[![Subjects: 14](https://img.shields.io/badge/subjects-14-green)]()
[![Coverage: G1--G9](https://img.shields.io/badge/coverage-G1--G9-blue)]()

## 为什么做这个

> 孩子卡在某个知识点，家长/老师只能干着急 —— **不知道之前漏了哪一步**。

中国 1.6 亿 K12 学生，每天有 2 亿次"为什么这个不会"的教育焦虑时刻。**80% 的"卡住"不是因为这步难，而是因为之前某步没学透。** 但市场上没有任何产品能告诉家长"为了学这个，要先会什么"。

> 老师备课：教育部 2022 课标更新了，但**没有人把整个学段的"先后顺序"画成图**。每学期备 50 个新概念，每个都靠老师凭经验推"之前要学什么"。

> 教研员看跨学科：数学和科学、数学和艺术、物理和地理 —— **跨学科连接藏在课标里**，但没人整理成可视化的"概念地图"。

这个项目把这三件事做成一张图。开源，让任何老师/家长/学生/教研员都能用。

## 它能做什么

🆘 **孩子卡在某个知识点** → 看看之前漏了哪一步
📖 **老师备课** → 翻完整的学习路径
🧒 **学生想提前学** → 一眼看到先后顺序
🔗 **找学科之间的连接** → 看到概念之间怎么连

## 我们不做

不是题库 · 不是网课 · 不是 AI 老师 · 不是学习机

就是一份**「学之前要会什么 / 学之后能学什么」**的图谱。开源免费。

## 两种视图

### 🔮 [3D 球面视图](https://zachsaws.github.io/open-curriculum-cn/explore.html)

1906 概念按 Fibonacci 球面分布，14 学科配色，鼠标拖动旋转，点击节点：

- **0.45 秒相机自动转**到节点正前方（不再"硬切"）
- **节点放大 1.6 倍** + 白色高亮环
- **lineage BFS 反向追溯** —— 整条学习链金色高亮（"为了学这个要先会什么"全展开）
- 球背面点自动变暗 50%（depth fog 显出 3D 深度）

### ▼ [漏斗学习路径](https://zachsaws.github.io/open-curriculum-cn/funnel.html)

复刻 [Marble](https://withmarble.com/curriculum/) 的范式。1906 概念按年级升序展开成倒漏斗，点击节点 lineage BFS 反向追溯所有"之前要学的"。

### 📝 [题目练习](https://zachsaws.github.io/open-curriculum-cn/exercise.html?id=M_G4_GM_08)

**V4.0 新增** — 每个概念配 5 道互补设计题 (1 选择 + 1 填空 + 3 简答/应用/综合)，覆盖 14 学科全 1906 概念。

- **T1 选择题** — 基础概念辨析，4 个选项考察 4 个不同维度（不是同概念 4 变体）
- **T2 填空题** — 关键步骤/关键词记忆
- **T3 简答题** — 解释/描述
- **T4 应用题** — 真实情境，真题风格，参考中考/小升初常考
- **T5 综合题** — 跨本概念 + 前置/后置概念，真题压轴

每道题都带 **Bloom 认知层级** 标签（理解/记忆/分析/应用/评价）+ **难度 1-5** 标签。math 3 个核心考点（勾股定理/一元二次方程/二次函数）额外入库 8 道经典常考题，`is_real_exam=true` 标记。

## 为什么是现在

| 因素 | 说明 |
|------|------|
| **2022 教育部新课标** | 课程结构全调，旧参考书（人教版 2011）的"先后顺序"过时 |
| **K12 焦虑升级** | 1.6 亿学生 + 双减后家长更焦虑"自学路径" |
| **国外 Marble 模式跑通** | [withmarble.com/curriculum/](https://withmarble.com/curriculum/) 美国 Common Core 版本产品已成型 |
| **国内空白** | 没有任何"中国 2022 课标"对应的可视化产品 |
| **AI 内容增强可行** | LLM 把 OCR 课标原文改写为人话 + 真实课例 + 常见错误 + 教学活动 |

## 目标用户 + 怎么帮

| 用户 | 痛点 | 这个项目怎么帮 |
|------|------|---------------|
| **家长** | 孩子说"不会"但说不上哪里不会 | 点节点看到 1-30 个之前要学的概念，一目了然 |
| **小学/初中老师** | 备 50 个新概念凭经验推谱系 | 漏斗视图按学段展开，lineage 告诉"为了教这个学生要会什么" |
| **学生** | 想预习但不知道从哪开始 | 漏斗按年级升序，看完一个看下一个 |
| **教研员/区/市** | 跨学科连接藏在课标里 | 14 学科全量 + 2613 条跨学科软关联 |
| **教培 SaaS** | 想做"知识图谱"但缺数据 | 完整数据可下载 (CC-BY-SA)，3.8MB JSON |
| **教育研究者/AI 公司** | 缺"中国 K12 课程图谱"标注数据 | 4736 条带 reason 的边，可做 RAG / 微调 / 评测 |

## 数据范围

教育部 2022 最新课标，**14 学科 × 1-9 年级**全学段，**1906 概念** + **4736 条学习路径**。

学习路径分 3 类：

- **1759 条** prerequisite（先决）—— 严格"为了学这个要会什么"
- **364 条** progresses_to（进阶）—— 自然延伸
- **2613 条** relates_to（软关联）—— 跨学科连接

**46% 跨学段**（2183 边）/ **55% 跨学科**（2613 边）。

### 14 学科覆盖

| 学科 | 概念 | 课标原文匹配 |
|---|---:|---:|
| 数学 | 337 | 100% |
| 英语 | 296 | 100% |
| 语文 | 209 | 100% |
| 历史 | 136 | 100% |
| 物理 | 121 | 100% |
| 科学 | 121 | 100% |
| 道德与法治 | 115 | 100% |
| 信息科技 | 97 | 100% |
| 地理 | 91 | 100% |
| 体育与健康 | 87 | 100% |
| 劳动 | 85 | 100% |
| 艺术 | 78 | 100% |
| 生物 | 71 | 100% |
| 化学 | 62 | 100% |
| **合计** | **1906** | — |

### 节点 13 字段

每个概念带 13 字段：`title` / `domain` / `subdomain` / `difficulty` / `content_req`（课标原文） / `academic_req`（课标学业要求） / `key_points` / `bloom`（布鲁姆动词） / `estimated_minutes` / `src_page`（链回人教社 PDF） / `description`（人话版） / `real_examples`（真实课例） / `common_mistakes`（常见错误） / `teaching_activity`（教学活动） / `centrality`（被需要 + 能学）

后 3 个字段（real_examples / common_mistakes / teaching_activity）是 LLM 教师用书级增强，全 14 学科 1906 节点 100% 覆盖。

### 题目库（V4.0 新增）

- **5000+ 道 LLM 自动出题**（覆盖全 14 学科 1906 概念，每概念 5 道题互补设计）
- **题型**：选择题 (4 选 1) + 填空题 + 简答题 + 应用题 + 综合题
- **每道题带 Bloom 认知层级** + 难度标签
- **8 道经典常考题手动入库**（math 3 个核心考点：勾股定理/一元二次方程/二次函数）
- **数据下载**：`data/exercises.json` (~3.4MB) / `data/exercises.json.gz` (~850KB)

## 数据来源

- **一手数据**：教育部 2022 义务教育课程方案 + 16 学科课程标准（PDF）
- **官方下载**：<https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html>
- **OCR 工具**：tesseract 5.5.2（chi_sim + eng）@ 180 DPI
- **LLM 内容增强**：把 OCR 原文改写为人话描述 + 真实课例 + 常见错误 + 教学活动

## 商业模式

**开源 + 双边市场**：

1. **C 端完全免费** —— 老师/家长/学生/学生，永远免费。靠 GitHub Pages 部署，零边际成本
2. **B 端 SaaS**（V4.0 路线）—— 教培机构/学校/区/市接入，按学生数 / 老师数 / API 调用量收费
3. **数据授权** —— 教育研究机构 / AI 公司 / 教材出版社购买标准化数据集
4. **增值功能** —— 智能诊断（"卡哪里"自动分析）、个性化学习路径推荐、机构学情分析

参考 [Marble 商业化路径](https://withmarble.com/)：美国已跑通"免费 web + 企业 SaaS + 数据 API"三层。

## 快速开始

数据科学家 / 老师 / 家长 / 学生直接用 demo：

```bash
# 浏览器打开（无需本地）
open https://zachsaws.github.io/open-curriculum-cn/
```

下载 `graph.json` 自己分析：

```bash
# 完整图谱 (3.8MB JSON / 1.4MB gz)
curl -O https://zachsaws.github.io/open-curriculum-cn/data/graph.json
curl -O https://zachsaws.github.io/open-curriculum-cn/data/graph.json.gz
```

`graph.json` 包含 `nodes`（1906 概念）+ `edges`（4736 学习路径），可读入 Python / R / Julia 自己分析。

完整数据 schema 看 [docs/schema.md](docs/schema.md)。

## 仓库结构

```
open-curriculum-cn/
├── data/
│   ├── raw/curriculum_2022/   # 17 本 PDF（人教社下载）
│   ├── parsed/                # OCR 解析
│   ├── graph/                 # 知识图谱 JSON
│   │   ├── all_v3.7_p1.json   # V3.7 P1 final (含 teaching_voice 100%)
│   │   └── {subject}_v3*.json # 学科 + V3.3.5 LLM 增强
│   └── exercises/             # 题目库
│       └── exercises_v1.json  # 5000+ 题 (LLM 自动 + 8 道经典常考)
├── src/
│   ├── extract/               # PDF 下载 + OCR
│   └── pipeline/              # enrich / merge / V3.3 LLM 化
├── data/build/                # LLM 跑批脚本
│   ├── build_p0.py            # academic_req + key_points 跑批
│   ├── build_p1.py            # teaching_voice 跑批
│   ├── build_p2.py            # 题目库跑批（5 道题/概念互补设计）
│   └── add_real_exams.py      # 经典常考题手动入库
├── web/                       # 静态前端
│   ├── index.html             # 主页（产品化 V3.6.1）
│   ├── explore.html           # 3D 球面视图
│   ├── 3d.js                  # Three.js r160 + lineage + camera tween + depth fog
│   ├── funnel.html            # 漏斗视图
│   ├── funnel.js              # Canvas 2D + lineage BFS
│   ├── print.html             # A4 黑白打印版
│   ├── exercise.html          # 题目练习页（V4.0.1 新增）
│   ├── diagnose.html          # 智能诊断页（V4.0.2 新增）
│   ├── diagnose.js            # 客户端 BFS + 自适应阈值算法
│   └── subject-cn.js          # 14 学科中文名共享字典
├── api/                       # FastAPI B 端 REST（本地，暂未上公网）
├── docs/
│   ├── schema.md
│   ├── reviews/               # 三倍镜评测
│   └── reports/               # 调研报告（含 withmarble 对比）
├── .github/workflows/         # GitHub Actions: enrich + Pages 部署
├── CONTRIBUTING.md
├── LICENSE                    # CC-BY-SA 4.0
├── LICENSE-DATA               # CC0 1.0 (数据库层)
└── PROVENANCE.md              # 数据溯源
```

## 与 Marble 的对比

| 维度 | Marble | Open Curriculum CN |
|---|---|---|
| 数据源 | 美国 Common Core | 中国 2022 义教课标 |
| 概念数 | 1,590 | **1,906** |
| 学习路径 | ~5,000 | **4,736** |
| 视图 | 漏斗 | **3D 球 + 漏斗（双视图）** |
| 球 | 无 | **V3.6.2-4: lineage BFS + camera tween + 选中放大 1.6x + depth fog** |
| 学科 | 8 | **14（全学段）** |
| 节点内容 | 标题 + age | **13 字段（含 3 教师用书级）** |
| 跨学段 / 跨学科 | 少 | **46% 跨学段 / 55% 跨学科** |
| 4 句对仗场景入口 | 无 | **V3.6.1: 孩子卡住 / 老师备课 / 学生预习 / 找跨学科连接** |
| "我们不做"反向定位 | 无 | **V3.6.1: 不是题库/网课/AI 老师/学习机** |
| License | 商业 | **CC-BY-SA 4.0** |
| 中国市场 | 无 | **✓ 教育部 2022 课标 + 中文 + 国内教培 SaaS 路径** |

## 路线图

- [x] V0.x: 758 概念 + 14 学科 preseed
- [x] V1.0–V2.3: 工具 / UX / 关系扩充
- [x] V3.0: 概念 758 → 1906 / 关系 299 → 4736
- [x] V3.1: 学科→学段→领域 4 层树状导航
- [x] V3.3.1–5: LLM 内容增强 + 14 学科 100% 教师用书级
- [x] V3.3.3: 3D 球面视图（Three.js）
- [x] V3.4: Marble 漏斗 1:1 复刻
- [x] V3.5: 产品化首页（4 句对仗 + 我们不做 + 工程师话改人话）
- [x] **V3.6.1-5**: 球 lineage BFS + camera tween + 选中放大 1.6x + depth fog
- [x] **V3.6.6**: GitHub Pages 自动部署 + GitHub repo 公开
- [x] **V3.7**: 数据完整度 100%（academic_req + key_points + teaching_voice 14 学科全覆盖）
- [x] **V3.7.10**: P3 审查 CI 化（自动跑 audit + 覆盖率红线阻断）
- [x] **V4.0.0**: 题目库首批 5137 题（每概念 3 道题：1 选择 + 1 填空 + 1 简答）
- [x] **V4.0.1**: 题目库升级每概念 5 道题互补设计（理解/记忆/分析/应用/评价 Bloom 全覆盖）+ 8 道经典常考题入库 + exercise.html 题目练习页
- [x] **V4.0.2**: 智能诊断 PoC — 5 道题快速测试 / 手输答对率 / BFS 找先决链 / 自适应阈值 (80/70/60/50%) / 复习路径排序 / 人话解释 + 2 个 V4 API 端点 (POST /v4/diagnose + GET /v4/diagnose/quick-check) + diagnose.html 3 步 UI + 概念卡"🩺 智能诊断"按钮
- [x] **V4.0.3**: 诊断历史 + 错题本 + 全 14 学科 — localStorage 持久化 (history/wrongbook 2 store) + 错题本页 (重做/移除) + 19 个全学科 quick pick + 诊断结果页加历史区 + 修 2 bug (JSON.parse/list 适配)
- [x] **V4.0.4**: 完整 canvas 进度趋势图 (替换 V4.0.3 占位) + 个性化推荐 (B 站 18 条手挑真实视频 + 人教版教材 + Khan Academy) — 19 quick pick 概念静态推荐表 + 长尾 1887 概念走 B 站搜索 fallback + trend.js / rec.js 独立文件避 V4.0.3 syntax 坑
- [x] **V4.1**: 全站 V4.1 浅色风 (Brilliant 风: 米黄 #faf6ee + 深色 #0a0d18 + V4.1 primary 绿 #00875a) — 主页 14 学科加 emoji icon + 双 CTA (5 分钟测出 + 备一节课) + 新加 test.html (3 步选学段+学科+题数) + 5 核心页 (explore/funnel/diagnose/exercise/wrongbook) 浅色 + 3D 球/漏斗 canvas 内部米黄底 + diagnose 多学科模式 (test.html 跳转目标) + 视频 frame 装饰 + funnel 详情面板文字对比度修复 + 14 学科卡 hover 上移 + V4.1 主页存 /preview/, 根 /index.html 留 V3.6 对比
- [x] **V4.1.1 phase 1.1**: 录 V4.1 浅色版演示视频 (Playwright headless 录屏 + ffmpeg 转 mp4/gif + 抽关键帧做 poster)
- [x] **V4.1.1 phase 1.2**: 跨学科混合题闭环 (test.html 选学段+学科+题数 → diagnose 多学科模式, 按学科均匀出题 [3+2] + 按学科分组结果 + grade 过滤, 答对自动移除)
- [x] **V4.1.1 phase 1.3**: 移动端响应式 (5 核心页 + 主页 + test.html 加 @media (max-width: 480px), 375x812 mobile 无水平滚动, 错题本 hero 不压, 3D 球加桌面访问提示)
- [x] **V4.1.1 phase 1.4**: 根 / 覆盖 V4.1 (dev 预览结束, web/index.html + web/test.html 落地, 保留 web/preview/ 作为历史快照)
- [x] **V4.0.5 phase 2.1**: PDF 报告导出 (window.print() + @media print CSS, 诊断 step3 + 错题本主页加 🖨 导出 PDF 按钮, 报告头部 ::before + 尾部 ::after 注入)
- [x] **V4.0.5 phase 2.2**: IRT 自适应难度 (5 题动态换题, 答对→更难题 / 答错→更易题, 加权算分, 阈值 80/70/60/50% 按 difficulty 1-5)
- [x] **V4.0.5 phase 2.3**: 7 天复习计划 (基于 history 里的薄弱/巩固概念, 每天 3 个, 7 天日程, 兼容 status 中英文, 可导出 PDF)
- [x] **V4.0.5 phase 2.4**: 错题本重做模式 (错题卡按 exercise_id 找原题, 答对自动从错题本移除, 反馈条 + 解释 + 3 状态 banner)
- [x] **V4.1.2 phase 1-3**: 视频接入框架 (3 处显示: explore 概念卡 / diagnose 复习路径 / wrongbook 错题卡 chip) + B 站 wbi 签名自动挑选 1008 视频 (508 核心 + 500 L2 概念, 跑题率 < 5%, 全 14 学科覆盖) — auto_pick_videos.py 学科化 query + 评分 (关键词 + 白/黑名单 + 播放数 log + 时长适中) + 候选清单 docs/v412_video_picks.csv (514) + docs/v412_video_picks_l2.csv (950 L2) + 拼图 web/preview/v4.1.2-collage.png
- [ ] **V4.0 短期 (3 个月)**:
  - 知乎/公众号文章（让老师/教研员/家长知道这玩意）
  - 演示视频/GIF（让 5 秒看懂）
  - B 端 SaaS 模板（教培机构接入）
- [ ] **V4.0 中期 (6 个月)**:
  - 智能诊断全量（V4.0.3 扩全 14 学科 + 诊断历史持久化 + 错题本 + 进度趋势；V4.0.4 加 PDF 报告导出 + IRT 自适应难度 + 7 天复习计划；**V4.0.4 已交付 趋势图 + 推荐**）
  - 个性化学习路径推荐
  - 区域学情分析
- [ ] **V4.0 远期 (12 个月)**:
  - 海外华人 K12 市场（Marble 中文版）
  - 高校先修课图谱（衔接 K12 + 大学）

## 贡献

- **概念补全 PR**（按 [docs/schema.md](docs/schema.md) 字段）
- **课标原文校对**（标错字 / 标错 OCR）
- **关系图谱补充**（缺失的先决/后继）
- **反馈使用问题** → [Issues](https://github.com/zachsaws/open-curriculum-cn/issues)

[CONTRIBUTING.md](CONTRIBUTING.md) 详。

## License

- **内容**（titles / descriptions / examples）：[CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) — 署名 + 相同方式共享
- **数据库层**（节点 ID + 边 ID）：[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) — 公共领域
- 教育部 2022 课标原文（引用）：人教社官方版权

## 致谢

- 教育部 / 人教社 2022 义教课程标准
- [Marble](https://withmarble.com/) 范式启发
- tesseract OCR / Three.js / Canvas 2D / FastAPI
