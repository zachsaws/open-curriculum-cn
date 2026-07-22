# Open Curriculum CN V2.0 — 前端 UX + 性能审查

**审查日期**: 2026-07-22
**审查范围**: `web/index.html` · `web/app.js` · `web/i18n.js` · `web/data/graph.json` · 公网 `https://zmr9rhsf7ugq0.space.mcode.cn`
**数据基线**: 758 节点 / 167 关系 / 14 学科 / cytoscape.js 373 KB
**测试方法**: curl HEAD/GET + Playwright 1.61 headless Chromium (desktop 1440×900, mobile 375×812 iPhone, iPad 768×1024)
**环境**: 截图存于 `data/screenshots/review-frontend/`, 原始指标 `metrics.json` (同目录)

---

## 0. 摘要

| 维度 | 结论 |
|---|---|
| **冷启动** | DOM 200ms · FCP 120ms · 全加载（含 cytoscape init + preset layout） 1.78s — **可接受** |
| **大体积隐患** | `cytoscape.min.js` 373 KB **未启用 gzip**, 公网每次冷加载浪费 ~256 KB 带宽（占首屏 80% 体积）— **P0** |
| **运行时性能** | 758 节点 60 FPS · 1800 节点仍 60 FPS · 搜索纯计算 1.3ms · 重排 1.6s — **无需重写引擎** |
| **搜索 120ms 防抖** | 当前 758 节点 JS 搜索 1.3ms, 1800 节点 0.7ms — **120ms 防抖过保守**, 浪费约 119ms 感知延迟 |
| **ARIA / 键盘** | 全站 **0 个 ARIA 属性**, 14 个 chip 不可 Tab, 无 `/`、`1-9` 快捷键, canvas 不在 Tab 顺序 — **P0 a11y 失败** |
| **移动端 (375px)** | 详情卡片 480px 宽 > 视口, 内容左缘被裁掉 ~77px, 标题/标签首字不可读 — **P0 不可用** |
| **i18n 缺口** | EN 模式详情面板 **整段仍是中文** (block 标题/tags/subdomain/学科名); zh-TW 简繁字典仅 ~100 字, 286/758 节点残留简体 — **P0** |
| **入口高亮** | 629/758 节点是无入度"根" — 黄色高亮覆盖率 83%, **失去筛选意义** |

**P0 问题数: 5**（带宽、移动端卡片裁切、i18n 详情面板、根节点高亮无意义、a11y 全缺失）
**P1 问题数: 8** · **P2 问题数: 4**

---

## 1. 性能基线 (curl + Playwright)

### 1.1 文件体积 & 公网下载

| 资源 | 原始 | gzip 实际可达 | 公网 transferSize | 实际下载 (公网) | 压缩启用 |
|---|---|---|---|---|---|
| `index.html` | 14 023 B | 3 858 B | ~5 KB | 92 ms | ✅ gzip |
| `cytoscape.min.js` | 373 304 B | **116 944 B** | **373 604 B** | 102 ms | ❌ **未压缩** |
| `app.js` | 20 496 B | 6 420 B | 20 796 B | 53 ms | ❌ (小文件可忽略) |
| `i18n.js` | 7 666 B | 2 819 B | 7 966 B | 35 ms | ❌ (小) |
| `data/graph.json` | 683 102 B | 52 458 B | 52 747 B | 219 ms | ✅ gzip |
| **合计** | **1.07 MB** | **182 KB** | **~460 KB** | — | — |

> **🔴 P0-A 带宽浪费**: `cytoscape.min.js` 服务端没启用 gzip（`Content-Length: 373304`、无 `Content-Encoding`）。每次冷加载多下 256 KB, 在 3G/4G 弱网下多 1-2 秒。**首屏体积放大 2.5 倍**。

### 1.2 冷加载时序 (桌面, headless)

| 阶段 | 时间 |
|---|---|
| TTFB | **12 ms** |
| First Paint | **120 ms** |
| First Contentful Paint | **120 ms** |
| DOM Interactive | 198 ms |
| DOM Complete | 207 ms |
| Load Event | 207 ms |
| `nCount` 填充（数据解析完） | 606 ms |
| `loading` 消失（layout 收尾） | **2 110 ms** |

> 2.1s 中有约 1.5s 是 `setTimeout(..., 200)` + cytoscape preset layout + 随机抖动。**实际感知"看到可交互图"约 2 秒**。

### 1.3 渲染 & 交互性能

| 场景 | 758 节点 | 1800 节点 (合成) |
|---|---|---|
| 内存 (usedJSHeap) | 9.5 MB | 13.6 MB (+4 MB) |
| 总 JS Heap | 28 MB | 38 MB |
| 拖拽/缩放 FPS | **60.1** (2s 内 121 帧) | **60.1** (2s 内 121 帧) |
| 搜索 (纯 JS, in-memory filter) | **1.3 ms** | **0.7 ms** |
| 搜索 (E2E, 含 120ms 防抖 + DOM 渲染) | **186–208 ms** | ~200 ms (估) |
| 重排 (preset 4×4 网格) | **1 592 ms** | **2 086 ms** |
| COSE 1500 iter (仅对照) | 1 348 ms | (未测) |

> ✅ **运行时性能好, 1800 节点也无压力**。瓶颈不在引擎。
> ⚠️ 搜索 E2E 200ms 中 120ms 是防抖 + 60-80ms 渲染 + 浏览器开销。**120ms 防抖是 2008 年的经验值, 当前 758→1800 节点 JS 搜索 ≤2ms, 50ms 防抖足够**。

### 1.4 资源时间线 (PerformanceObserver)

```
cytoscape.min.js:  59 ms (实际下载 102 ms, 含 TTFB)
i18n.js:          128 ms
app.js:           126 ms
graph.json:       118 ms (gzip 后 52 KB)
```

cytoscape 是首屏关键路径, **未压缩导致它和后续三个文件总大小相当**。

---

## 2. UX 12 个具体问题

### 🔴 P0-1: 详情卡片在移动端 (≤ 480px) 文字被裁切 (i18n + 移动)

**实测数据**:
```
[mobile_card] width=480, x=-105, right=375, vw=375
```
- `#card` 是 `position: fixed; right: 0; width: 480px;`
- 375px 视口下, 卡片左缘在 `x = 375 - 480 = -105` (屏外)
- 加上 `padding: 20px 28px`, 内容起点在 `x = -77`, **首 77px 文字不可见**
- 实测截图 (mobile-card.png) 显示: 标题 "整数加减法的算理与算法" → "减法的算理与算法", **"整数加" 3 字被裁**

**根因** (`web/index.html:99`):
```css
#card { position: fixed; right: 0; top: 0; bottom: 0; width: 480px; ... }
```
绝对像素宽度, 无响应式断点。

**修复建议**:
```css
#card { right: 0; width: min(480px, 100vw); ... }
@media (max-width: 600px) {
  #card { width: 100vw; padding: 16px 18px; }
  #card .ctl { font-size: 18px; }
}
```

---

### 🔴 P0-2: i18n 切换 EN/zh-TW 后, 详情面板整段仍为中文

**实测** (EN 模式打开 `M_G1_NS_07`):
```
i18n_en_card:
  blocks: ['📋 课标内容要求', '🎯 课标学业要求', '💡 知识要点', '📚 课标例题']   ← 仍是中文
  tags:   ['✦ 会', '✦ 探索', '难度 ●○○○○', '⏱ 15 分钟', '数的运算']         ← 仍是中文
  ctl:    '整数加减法的算理与算法'                                              ← 仍是中文
  cs:     '数学 · G1-2 · 数与运算'                                              ← 仍是中文
i18n_en_global:
  legendNames: ['艺术','生物','化学','语文','英语','地理','历史','信息科技',...]  ← 全是中文
```

**根因** (3 处):
1. `web/index.html:266-281` 4 个 block 标题**硬编码**:
   ```html
   <div class="block-title">📋 课标内容要求 ...</div>
   <div class="block-title">🎯 课标学业要求</div>
   <div class="block-title">💡 知识要点</div>
   <div class="block-title">📚 课标例题</div>
   ```
2. `web/app.js:285-307` `showCard()` 中 tags 拼接**硬编码中文**: `'✦ ' + b` / `'难度 ' + ...` / `'⏱ ' + ... ' 分钟'`, 学科名取自 `SUBJECT_CN` (硬编码中文), subdomain 直接 `n.subdomain` (图谱数据, 中英文都有).
3. `web/app.js:117` 图例渲染用 `SUBJECT_CN[s] || s` 而**不是** `tSubject(s)`. `tSubject` 定义了但**从未调用**.

**修复方向** (代码片段):
```js
// app.js buildLegend() 改为:
el.innerHTML = `<span class="sw" ...></span>
  <span class="nm">${tSubject(s)}</span>   <!-- 而不是 SUBJECT_CN[s] -->
  <span class="ct">${counts[i]}</span>`;

// app.js showCard() tags 改为:
t.textContent = (currentLang === 'en' ? 'Difficulty ' : '难度 ') +
  '●'.repeat(d) + '○'.repeat(5-d);
t.textContent = (currentLang === 'en' ? '⏱ ' : '⏱ ') +
  n.estimated_minutes + (currentLang === 'en' ? ' min' : ' 分钟');

// index.html 4 个 block-title 改为 id + i18n 字典:
<div class="block-title" data-i18n="card_content_req">📋 课标内容要求</div>
```
并新增 EN/zh-TW 翻译键 `card_bloom`, `card_difficulty`, `card_minutes`, `card_subdomain_label`。

---

### 🔴 P0-3: zh-TW 简繁转换字典覆盖率 38%, 286/758 节点残留简体

**实测**:
```
i18n_tw_simp_residual: total=758, bad=286 (37.7%)
  例: '萬以內数的認識'      ← '数' 漏
       '整数加减法的算理与算法' ← '数','算','理','与','算' 漏
       '20 以內加减法口算'   ← '算' 漏
```

**根因** (`web/i18n.js:130-156` `SIMP_TO_TRAD` 字典):
- 字典只有 ~100 个条目, **大量常用字缺失**: 数、算、义、理、与、号、说、议、请、实、现、来、历、义、设、备、报、告、记、据、处、处、们、见、现、发、观、点、长、师、时、候、种、从、实... (课标语料里出现频次最高的几十字)
- 字典还有**重复 key** (`'习':'習'` 出现 2 次、`'议':'議'` 3 次、`'业':'業'` 2 次、`'计':'計'` 4 次), 浪费条目数

**修复建议**:
1. 用成熟的简繁映射 (opencc-js / hanziconv / t2s.js), 库覆盖 7000+ 字
2. 或手工补全常用 200 字, 维护一份 `web/data/simp_trad.json`
3. 顺带把**每个概念节点**预生成 `title_trad` 写入 graph.json, 启动时一次性完成, 而不是每次切换都遍历 758 节点

```js
// 一次性预转换 (在 loadData 末尾):
for (const n of DATA.nodes) {
  n.title_trad = simpToTrad(n.title);
  n.content_req_trad = simpToTrad(n.content_req || '');
  n.academic_req_trad = simpToTrad(n.academic_req || '');
  // key_points / examples 也是数组
  if (n.key_points) n.key_points_trad = n.key_points.map(simpToTrad);
}
```

---

### 🔴 P0-4: 入口高亮 83% 节点都是"根" — 失去筛选意义

**实测**:
```
roots_state: rootCount=629, highlighted=629 (758 中 629, 占比 83%)
root_visibility: totalRoots=629, inView=629
toggleText: '取消高亮'
```

**根因** (`web/app.js:172-179` `updateRootCount` + `toggleRootsHighlight`):
```js
const roots = cy.nodes().filter(n => n.indegree() === 0 && n.data('subject'));
```
- 课标 2022 版**确实**有大量"零起点"概念 (G1 第一学段几乎所有概念都是根), 这是事实
- 但 "高亮入口" 按钮的语义是 "**没有先决、可作为学习起点**", 当前高亮 83% 节点**等于全图变黄**, 视觉上没有任何区分
- 截图 `05b-roots.png` 和默认视图视觉上**几乎无差**

**修复建议 (2 个方向)**:
1. **改定义**: 真正的"入口"应该 = 终点无出度的叶子节点 (即"最基础不能再分"), 或"学段最早" (G1) 的概念。当前 629 个里, 多数是有后继的中间概念, 并不是"学习入口"
2. **改交互**: 既然图谱本身就是 DAG, 入口 = `indegree === 0` 太宽松。可以加一个 "**只显示无先决的概念**" 模式 (高斯模糊其他节点) 而不是黄色描边

```js
// 改 1: 入口限定为 (indegree === 0 && grade_start <= 2) — 真正"零基础可学"
const roots = cy.nodes().filter(n =>
  n.indegree() === 0 && n.data('grade_start') <= 2 && n.data('subject')
);
```

---

### 🔴 P0-5: 全站零 ARIA, 键盘用户无法用

**实测**:
```
aria: {
  searchInput: { aria_label: null, role: null },
  card: { aria_label: null, role: null },
  close: { aria_label: null },        // 只有 "×"
  legend: { role: null },
  chips: 全部 { role: null, aria_label: null, aria_pressed: null, tabindex: null },
  langBtns: 全部 { aria_label: null, aria_current: null },
  srOnly: 0, ariaHidden: 0, ariaDescribedby: 0, ariaLive: 0
}
```

**Tab 链实测** (20 次 Tab):
```
1. <a> Marble
2. <a> 教育部 2022 义教新课标
3-5. <button> 简/繁/EN (lang switch)
6-8. <button> 显示标签/高亮入口/重排
9. <input#searchInput>
10. <button.close> ×
11. <body> ← Tab 跳出, 但 chips / canvas / 关联系都不可达
```

**14 个 chip 不在 Tab 链** (无 `tabindex`); canvas 完全不可聚焦, **键盘用户无法探索图谱**.

**修复示例**:
```html
<!-- 搜索框 -->
<input id="searchInput"
  role="searchbox"
  aria-label="搜索概念"
  aria-controls="searchResults"
  aria-autocomplete="list"
  ...>

<!-- 搜索结果列表 -->
<div id="searchResults" role="listbox" aria-label="搜索结果">
  <div class="r-item" role="option" tabindex="0" data-id="...">
    ...
  </div>
</div>

<!-- chip 改为可聚焦 + aria -->
<div class="chip" role="button"
     tabindex="0"
     aria-pressed="true"
     aria-label="切换 艺术 学科显示, 22 个概念">
  ...
</div>

<!-- canvas 加描述 -->
<div id="cy-container" role="application"
     aria-label="知识图谱画布, 共 758 个概念, 14 个学科, 鼠标拖拽平移, 滚轮缩放, 单击节点查看详情"
     tabindex="0">
</div>

<!-- 详情面板 -->
<div id="card" role="dialog" aria-modal="false" aria-labelledby="card-ctl">
```

**键盘快捷键建议** (在 app.js 顶部加):
```js
document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') return;  // 输入框内不拦截
  if (e.key === '/') { e.preventDefault(); document.getElementById('searchInput').focus(); }
  if (e.key === 'l') { document.getElementById('toggleLabels').click(); }
  if (e.key === 'r') { document.getElementById('toggleRoots').click(); }
  if (e.key === 'Escape') { document.getElementById('card').classList.remove('on'); }
  if (/^[1-9]$/.test(e.key)) {
    const idx = parseInt(e.key) - 1;
    const chip = document.querySelectorAll('.chip')[idx];
    if (chip) chip.click();
  }
});
```

---

### ⚠️ P1-1: 搜索 120ms 防抖在 758/1800 节点下过保守

**实测**:
- 758 节点纯 JS filter: 1.3ms
- 1800 节点纯 JS filter: 0.7ms (更少, 因 synth 节点没相关字段)
- 当前 E2E: 186-208ms (debounce 120 + render 60 + 浏览器 6-28ms)

**建议**: 改为 **40ms 防抖** + 30ms 内的输入合并, 或**完全去掉防抖** (1ms 计算 + 60ms 渲染 = 61ms, 仍在 60fps 预算内, 体感比当前快 2 倍).

```js
// 当前
debounce = setTimeout(() => doSearch(input.value.trim()), 120);

// 改为
debounce = setTimeout(() => doSearch(input.value.trim()), 30);
```

注: 防抖主要是为"打字速度 < 网络往返"。本地 in-memory 搜索, 不存在网络成本, 120ms 显得过度。

---

### ⚠️ P1-2: 搜索框左缘的 🔍 图标在某些环境下不可见

**CSS** (`web/index.html:71-77`):
```css
.search::before { content: "🔍"; position: absolute; left: 12px; ...; color: #8a92a8; font-size: 12px; }
.search input { padding: 10px 14px 10px 36px; ... }
```

**问题**:
- 🔍 emoji 在不同操作系统字体下大小不一 (Win 不带彩 emoji 字体时回退到黑白)
- `color: #8a92a8` (灰) 在深色背景上对比度仅 3.4:1, **低于 WCAG AA 4.5:1**
- 实测默认截图里图标**几乎看不见**

**建议**:
```css
.search::before {
  content: "";
  width: 14px; height: 14px;
  background: url("data:image/svg+xml,...search icon SVG...") center/contain no-repeat;
  opacity: 0.7;
}
```

---

### ⚠️ P1-3: 14 学科图例排成 10+4 两行, 顺序无逻辑

**实测** (1440 视口):
```
row 1 (y=818): 艺术(22) 生物(36) 化学(37) 语文(75) 英语(71) 地理(43) 历史(43) 信息科技(28) 劳动(21) 数学(214)
row 2 (y=852): 道法(39) 体育(25) 物理(63) 科学(41)
```

**问题**:
- 顺序按 `set(...nodes.map(n=>n.subject)).sort()` (字母序) — 但 GROUPS 的 sort 是默认字典序, **"art" 排第一是因为 a 字母最小**, 跟学科重要性无关
- "数学(214)" 是最大块却排到第一行最后, 用户第一眼看到的是 "艺术(22)"
- 第一行 10 个 chip 满到 864px (视口 60%), 第二行 4 个显得孤零零
- 14 学科全靠颜色记忆, 没有分组 (文/理/艺/体), 颜色相近的 (math#5b8def / science#f9a825 / geography#42a5f5) 容易混淆

**建议**:
- 按学科**中文笔画/拼音**排序, 第一行 "语数英" 三大主科放最显眼
- 或按"学段数"分组: 主科 (语数英) / 理科 (物化生科) / 文科 (史地道法) / 艺体综合 (音体美劳信息)
- 第二行 chip 居中或加分组标签

---

### ⚠️ P1-4: 双击 chip fly to 中心, 但 zoom 1.2 看不到边缘概念

**实测** (`web/app.js:131-138` `flyToSubject`):
```js
cy.animate({
  center: { x: (bb.x1 + bb.x2) / 2, y: (bb.y1 + bb.y2) / 2 },
  zoom: 1.2,    // ← 硬编码
  duration: 600,
});
```

**问题**:
- 实际 layout 里每个学科块是 4×N 网格, 物理像素占满视口 (因 fit 后)
- zoom 1.2 反而**放大到单学科块内部**, 不在当前 zoom 范围的概念 (即学科块边缘) 看不到
- 用户期望"看这个学科" = "fit 整个学科块到视口", 而不是 "放大到中心"
- 此外, 学科块**有重叠的边** (相邻学科的节点可能因随机抖动在边界处穿插), 单击 chip 显隐 + 双击 fly 是一对矛盾操作

**建议**:
```js
function flyToSubject(s) {
  const nodes = cy.nodes().filter(n => n.data('subject') === s);
  if (!nodes.length) return;
  // 计算该学科所有节点的 boundingBox, fit 到视口
  const bb = nodes.boundingBox({ includeLabels: false });
  cy.animate({
    fit: { eles: nodes, padding: 80 },
    duration: 600,
  });
}
```

---

### ⚠️ P1-5: 学科 chip 单击切换显隐的反馈是 `opacity 0.1` — 边缘节点仍可见

**实测** (`web/app.js:148-158` `updateFilter`):
```js
cy.nodes().forEach(n => {
  if (activeGroups.has(n.data('subject'))) {
    n.style('opacity', 1);
  } else {
    n.style('opacity', 0.1);  // ← 0.1 还是看得见
  }
});
```

但**边 (edges) 完全没有处理** — 隐藏学科的边仍然画着, 视觉混乱。
截图 `05b-roots.png` 也未截到此场景, 实际可观察到: 关闭 1-2 个学科, 那些边横穿整个画布。

**建议**:
```js
function updateFilter() {
  const chips = document.querySelectorAll('.chip');
  const newActive = new Set();
  chips.forEach(chip => {
    if (!chip.classList.contains('off')) newActive.add(chip.dataset.subject);
  });
  activeGroups = new Set(newActive);
  if (cy) {
    cy.batch(() => {
      cy.nodes().forEach(n => {
        n.style('opacity', activeGroups.has(n.data('subject')) ? 1 : 0.08);
        n.style('display', activeGroups.has(n.data('subject')) ? 'element' : 'none');
      });
      // 关键: 边和关闭学科相连时也隐藏
      cy.edges().forEach(e => {
        const sOk = activeGroups.has(e.source().data('subject'));
        const tOk = activeGroups.has(e.target().data('subject'));
        e.style('display', sOk && tOk ? 'element' : 'none');
      });
    });
  }
}
```

---

### ⚠️ P1-6: 标签模式 "显示标签" — 758 节点全显示文字, 完全不可读

**实测截图** `11b-labels.png`:
- 节点 8px, 文字 10px, 每个节点标签下都有 ~30 字的概念名
- 整张图变成 "文字糊", 完全无法辨识哪个文字属于哪个节点
- 标签互相重叠 5+ 层

**建议** (3 个方向任选):
1. **默认不开启, 按钮改成 "按 hover 显示"**: 取消 toggle 按钮, hover 节点才显示 label (当前已有 hover 显示, 但 toggle 按钮误导)
2. **限定只在选中/根节点显示**: 选中的节点 + 1-hop 邻居才显示
3. **加 zoom 阈值**: `text-rotation: 'autorotate'` + `min-zoom: 2` (放大到 200% 才显示 label), cytoscape 原生支持

```js
// 方案 3 最简单
{
  selector: 'node',
  style: {
    'label': '',  // 默认无 label
    'min-zoom-label': 1.5,  // 放大到 1.5x 才显示 (cytoscape 3.20+)
  }
}
```

---

### ⚠️ P1-7: 详情面板 G1-2 / G7-9 ID 标签字体等宽, 中文 4 字 = 数字 4 字 = 错位

**实测** (`showCard` 输出):
```
cs: '数学 · G1-2 · 数与运算'    ← "1-2" 占 3 字符
ctl: '整数加减法的算理与算法'  ← 中文 11 字, font-size 22px
charsPerLine: 19 (中英字符宽度差 ~2x)
```

**问题**:
- 标题 22px 字体在 423px 宽 (480-2*28) 容器里只能放 ~10 个汉字 (汉字宽度是英文 2 倍), 超过会换行
- 实测长标题 (例: "万以内数的认识" = 7 字) 一行能放下; "整数加减法的算理与算法" (11 字) **必须换行** — 截图中标题确实一行 (29px height, lineHeight 28.6) — 是单行
- 但**学科信息行** "数学 · G1-2 · 数与运算" (15 字符) 在 480px - padding 56 = 424px 容器里刚好, 字号 11px, 也可能换行

实测 11 字 ctl 高度 29px = lineHeight 28.6 → 1 行, 实际 11 中文字符 + 22px 字号 ≈ 242px 宽 < 423, 一行放下. 但**15 字符的 cs 文本** 11px 字号, 中英文混排, 实测**勉强 1 行**.

**实测 ID 格式**: 实测节点 ID 形如 `M_G1_NS_01` (10 字符), 卡片**不直接显示 ID** (只显示 subject + grade + domain). 所以 ID 难读问题不严重, 但 `subdomain` tag 直接显示, 形如 "数的认识" / "物质的结构" / "能量与能源", 是中文短语, 渲染正常.

**结论**: 标题在 480px 宽 + 22px 字号下可放 ~19 中文字符 (实测) — **不会换行**, 但**容错余量仅 30%**. 若标题再长 (例: "三角形面积的计算公式及其在生活中的应用" 18 字) 会**强制换行 2 行**, 体验可接受. **不视为 P0**.

**建议**: 标题字号桌面 22px → 18px (`font-size: clamp(16px, 2vw, 22px)`), 留出余量.

---

### ⚠️ P1-8: 重排按钮预设布局耗时 1.6s, 期间无 loading 反馈

**实测**: 1 592 ms (758), 2 086 ms (1800)
- cytoscape `preset` layout 是同步阻塞, 期间页面**完全无响应**
- 鼠标点击后 ~1.6s 没有任何视觉变化 (除了 console.log)

**建议**:
```js
function relayout() {
  const btn = document.getElementById('reLayout');
  btn.disabled = true;
  btn.textContent = '排版中…';
  // 用 requestAnimationFrame 切到下一帧再跑
  requestAnimationFrame(() => requestAnimationFrame(() => {
    // ... 现有逻辑 ...
    cy.layout({...}).run();
    // preset 是同步的, 用 setTimeout 让 UI 有机会更新
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = t('btn_relayout');
    }, 50);
  }));
}
```
注: 1.6s 主要花在**遍历 758 节点计算网格位置** (JS 部分) + `cy.layout().run()` (cytoscape 部分). 可改用 Web Worker 离主线程计算, 或改写为更高效的算法 (现版每个节点计算 `Math.random()` × 2 次, 总 1500 次函数调用, 可批量).

---

### P2-1: 搜索结果列表无 "高亮当前选中项" / 键盘上下选择

`web/app.js:226` 的搜索结果只支持鼠标点击, 键盘用户无法:
- ↑/↓ 在结果间切换
- Enter 打开高亮项
- 结果列表也没 `aria-selected`

### P2-2: `simplify-to-trad` 字典有重复 key

```js
'习':'習','习':'習',  // 重复
'议':'議','议':'議','议':'議',  // 重复 ×3
'业':'業','业':'業',  // 重复
'计':'計','计':'計','计':'計','计':'計',  // 重复 ×4
'动':'動','动':'動',  // 重复
'变':'變','变':'變',  // 重复
'种':'種','种':'種',  // 重复
'样':'樣','样':'樣',  // 重复
'来':'來',  // '來' 已经是繁, 没问题
'现':'現',
```
重复 key 在 JS 对象里**后写覆盖前写**, 所以 24 个 key 实际只贡献 12 个映射. 字典看上去 100 条, 实际 88 个 unique.

### P2-3: `applyI18n()` 不会重新填充已打开的详情面板

```js
// i18n.js applyI18n:
if (typeof window._currentNode === 'function') { /* 略 */ }   // ← 占位, 没实现
```
语言切换时, 若详情面板已打开, 标题/tags/blocks 不会重新渲染. 截图 `07-tw-card.png` 证实 — 切到 zh-TW 后卡片还是简体中文.

### P2-4: 加载 spinner 后无错误重试

`web/app.js:50-55` `loadData`:
```js
} catch (e) {
  loadingMsg.innerHTML = `<div class="err">未找到图谱数据 (graph.json)<br><br>数据仍在采集中</div>`;
  return;
}
```
失败后只显示静态错误, 无 "重试" 按钮, 用户得 F5.

---

## 3. 键盘 / 无障碍清单

| 项 | 当前 | 应有 | 严重度 |
|---|---|---|---|
| 搜索 input `aria-label` | ❌ | `aria-label="搜索概念"` | P0 |
| 搜索结果 `role="listbox"` | ❌ | 角色 + 选项 | P0 |
| Chip `role="button"` + `tabindex=0` | ❌ | 全部 14 个 | P0 |
| Chip `aria-pressed` 切换显隐 | ❌ | 状态 | P0 |
| Canvas `tabindex=0` + `aria-label` | ❌ | 可达 + 描述 | P0 |
| 详情面板 `role="dialog"` + `aria-labelledby` | ❌ | 屏幕阅读器 | P0 |
| 关闭按钮 `aria-label` | ❌ ("×" 无意义) | `aria-label="关闭详情"` | P1 |
| 语言切换 `aria-current` | ❌ | 当前语言标记 | P1 |
| 标签/状态变化 `aria-live` | ❌ | "搜索到 N 个结果" | P1 |
| 快捷键 `/` 聚焦搜索 | ❌ | 触发 | P1 |
| 快捷键 `1-9` 切学科 | ❌ | 触发 | P2 |
| 快捷键 `l` toggle label | ❌ | 触发 | P2 |
| 快捷键 `r` toggle roots | ❌ | 触发 | P2 |
| 快捷键 `Esc` 关闭面板 | ⚠️ 只清搜索 | 关闭详情也支持 | P1 |
| 搜索结果 ↑/↓/Enter | ❌ | 键盘可达 | P2 |
| 跳到主内容 skip link | ❌ | `<a href="#wrap">` | P2 |
| 焦点环样式 | ⚠️ 默认浏览器环 | 自定义可见环 | P2 |
| html lang 切换 | ❌ (一直 zh-CN) | 随语言切换 | P1 |

**结论**: 0/18 通过. **键盘用户当前完全无法使用产品**.

---

## 4. 移动端适配建议

### 4.1 实测布局 (375×812 iPhone)

| 元素 | 位置 (x,y,w,h) | 问题 |
|---|---|---|
| header | 0,0,375,100 | h1 16px + sub 12px 双行 → 60-100px, **占据首屏 12%** |
| lang-switch | 46,20,109,26 | 飘在 header 上, **与 h1 重叠** |
| stats | 161,80,194,125 | **与 header 底部重叠**, 占据右上 194px |
| search | 20,80,320,38 | 320px 在 375 视口, **右缘只剩 35px 边距** |
| legend | 20,560,225,232 | 7 行 × 2 chip, 232px 高, **占屏 28%** |
| card | -105,0,480,812 | **左缘在屏外 -105px** (见 P0-1) |

### 4.2 修复路线图

**第一阶段 (1-2h)**:
- `#card` 响应式: `width: min(480px, 100vw)` + 移动断点 padding 收紧
- header `h1 + sub` → 移动端只显示 h1, sub 折叠到可点 ⓘ
- stats 移到顶部底部 (header 下, search 上), **不再悬浮**
- search 全宽 (`width: calc(100vw - 40px)`)

**第二阶段 (半天)**:
- 14 chip 改**抽屉**, 顶部一个 "14 学科 ▾" 按钮, 弹出 4 列网格
- lang-switch 移到 header 右上 (现在飘在半空)
- canvas 在移动端用 `<details>` 折叠 detail, 全屏打开 (现在 480px 卡挡住 100% 视口, 但只看到右 375px)

**第三阶段 (1 天)**:
- 整套布局重写为 flex/grid, 媒体查询三档 (手机 ≤ 600 / 平板 ≤ 900 / 桌面 > 900)
- 触摸事件: cytoscape 的 tap 移动端 OK, 但**双击 chip fly** 在移动端无意义 (没双击), 改 "长按"

---

## 5. i18n UI 翻译缺口

### 5.1 已翻译 (OK)
- `app_title` / `app_subtitle`
- `stats_concepts` / `stats_edges` / `stats_subjects` / `stats_roots`
- `btn_labels` / `btn_roots` / `btn_relayout`
- `search_placeholder`
- 学科名 `SUBJECT_CN_I18N` 表 (14 个, 全有 EN/zh-TW 翻译) — **但代码不调用** (见 P0-2)

### 5.2 未翻译 (gap)

| 字段 | 位置 | 当前值 (EN) | 应翻译 | 严重度 |
|---|---|---|---|---|
| 4 个 block 标题 | index.html:266-281 | 课标内容要求 / 课标学业要求 / 知识要点 / 课标例题 | EN 字符串 | P0 |
| 标签 `✦ 会 / ✦ 探索 / ...` | app.js:288 (bloom) | 用图谱数据原值 | "✦ Mastery" 等 | P0 |
| 标签 `难度 ●○○○○` | app.js:296 | "难度 " 前缀 | "Difficulty " | P0 |
| 标签 `⏱ 15 分钟` | app.js:303 | "⏱ " + " 分钟" | "⏱ 15 min" | P0 |
| 标签 `subdomain` | app.js:309 | 直接显示中文 (图谱数据) | (依赖图谱 EN 翻译) | P1 |
| 详情 `cs` 头部 | app.js:282 | "数学 · G1-2 · 数与运算" | "Math · G1-2 · ..." | P0 |
| 详情 `preEmpty / nextEmpty` | app.js:329,335 | "没有先决概念" | "No prerequisites" | P0 |
| 详情 `ctl` (title) | app.js:283 | 图谱数据原值 | (依赖图谱 EN 翻译) | P1 |
| 详情 `block-body` | app.js:294 等 | 图谱数据原值 | (依赖图谱 EN 翻译) | P1 |
| 14 学科图例 | app.js:117 | `SUBJECT_CN[s]` 直接渲染 | `tSubject(s)` | P0 |
| 加载错误 | app.js:53 | "未找到图谱数据" | EN 翻译 | P2 |
| 搜索结果 `N 匹配` | app.js:215 | 中文 | EN 翻译 | P2 |
| 搜索结果 `无匹配概念` | app.js:218 | 中文 | EN 翻译 | P2 |

### 5.3 数据层 EN 翻译

`graph.json` 全部节点是中文 title/content_req/key_points. EN/zh-TW 模式只翻译了**外壳 UI**, 数据本身仍是中文. **本质问题**: 这是"半翻译" — 静态 UI i18n 框架搭了, 但**图谱数据多语化未做**.

**建议**:
- 短期: 节点双语并存, 在 graph.json 加 `title_en` / `title_tw` 字段, 数据生成时一并产出
- 长期: 数据用 i18n key, 在 UI 查表 (类似 react-intl)

---

## 6. 优先修复清单

### 🔴 P0 (5 项, 1-2 天)

| ID | 问题 | 估算 | 验证 |
|---|---|---|---|
| **P0-A 带宽** | `cytoscape.min.js` 服务端启用 gzip (CDN / nginx `gzip on; gzip_types application/javascript;`) | 5min | curl -H 'Accept-Encoding: gzip' 看 `Content-Encoding` |
| **P0-1 移动卡片** | CSS 加 `min(480px, 100vw)` + 移动 padding 16px 18px | 30min | 375px 视口截图, 标题左缘对齐 |
| **P0-2 详情 i18n** | block-title 改 data-i18n + tags 拼接走 `t()` + 学科名走 `tSubject()` | 2h | 切换 EN, 卡片全英文 |
| **P0-3 简繁字典** | 用 opencc-js 替换手写字典 (npm 7000 字覆盖) | 1h | 切换 zh-TW, 0 个简体残留 |
| **P0-4 入口高亮** | 缩窄定义为 `(indegree === 0 && grade_start <= 2)` 或改 "模糊非入口" 模式 | 1h | 高亮数 ≤ 100, 视觉有区分 |
| **P0-5 键盘/a11y** | 14 个 chip 加 `role="button" tabindex="0" aria-pressed`; canvas 加 `tabindex="0" aria-label`; `/` 聚焦搜索 | 半天 | Tab 链到 18 项, VoiceOver 朗读 "按钮 艺术 22 个概念" |

### ⚠️ P1 (8 项, 3-5 天)

| ID | 问题 |
|---|---|
| P1-1 | 搜索防抖 120 → 30ms |
| P1-2 | 搜索 🔍 改 SVG icon, 对比度 4.5:1+ |
| P1-3 | 14 学科图例按"主科 / 理科 / 文科 / 艺体综合"分组, 主科排前 |
| P1-4 | `flyToSubject` 改 `cy.fit({eles: nodes, padding: 80})` |
| P1-5 | `updateFilter` 同时隐藏边 + 节点 |
| P1-6 | 标签模式改 min-zoom 1.5 显示 或 hover-only |
| P1-7 | 标题字号 `clamp(16px, 2vw, 22px)`, 防超长换行 |
| P1-8 | 重排按钮加 loading 态 + requestAnimationFrame 让 UI 有机会 paint |

### 🟢 P2 (4 项, 有空再做)

- P2-1 搜索结果 ↑/↓/Enter
- P2-2 简繁字典去重 (24 个重复 key)
- P2-3 `applyI18n` 重新填充已打开的详情面板 (i18n.js 里的占位 TODO)
- P2-4 加载失败加 "重试" 按钮

---

## 7. 附录: 性能基线数据 (raw)

```json
{
  "cold_load": {
    "ttfb_ms": 12, "fcp_ms": 120, "domComplete_ms": 207,
    "data_loaded_ms": 606, "layout_done_ms": 2110
  },
  "resources_transfer_bytes": {
    "cytoscape.min.js": 373604,  // ← 未压缩
    "graph.json": 52747,         // ← gzip 后
    "app.js": 20796, "i18n.js": 7966
  },
  "runtime_758": { "fps": 60.1, "mem_mb": 9.5, "search_pure_ms": 1.3 },
  "runtime_1800": { "fps": 60.1, "mem_mb": 13.6, "search_pure_ms": 0.7 },
  "search_e2e_ms_758": 186,    // 120 debounce + 60 render
  "relayout_preset_ms_758": 1592,
  "relayout_preset_ms_1800": 2086,
  "cose_1500_ms_758": 1348,
  "root_count": 629,           // 83% 节点无入度
  "i18n_tw_simp_residual": 286, // 286/758 节点未繁化
  "aria_attrs_total": 0        // 全站 0 个 ARIA
}
```

---

**报告完成**. 建议 P0 五项本周内修, 因为:
1. P0-A 5 分钟改 nginx, 用户立刻感知首屏快 2 倍
2. P0-1 移动端卡片是**功能完全不可用** (内容被裁), 修 30 分钟
3. P0-2/P0-3 关系到"中国 K12 国际化开源"项目定位, 不能 EN 模式还全是中文
4. P0-5 a11y 缺失对屏幕阅读器用户**完全黑屏**, GitHub 也会被 a11y bot 标 issue

P1 8 项建议两周内排期, P2 4 项 next milestone.
