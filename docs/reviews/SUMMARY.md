# V2.0 → V2.x 审查汇总

> 4 个 sub-agent 并行审查 4 个角度
> 报告: data-quality / relation-graph / frontend-ux / i18n

## 📊 总体判断

| 角度 | 报告 | VERDICT | P0 问题数 |
|---|---|---|---:|
| 数据质量 | [data-quality-review.md](data-quality-review.md) | **FAIL** | 5 |
| 关系图谱 | [relation-graph-review.md](relation-graph-review.md) | **FAIL** | 5 |
| 前端 UX | [frontend-ux-review.md](frontend-ux-review.md) | **WARN** (性能 OK, UX 不行) | 5 |
| i18n | [i18n-review.md](i18n-review.md) | **FAIL** | 5 |

## 🔥 4 份报告合并后的 20 项 P0

### 数据质量 (5)
1. **`src_page` 90.6% 指向 P1 封面** — 687 节点错位，"课标原文"链接全失效
2. **`src_stage` 7 学科 100% 缺失 + 6 学科 88 条错位** — 教学顺序错乱
3. **`academic_req` 82.5% 缺失** — 仅 133/758 填了，集中在数学
4. **`content_req` 是"通用 OCR 拼接头 + 概念改写"** — 39% 第二段在 OCR 找不到
5. **跨学科关系仅 12 条，9.9% 覆盖** — 14 学科理论组合 91 对

### 关系图谱 (5)
1. **拆 `type=0`** → `relates_to` (跨学科) + `progresses_to` (同学科跨段)
2. **补 88 条跨学科关系** (从 9 对 → 28 对 = 30.8%)
3. **补 23 条数学跨学段螺旋** (闭合 G1-2→G3-4→G5-6→G7-9)
4. **修 API 4 个 P0 bug** (递归爆栈 / 邻接表启动一次构建 / type 字段不丢 / 404 visited_count)
5. **补 12 条语/英同学科跨段** (中英 100% 孤儿)

### 前端 UX (5)
1. **`cytoscape.min.js` 373KB 未启用 gzip** (省 256KB)
2. **移动端 `#card` 480px > 375px 视口** — 标题"整数加"三字被裁
3. **EN 模式 detail panel 4 个 block 标题硬编码中文** — `t()` 没接
4. **简繁字典 100 字, 286/758 节点残留简体** — 换 OpenCC (7000 字)
5. **入口高亮 83% 节点被高亮** — 全图变黄失去筛选意义 (缩窄定义)

### i18n (5)
1. **扩 SIMP_TO_TRAD 字典**到 ≥500 字 (当前 100 字, 9.2% 覆盖)
2. **删 23 个无效映射** (同形字占位)
3. **修 `applyI18n` 不重渲染 showCard 的 bug** — 切语言后详情面板全中文
4. **`app.js` 改用 `tSubject()` 替换 `SUBJECT_CN`** — 三处硬编码
5. **`index.html` 4 个 block 标题用 `t()`** — 21 处硬编码

## ✅ 关键亮点（别全看负面的）

- **运行时性能完全不是瓶颈**: 1800 节点仍 60 FPS, 搜索 0.7ms
- **V0.7 enrich 14/14 PASS** 框架已跑通，颗粒度问题用迭代修
- **结构性问题已暴露**: src_page/src_stage/academic_req/i18n 4 大盲点明确

## 📅 建议的下一轮顺序 (3 阶段 V2.1 / V2.2 / V2.3)

### V2.1 (本周) — 数据修复 + 性能小修 (估 2 天)
- 修 `src_page` 提取 (按 stage 推真实页区间)
- 修 `src_stage` 公式 (对 G7-9 算 stage=4)
- 修 `academic_req` 缺失 (用同段 OCR 学业要求 fallback)
- 启用 gzip on web server
- 修移动端 #card 宽度 (min(480px, 100vw))
- 删无效字典映射 + 修 `applyI18n` showCard bug
**总 6 个 P0**

### V2.2 (下周) — 关系补全 + i18n 实质化 (估 3 天)
- 拆 type 字段 (relates_to / progresses_to)
- 补 88 跨学科关系
- 补 23 数学跨学段 + 12 语文英语跨段
- 扩 SIMP_TO_TRAD 字典到 500+ 字 (或换 OpenCC)
- app.js 改 t() 函数 + showCard 用 t() 重渲染
- index.html 4 block 标题用 t()
**总 6 个 P0**

### V2.3 (下下周) — UX 改造 + 教师审核 (估 2 天)
- 入口高亮缩窄 (grade_start ≤ 2)
- 加键盘快捷键 (/ 搜索, 1-9 切学科, esc 关闭)
- 加 ARIA (tabindex, role, aria-label)
- 加 "从这里学起" 按钮
- 抽样 30 概念请用户审核 (邮件或在线表单)
**总 5 个 P0**

## 📌 长期路线 (V3+)

- **V3.0** — 1800 概念扩到完整上限 (2000)
- **V3.5** — 海外华人版 (繁中 + 英文双语)
- **V4.0** — 真实 GitHub 仓库 (需用户授权 token)
- **V5.0** — 教培 SaaS B 端 API (多租户 + 计费)
