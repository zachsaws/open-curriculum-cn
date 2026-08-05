# 更新日志

按版本倒序排列。里程碑版本用粗体标出。

---

## V1.0 · 2026-08-05 · 正式版打包

首次以**正式版**形式发布。本版本没有新功能，专注把现有能力打包成可被介绍、可被搜索、可被信赖的形态。

### 新增
- **CHANGELOG.md** — 更新日志（你正在看的这个）
- **favicon.svg** — 品牌 icon（深绿底 + 黄"课"字）
- **web/404.html** — GitHub Pages 404 兜底页
- **web/privacy.html** — 隐私政策（localStorage / 不上传 / 不卖数据）
- **README.md 重写** — 从"V4.1 介绍"升级为"V1.0 正式版"（路线图标记 [x] 全量校对）
- **主页 SEO 增强** — canonical / og:url / twitter:card / keywords
- **8 个子页加版本 + 反馈** — explore / funnel / diagnose / exercise / wrongbook / test / video-admin / index 顶部右侧
- **反馈通道** — 顶部常驻 💬 反馈按钮（链 GitHub Issues / 邮件 / 微信群 / 班级模式 PoC 计划）

### 修
- 主页 hero 文案从"V4.0 · 2026 课标版"改为"V1.0 · 2026 课标版"
- 故事卡片的"9,259 题"从"V4.0.1"统计更新到 V1.0 真实数据
- README 路线图 V4.0.5 phase 2.x / V4.0.6 / V4.1.2 / V4.1.3 全部标记 [x]

### 本版本核心数据
- 1,906 概念 / 4,736 条学习路径 / 14 学科 / 9 视频数
- 9,264 题（含 13 道经典常考题 + 267 道 AI 改写 + 2,652 道难度校准）
- 1,008 视频（B 站 wbi 自动挑选，跑题率 < 5%）
- 3D 球首屏 3-6 秒（graph_lite 5.5MB / gz 1.7MB）

---

## V4.1.3 · 2026-07-29 · 3D 球性能优化

3D 球面首屏 10-20s → 3-6s，**快了约 4 倍**。

### 新增
- **graph_lite.json** (5.5MB) + **graph_lite.json.gz** (1.7MB) — 24 字段精简版，删 13 个不必要字段
- **data-cache.js 新 API** — `loadGraphLite()` / `loadGraphFull()` / `prefetchFull()`
- **scripts/gen_graph_lite.py** — 一键生成脚本

### 改
- `web/3d.js` `loadData()` 改用 lite + fallback full
- `web/funnel.js` / `web/print.html` 也用 lite（漏斗快 1 倍）
- `web/diagnose.js` / `web/exercise.html` 改用 fetch graph_lite.json

### 修
- 修复 3 个漏字段：real_examples / common_mistakes / teaching_activity 加回 lite（5.5MB）
- 修复 9 个 orphan concept_id（从 git history pre_fix 备份恢复原值）
- 删 3d.js 残留的 [debug] console.log

---

## V4.1.2 · 2026-07-29 · 视频接入

1008 个 B 站真教学视频（508 核心考点 + 500 L2 概念），跑题率 < 5%。

### 新增
- 3 处视频显示：
  - **explore 概念卡** — 节点详情显示 1-3 个讲解视频
  - **diagnose 复习路径** — 薄弱概念推荐视频
  - **wrongbook 错题卡** — 答错后 chip 形式显示视频链接
- **video-admin.html** — 视频入库工具（localStorage 草稿 + 自动复制剪贴板）
- **B 站 wbi 自动挑选** — `api.bilibili.com/x/web-interface/search/all/v2` + wbi 签名
  - 学科化 query（数学 / 语文 / 音体美 / 抽象分别不同）
  - 关键词提取（title 整段 + 滑动窗口）
  - 黑名单 ~200 词 / 白名单 ~50 词 / 播放数 log / 时长适中
  - 候选清单：`docs/v412_video_picks.csv` (514) + `docs/v412_video_picks_l2.csv` (950)
- 拼图预览：`web/preview/v4.1.2-collage.png`

### 学科分布（1008 视频）
- math 234 / chinese 109 / english 114 / physics 77 / chemistry 57 / biology 64
- history 62 / geography 44 / morality 62 / info 60 / science 57 / pe 40 / art 14 / labor 14

### 修
- 修 B 站 412 限速（playwright + 跨会话续跑）
- 修 wbi 库 `result_type` bug
- 删 51 个跑题视频（硬黑名单 v2 + 软跑题 v3）

---

## V4.0.6 · 2026-07-29 · 题目 AI 评估

9,264 题 5 维独立评估，278 high 风险改写 96% 修复率，2,652 题难度全量校准。

### 评估结果
- **99.1%** (9,188/9,264) 评估通过
- 风险分布：low 85.9% / medium 11.1% / high 3.0%
- 5 维问题：难度漂 29% / 答案错 6.1% / 题不清 5.4% / 概念错配 3% / 选项差 1.3%

### 改写结果
- 278 题 high 风险 → 267 题修复 (96%)
  - 235 第一次成功 (84.5%) + 32 retry 成功 (74.4% of 43)
- 9 题 concept_id 改（LLM 判断原错配）
- 235 题 difficulty 重标
- 235 题题面 + 答案 + 解释 重写
- 52 题仍 high → **回滚到 pre_fix 原版**（避免 LLM 改写副作用）

### 难度校准
- 1,754 题 d 字段重新打标（2,652 个 patch）
- 1 worker 串行 10 题/min + sleep 3.5s + 退避
- 净趋势：d=1 题少 325 / d=2/3/4 上升（系统低估修正）

### 报告
- `scripts/audit_poc/REPORT.md` — PoC 50 题
- `scripts/audit_poc/REPORT_fix.md` — 改写 235 题
- `scripts/audit_poc/REPORT_regression.md` — 改写后回归（79% 改善率）
- `scripts/audit_poc/REPORT_perf.md` — 难度校准

### 关键决策
- **4 prompt PoC 选 v1_strict_5d**（5 维独立 + fix_suggestion + overall_risk）
- **批量 3-4 题/请求**（避免 max_tokens 截断）
- **单 worker 串行**（避免 14 学科并发撞 429）
- **art 学科定制 prompt**（接受主观性 + 评分标准 + 难度 Bloom 区分）

---

## V4.1.1 · 2026-07-29 · 移动端 + 跨学科

4 个 phase 全量交付，正式版在桌面 + 移动端都可流畅使用。

### phase 1.1 — 演示视频
- V4.1 浅色版演示视频（Playwright headless + ffmpeg）
- `web/data/diagnose_demo.mp4` + `.gif` + `_poster.png`

### phase 1.2 — 跨学科混合题闭环
- `test.html` 选学段 + 学科（多选） + 题数 → `diagnose.html?test=multi`
- 跨学科模式：按学科均匀出题 [3+2] + 按学科分组结果 + grade 过滤
- 答对自动移除

### phase 1.3 — 移动端响应式
- 5 核心页 + 主页 + test.html 加 `@media (max-width: 480px)`
- 375×812 移动端无水平滚动
- 错题本 hero 不压
- 3D 球加桌面访问提示

### phase 1.4 — 根 / 覆盖 V4.1
- dev 预览结束
- `web/index.html` + `web/test.html` 落地 V4.1
- 保留 `web/preview/` 作为 V3.6 历史快照

---

## V4.1 · 2026-07-29 · 全站浅色风（Brilliant 风）

米黄底 + 深绿 CTA，14 学科 emoji 入口。

### 视觉
- 配色：米黄 #faf6ee + 深色 #0a0d18 + V4.1 primary 绿 #00875a
- 主页 14 学科加 emoji icon（🔢📖🔤⚛️🧪🧬🏛️🌍⚖️🔬💻🎨⚽🛠️）
- 主页双 CTA：5 分钟测出 / 备一节课

### 新增
- **test.html** — 3 步选学段 + 学科 + 题数
- **diagnose.js 多学科模式** — `MULTI_MODE` 状态 + `renderMultiLanding()`

### 改
- 5 核心页浅色（explore / funnel / diagnose / exercise / wrongbook）
- 3D canvas 内部也改浅色（scene.background + edge color）
- 漏斗 2D canvas 米黄底（fillRect 开头 + edge alpha）
- 顶栏半透明渐变（深色 → 浅色）

### dev 预览
- V4.1 存 `web/preview/index.html`，老 V3.6 留 `web/index.html`
- 用户访问 `/` 不受影响
- V4.1 验证完成后根路径切换（V4.1.1 phase 1.4 完成）

---

## V4.0.5 · 2026-07-29 · 4 大功能升级

### phase 2.1 — PDF 报告导出
- `window.print()` + `@media print` CSS
- 诊断 step3 + 错题本主页加 🖨 导出 PDF 按钮
- 报告头部 ::before + 尾部 ::after 注入

### phase 2.2 — IRT 自适应难度
- 5 题动态换题：答对→更难题 / 答错→更易题
- 加权算分
- 阈值 80/70/60/50% 按 difficulty 1-5

### phase 2.3 — 7 天复习计划
- 基于 history 里的薄弱/巩固概念，每天 3 个，7 天日程
- 兼容 status 中英文
- 可导出 PDF

### phase 2.4 — 错题本重做模式
- 错题卡按 exercise_id 找原题
- 答对自动从错题本移除
- 反馈条 + 解释 + 3 状态 banner

---

## V4.0.4 · 2026-07-29 · 趋势图 + 个性化推荐

### 完整 canvas 进度趋势图
- 替换 V4.0.3 占位
- 5+ 次诊断自动激活

### 个性化推荐
- 19 quick pick 概念静态推荐表
- 长尾 1,887 概念走 B 站搜索 fallback
- B 站 18 条手挑真实视频 + 人教版教材 + Khan Academy
- `trend.js` / `rec.js` 独立文件（避 V4.0.3 内嵌字符串 syntax 坑）

---

## V4.0.3 · 2026-07-29 · 诊断历史 + 错题本 + 全 14 学科

### 持久化
- `localStorage` history + wrongbook 2 store（500/1000 容量）
- history 含 status / 答对题数 / 总题数 / 时间戳

### 全 14 学科 quick pick
- math 6 + 其他 13 学科各 1（highest-centrality 选）

### 错题本 web/wrongbook.html
- 重做 / 移除 / 清空
- 4 统计卡
- 错题卡按概念分组

### 修
- ex.options 破损/null 时 JSON.parse() 抛错（try-catch + Array 适配）
- fill_blank answer list 时 .replace() 抛错（toStr 适配 list + Array.some）

---

## V4.0.2 · 2026-07-29 · 智能诊断 PoC

5 道题快速测试 → BFS 找先决链 → 自适应阈值 (80/70/60/50%) → 距离 + 难度排序复习路径 → 3 status 模板人话解释。

### 新增
- 2 V4 API 端点（FastAPI）：
  - `POST /v4/diagnose` — 完整诊断
  - `GET /v4/diagnose/quick-check` — 快速检查
  - X-API-Key 鉴权
- 诊断页 `diagnose.html` — 3 步 UI（选概念 → 5 题测试/手输答对率 → 结果页）
- 概念卡 4 处加 🩺 智能诊断按钮（explore / funnel / 3d.js / funnel.js）

### 客户端
- `diagnose.js` 客户端算法（不依赖后端也能跑）
- BFS 找先决链 + 自适应阈值

---

## V4.0.1 · 2026-07-29 · 题目库升级

每概念 5 道题互补设计（B / M / A / E / C Bloom 全覆盖）。

### 5 题设计
- **T1 选择题** — 基础概念辨析，4 个选项考察 4 个不同维度
- **T2 填空题** — 关键步骤/关键词记忆
- **T3 简答题** — 解释/描述
- **T4 应用题** — 真实情境 + 中考/小升初常考
- **T5 综合题** — 跨本概念 + 前置/后置概念

### 标签
- 每道题带 Bloom 认知层级（理解/记忆/分析/应用/评价）
- 每道题带 difficulty 1-5
- math 3 核心考点额外入库 8 道经典常考题（`is_real_exam=true`）

### 修
- race condition
- 真真题编号策略 `_901+` 高位号

---

## V4.0.0 · 2026-07-29 · 题目库首批

5,137 题（每概念 3 道题：1 选择 + 1 填空 + 1 简答）

### 题型
- 选择题 (4 选 1) + 填空题 + 简答题
- LLM 自动出题

---

## V3.x · 2026 早期

### V3.7.10
- P3 审查 CI 化（自动跑 audit + 覆盖率红线阻断）

### V3.7
- 数据完整度 100%（academic_req + key_points + teaching_voice 14 学科全覆盖）

### V3.6.6
- GitHub Pages 自动部署 + GitHub repo 公开

### V3.6.1-5
- 球 lineage BFS + camera tween + 选中放大 1.6x + depth fog

### V3.6
- 3D 球面视图（Three.js r160）
- 球 lineage BFS（"为了学这个要先会什么"金色高亮）

### V3.5
- 产品化首页（4 句对仗 + 我们不做 + 工程师话改人话）

### V3.4
- Marble 漏斗 1:1 复刻

### V3.3.3-5
- LLM 内容增强 + 14 学科 100% 教师用书级
- 真实课例 / 常见错误 / 教学活动 3 字段全员入库

### V3.3.1
- 学科→学段→领域 4 层树状导航

### V3.0
- 概念 758 → 1,906 / 关系 299 → 4,736

---

## V2.x · 2025 末

- 工具 / UX / 关系扩充
- lineage BFS 算法稳定
- 主题切换 / 多视图
- 学科化查询

---

## V1.0 之前

- V0.x: 758 概念 + 14 学科 preseed
- 立项：复刻 [Marble](https://withmarble.com/curriculum/) 范式，做中国 2022 义教课标版

---

## 数据现状（V1.0）

| 维度 | 数量 |
|---|---:|
| 概念 | 1,906 |
| 学习路径（边） | 4,736 |
| 学科 | 14 |
| 学段 | 1-9 年级 |
| 题目 | 9,264 |
| 真题（is_real_exam） | 13 |
| AI 改写 | 267 |
| 难度校准 | 2,652 |
| 视频 | 1,008 |
| 跨学段边 | 2,183 (46%) |
| 跨学科边 | 2,613 (55%) |
| 节点 24 字段 | 1,906 × 24 |
| 14 学科教师用书级增强 | 100% |
