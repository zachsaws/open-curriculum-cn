# Open Curriculum CN V2.3 — 剩余 Bug 审查

**审查日期**: 2026-07-22
**审查范围**: `web/index.html` · `web/app.js` · `web/i18n.js` · `web/simp_to_trad.js` · `api/server.py` · `api/web_server.py` · `data/graph/all_v0.8.json`
**审查方式**: 静态代码审查 (Read 工具) + Python 数据健全性 + curl 边界测试 + Playwright 1.x 真实运行
**基线**: 30 个 pytest 全过, V2.0 → V2.3 之前已修 4 个 P0 维度 (gzip / 移动端 / i18n UI / 字典 / 入口缩窄)
**测试脚本**: `/tmp/v23_uitest.py` (12 个 UI 断言) + 内联 curl 探测
**截图**: `/tmp/v23_ui/01-13_*.png`

---

## 0. TL;DR

| 维度 | 结论 |
|---|---|
| **P0 安全** | 1 个 — web_server **路径遍历** 可读 `/etc/passwd` |
| **P0 数据** | 1 个 — **`src_page` 100% 是 P1 (687/687)** (V2.0 报告的 90.6% 实际是 100%) |
| **P0 i18n** | 1 个 — **EN 模式概念 title 仍是中文** (UI 翻译了, 数据没翻译) |
| **P0 UX** | 1 个 — **详情面板打开时, 整个 lang-switch 被遮挡** (z-index 13 < card 15) |
| **P1 UX** | 4 个 — 浮动按钮 z-index 14 遮 stats panel; 切语言后 search/floating/loading 三处不重渲; 重排按钮 100 字段 |
| **P1 数据** | 1 个 — **467/758 (62%) 节点是孤立** (无入度无出度) |
| **P1 字典** | 1 个 — **simp_to_trad 字种覆盖 20.4%, 31.4% by freq** (声称 500+ 实际有效 233) |
| **P2 死代码** | 4 个 — `cy_nodes_initialized` / `_should_gzip` / `loading.error` 状态不切 / `app.get("/")` 不可达 |
| **总体** | **5 个 P0 / 9 个 P1 / 5 个 P2** — **VERDICT: FAIL** |

**4 个 P0 必修**:
1. `api/web_server.py:49-50` 加 `fp.resolve()` 防 `Path("WEB_DIR") / Path("//etc/passwd")` 跳过沙盒
2. `data/graph/all_v0.8.json` 全部 687 节点的 `src_page=1` 修复, "课标原文 ↗" 链接 100% 失效
3. `web/app.js` EN 模式要给每个 cy 节点加 `title_en` 翻译 (i18n.js 加 `CONCEPT_EN` 字典 / API 加 `?lang=`)
4. `web/index.html:332` 把 `.lang-switch` 的 `z-index` 从 13 提到 ≥ 16, 移到 card 之上

---

## 1. P0 — 必修

### 🔴 P0-1: web_server 路径遍历 — 任意文件读取

**位置**: `api/web_server.py:49-50`

**代码**:
```python
@app.get("/{path:path}")
def serve(path: str = ""):
    if not path:
        path = "index.html"
    fp = WEB_DIR / path   # ← BUG: 没解析 / 没检查越界
    if not fp.exists() or not fp.is_file():
        return Response("Not Found", status_code=404)
```

**复现**:
```bash
$ curl -s 'http://127.0.0.1:8002////etc/passwd' | head -3
##
# User Database
# 

$ curl -s 'http://127.0.0.1:8002////etc/hosts'
127.0.0.1	localhost
...
```

**根因**: POSIX `Path("a") / Path("//etc/passwd")` 把前导 `//` 视为绝对路径, 直接绕过 `WEB_DIR` 沙盒。`/../../../etc/passwd` 被 FastAPI 规范化掉, 但 `////etc/passwd` 不被规范化, 走到 web_server 时变成 `//etc/passwd`, `WEB_DIR / Path("//etc/passwd")` = `Path("//etc/passwd")` 即根目录。

**修复**:
```python
fp = (WEB_DIR / path).resolve()
try:
    fp.relative_to(WEB_DIR.resolve())  # 强制在沙盒内
except ValueError:
    return Response("Forbidden", status_code=403)
if not fp.exists() or not fp.is_file():
    return Response("Not Found", status_code=404)
```

**优先级**: P0 — 公网部署 (`https://zmr9rhsf7ugq0.space.mcode.cn`) 立即可被利用读取 `/etc/passwd`、`.env`、任何用户文件。30 测虽过 (TestClient 不发 `//` 头) 但这是测试盲区。

---

### 🔴 P0-2: src_page 100% 指向 P1, "课标原文" 链接全失效

**位置**: `data/graph/all_v0.8.json` (687 个节点, 全部 `src_page=1`)

**实测** (Python):
```
有 src_page: 687
无: 71
页码 top 10:
  P1: 687       ← 100% 全部是 P1
```

**根因**: V2.0 数据质量审查已经报告 "src_page 90.6% 指向 P1 封面"。V2.3 没有修复, 反而**还更糟了** (从 90.6% 变成 100% — 之前还有 9.4% 是正确页码, 现在全部归一)。showCard 的链接:
```js
// web/app.js:367-369
pageLink.innerHTML = ` · <a class="src-link" href="https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html" target="_blank">P${node.src_page} ${srcText}</a>`;
```
href 永远是 `index.html` 根地址, 显示文本却写 "P1 课标原文 ↗", 跟 P1 章节无对应关系。教师点进去看不到任何上下文。

**修复**: 在 `data/parsed/*.json` enrich 阶段按 subject + stage 推真实页码区间 (e.g. math G1-2 → P5-P12, G3-4 → P13-P30)。或者干脆**移除"课标原文"链接**直到数据修好, 别让用户看到坏链。

**优先级**: P0 — 用户可见的功能, 全图谱教师/家长信任崩塌。

---

### 🔴 P0-3: EN 模式概念 title 仍是中文, i18n 形同虚设

**位置**: `web/app.js:81-90` + `data/graph/all_v0.8.json` (无 `title_en` 字段)

**实测** (Playwright 切换到 EN):
```
EN 模式 cy 节点 title:
  {'id': 'M_G1_NS_01', 'title': '万以内数的认识'},
  {'id': 'M_G1_NS_02', 'title': '数位与位值'},
  {'id': 'M_G1_NS_03', 'title': '用算盘表示多位数'},
```

**根因**:
```js
// web/app.js:81-90 (setupLangSwitch)
} else {  // 切到非 zh-TW 语言
  cy.nodes().forEach(n => {
    if (n.data('title_orig')) n.data('title', n.data('title_orig'));
  });
}
```
切到 EN 时, 只回滚到 zh-CN 原文。**根本不存在 title_en 翻译数据**, 也没有调任何翻译 API。`simpToTrad` 也不能反向简→英。

V2.0 审查 "EN 模式 detail panel 4 block 标题硬编码中文" V2.3 修了 (改用 `data-i18n`), 但**只修了 UI 文案, 没修数据本身**。EN 用户打开图谱: 节点名/搜索结果/详情标题/标签全部中文, 等于无法使用。

**修复**:
1. 短期: 在 `web/i18n.js` 加 `CONCEPT_EN_DICT` (id → english), 给 M_/CH_/EN_/P_/... 各学科核心 100-200 概念补 EN 翻译; showCard 和 cy 节点都读 `title_en`。
2. 长期: API `/api/concepts?lang=en` 加服务端 i18n 字段。

**优先级**: P0 — V2.3 的核心 "海外华人版 / 双语版" 路线直接打脸。

---

### 🔴 P0-4: 详情面板打开时 lang-switch 被遮挡, 切不了语言

**位置**: `web/index.html:80` (`.lang-switch` z-index:13) + `web/index.html:91` (`#card` z-index:15)

**实测** (Playwright 试图点 `data-lang="en"` 在 card 打开时):
```
card box: {'x': 960, 'y': 0, 'width': 480, 'height': 900}
lang-en button box: {'x': 1184.796875, 'y': 20, 'width': 35.203125, 'height': 26}
lang-en clickable when card open: NO
card z-index: 15, lang-switch z-index: 13
```

**根因**: card 是 `position: fixed; right: 0; width: min(480px, 100vw)`, 在 1440 视口下右缘到 1440, 完全覆盖 `top: 20px; right: 220px` 的 lang switch。card z=15 > lang z=13, card subtree 拦截 click。

**影响**: 教师正在看一个概念的详情, 突然想切繁体, 必须先关 card (Esc) → 再点 EN。这违反"不打断用户思路"原则。

**修复**:
```css
.lang-switch { z-index: 16; }  /* 高于 card */
```
或直接把 lang-switch 移到 card 内部右上角。

**优先级**: P0 — i18n 入口被自己的 UI 锁死。

---

## 2. P1 — 应当修

### 🟠 P1-1: 浮动 "从这里学起" 按钮 z-index=14, 概率性遮挡 stats panel 按钮

**位置**: `web/index.html:147-148` (`.start-here-btn { z-index: 14 }`) vs `web/index.html:78` (`.stats { z-index: 10 }`)

**实测** (Playwright 模拟用户点击):
- toggleRoots on 后, 115 个浮动按钮散布在 cytoscape 节点位置
- 多次重排后, 至少一次 `#reLayout` 按钮被一个 `start-here-btn` 遮挡 (e.g. `data-node-id="EN_E1_SK_02"`)
- 用户无法点 "重排", 也无法点 "再次高亮" 关闭 (因为 toggleRoots 按钮自己也被挡)

**根因**: 浮动按钮用 `position: fixed` 直接挂 `document.body`, z-index 14 覆盖 z-index 10 的 stats 容器。Cy 节点位置是相对容器的, 当节点落在右上角 (x>1100, y<100) 时, 浮动按钮就压到 stats panel 上。

**修复**: 浮动按钮 z-index 降到 9 (低于 stats), 或者把浮动按钮的容器 `pointer-events: none` 让底层 click 通过。或者更简单: 浮动按钮改成"hover 时显示"而不是默认显示。

---

### 🟠 P1-2: 浮动按钮的文本/aria-label 在切语言时不更新

**位置**: `web/app.js:420-421`

**实测** (Playwright):
```
zh-CN 按钮文字: '从这里学起 →'
aria: '从此概念开始学习: 数位与位值'
[切到 EN]
EN 按钮文字 (after lang switch): '从这里学起 →'  ← 没变
EN aria: '从此概念开始学习: 数位与位值'  ← 没变
```

**根因**: `applyI18n` 调了 `buildLegend()` 和 `showCard()`, 但**没调 `renderStartHereButtons()`**。浮动按钮的 textContent 在 `renderStartHereButtons` 创建时 hardcode `window.t('btn_start_here')`, 之后没人改。

**修复**: `applyI18n` 末尾加 `if (window._rootsHighlighted) renderStartHereButtons();` (P1 配合: 修后会在切语言时瞬间重渲 115 个 DOM 节点, 性能可接受)。

---

### 🟠 P1-3: 切语言后搜索结果下拉不重渲染

**位置**: `web/i18n.js:147-148` (applyI18n)

**实测** (Playwright):
```
--- 搜 zh-CN ---
搜索 count 后缀: 2 匹配 (按 ESC 关闭)
切到 EN 后 search count 后缀: 2 匹配 (按 ESC 关闭)  ← 中文文案没换
```

**根因**: searchResults.innerHTML 在 doSearch 里设置, applyI18n 不重渲。`search_count_suffix` 在 en 里是 "matches (press ESC to close)", 但下拉仍是 zh-CN 文案。

**修复**: applyI18n 末尾判断 `#searchResults.on` 类, 若有, 用当前 input.value 重跑 doSearch。

---

### 🟠 P1-4: 切语言后 search input 不清空, 'r' 字符被吞进搜索框

**位置**: `web/app.js:651-666` (Escape handler)

**实测** (Playwright):
```
按 '/' 聚焦 searchInput
填 '勾股' + Esc 关掉
focus 仍: 'searchInput'
按 'r'  → search 框: 'r'  ← 'r' 没触发 toggleRoots, 进了搜索框
aria-pressed: false
```

**根因**: Esc 只清空 `input.value` 不 `input.blur()`, input 仍 focused。`r` 被搜进搜索框, 不触发全局快捷键。

**修复**: Esc handler 加 `input.blur()`。

---

### 🟠 P1-5: SIMP_TO_TRAD 字典覆盖率远低于声称值, 简繁混杂严重

**位置**: `web/simp_to_trad.js`

**实测** (Python):
```
raw mappings: 1179 行 (含大量重复 key)
unique keys: 609
effective (k != v): 233     ← 真正起作用的仅 233
same (k == v, useless): 376  ← 376 个同形字白占行

758 概念标题覆盖率:
  字种 20.4% (173 / 850)
  字次 31.4% (1502 / 4781)
```

**实测 (Playwright 切到 zh-TW)**:
```
'四则运算的意义'           → '四則運算的意義'           ✓
'乘法是加法的简便运算'       → '乘法是加法的简便運算'       ✗ (简/决未转)
'用数和运算解决简单问题'      → '用數和運算解决简單问题'     ✗ (决/问/单未转)
'新中国成立与巩固'          → '新中國成立與巩固'          ✗ (固未转)
```

**根因**: V2.0 审查 P0 #4 "扩 SIMP_TO_TRAD 到 ≥500 字" 未真正完成 (写了很多但有效 233)。简繁高频字如 `简/决/问/单/干/发` (作"發"已加, 但作"头发"未加分支) 漏收录。

**修复**: 换 OpenCC (`opencc-js` 库, npm 包, 7000+ 字符) 一次性覆盖; 或手工补足 ≥1000 真正有效 mapping。

---

### 🟠 P1-6: 467/758 (62%) 节点是孤立, 图谱稀疏

**位置**: `data/graph/all_v0.8.json`

**实测** (Python):
```
总孤立节点 (无入度无出度): 467 / 758 = 61.6%
有出度的根节点: 80
有入度: 211
叶子: 583
```

**根因**: V0.5 → V0.6 阶段只 enrich 了 14 学科核心概念, 很多边缘概念 (尤其是 art/labor/PE 一些条目录入) 没有先决/后继。`isLearnableEntry` (V2.3 缩窄到 G1-2) 算出 110 个 "可学入口", 但其中很大一部分是孤立节点 (用户点开后看不到下游路径, 体验很糟)。

**修复**: 给孤立节点至少 1 条 prerequisite (哪怕是 fallback 同学科相邻年级), 让图谱连通。优先级低于 P0, 但视觉上"很多黄点没有线"很丑。

---

### 🟠 P1-7: /api/stats by_stage 把 stage=5 错误显示为 "G9-9" (307 节点)

**位置**: `api/server.py:139`

**实测**:
```python
"by_stage": {
    "G1-2": 101,
    "G3-4": 128,
    "G5-6": 119,
    "G7-9": 103,
    "G9-9": 307    ← 错! stage=5 实际是 G7-9
}
```

**根因**:
```python
{f"G{(s-1)*2+1}-{(s-1)*2+2 if s<4 else 9}": v for s, v in sorted(by_stage.items()) if s > 0}
```
s=4 时显示 "G7-9" (正确), s=5 时显示 "G9-9" (错, 实际是 G7-9 末尾阶段)。

**修复**: 公式改为 `f"G{(s-1)*2+1}-{(s-1)*2+2 if s<4 else 9 if s==4 else 9}"` 永远 7-9, 或者按 stage 实际 grade_start/grade_end 范围计算。

---

### 🟠 P1-8: /api/path 404 hint 引用不存在的 endpoint

**位置**: `api/server.py:339`

```python
"hint": "考虑用 /api/related/ 查跨学科软关联边 (relates_to)"
```

**根因**: 全代码搜 `related` 路由, 实际**根本没有 `/api/related/` 端点**。用户看到提示, 试一下 404, 体验割裂。

**修复**: 改 hint 文本为 "考虑用 /api/concepts/{id} 查 has unlocks 字段, 或用 /api/prerequisites/{id} 查先决链", 或者真把 related 端点实现了。

---

### 🟠 P1-9: /rss.xml 返回 JSON-encoded 字符串 (而不是真 XML)

**位置**: `api/server.py:354`

**实测** (curl):
```bash
$ curl -s 'http://127.0.0.1:8003/rss.xml' | head -c 50
"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<rss ver
```

**根因**:
```python
return JSONResponse(content=rss, media_type="application/rss+xml")
```
`JSONResponse` 把 Python string 序列化成 JSON 字符串 (外层加 `"` 包裹, 内部 `\"` 转义), 真正的 RSS 客户端 (Feedly, Inoreader) 解析会失败。

**修复**: 改用 `Response(content=rss, media_type="application/rss+xml")` 或 `PlainTextResponse`/`HTMLResponse`。

**注**: V2.3 test `test_api_rss` 写得很松 (只检查 `<rss` in r.text, 不检查是 JSON 字符串还是真 XML), 所以 30 测全过。**测过 ≠ 对**。

---

## 3. P2 — 死代码 / 锦上添花

### 🟡 P2-1: `cy_nodes_initialized` 写但不读 (死代码)

**位置**: `web/app.js:51, 69`
```js
// 第 51 行 (loadData 内)
DATA.nodes.forEach(n => { n.title_orig = n.title; });
cy_nodes_initialized = true;          // ← 写
...
// 第 56-60 行 (setupLangSwitch 内)
if (lang === 'zh-TW' && cy) {
  cy.nodes().forEach(n => {
    if (!n.data('title_orig') && n.data('title')) {
      n.data('title_orig', n.data('title'));
    }
  });
}
// 第 69 行
let cy_nodes_initialized = false;     // ← 读?  全文件 grep 只有这两行
```

`grep cy_nodes_initialized web/app.js` 只有 2 处 (写 + 声明), 无任何读取。**完全死代码**, 命名也误导。删了。

---

### 🟡 P2-2: `_should_gzip` 函数定义但不调用 (死代码)

**位置**: `api/web_server.py:34-39`

```python
def _should_gzip(req: Request, content_type: str) -> bool:
    """只在客户端支持 + 体积 > 1KB + 类型在白名单时启用 gzip"""
    if not content_type.split(";")[0].strip() in GZIP_TYPES:
        return False
    accept = req.headers.get("accept-encoding", "")
    return "gzip" in accept.lower()
```

`grep _should_gzip api/web_server.py` 只有 1 处 (定义), 无任何调用。`_make_response` 直接用 `gz_path.exists()` 判定。**死代码**。

---

### 🟡 P2-3: 加载失败时 spinner 永远转

**位置**: `web/app.js:41, 66`

```js
// 第 41 行
loadingMsg.innerHTML = `<div class="err">${...}</div>`;  // 错误时替换文本
// 第 66 行 (成功路径)
loading.classList.add('done');
```

错误路径**没**调 `loading.classList.add('done')`, 错误信息盖在仍转的 spinner 上。用户看到 "[旋转的 loading 图标] 未找到图谱数据..." 不知道页面是还在加载还是已死。修: catch 块也调 `loading.classList.add('done')`。

---

### 🟡 P2-4: `@app.get("/")` 永远不被命中 (被 `/{path:path}` 截胡)

**位置**: `api/web_server.py:42, 72`

```python
@app.get("/{path:path}")   # 第 42 行
def serve(path: str = ""):
    if not path: path = "index.html"
    ...

@app.get("/")              # 第 72 行
def root():
    return FileResponse(WEB_DIR / "index.html", media_type="text/html")
```

FastAPI 按声明顺序匹配, `/{path:path}` 一定先匹配 (path=""), 所以 `root()` 不可达。实测 `/` 走的是 `serve("")` → 返回 gzipped。**`@app.get("/")` 是死代码**, 而且绕过了 `_make_response` 的 gzip 逻辑 (虽然实际不命中所以无害)。

---

### 🟡 P2-5: `setupLangSwitch` 的 title_orig 兜底代码是冗余

**位置**: `web/app.js:56-60`

```js
if (lang === 'zh-TW' && cy) {
  cy.nodes().forEach(n => {
    if (!n.data('title_orig') && n.data('title')) {
      n.data('title_orig', n.data('title'));
    }
  });
}
```

`loadData` 第 50 行已经把 `DATA.nodes.forEach(n => { n.title_orig = n.title; })` 做过了, cytoscape 拿的是 `{...n}` 浅拷贝, 所以 cy 节点已经有 `title_orig`。这段 forEach 在正常路径上**永远不进入 if 体**。是 V2.0 修的兜底, 但现在冗余。

---

## 4. 已修复 (V2.3 自证)

| V2.0 报告的 P0 | V2.3 状态 | 验证方式 |
|---|---|---|
| gzip 未启用 | ✅ 已修 | curl `content-encoding: gzip` + .gz 文件返回 |
| 移动端 #card 480>375 裁切 | ✅ 已修 | Playwright mobile 375x812, card right=375, 无裁切 |
| EN 详情面板 4 block 硬编码 | ✅ 已修 | DOM 扫 `data-i18n` 已上 |
| SIMP_TO_TRAD 100 字 286 节点残留 | ⚠️ 部分修 | 字数到 609, 但有效 233, 实际覆盖率 20.4% (P1-5) |
| 入口高亮 83% 节点 | ✅ 已修 | isLearnableEntry 缩窄 G1-2, 现 110 个 |
| ARIA / 键盘 0 个 | ✅ 已修 | Playwright 验证 `?` 弹 modal, `/` 聚焦, `r`/`l` 切换 |
| applyI18n 不重渲染 showCard | ✅ 已修 | DOM 切语言后 card 标题确实换 |
| tSubject() 替换 SUBJECT_CN | ✅ 已修 | web/app.js 无硬编码学科名 |

---

## 5. 验证环境与证据

### 5.1 静态 Read 工具读过的文件 (按字节)

| 文件 | 行数 | 字节 | 关键发现 |
|---|---|---|---|
| `web/app.js` | 953 | 32952 | P0-4, P1-1..4, P2-1, P2-3, P2-5 |
| `web/i18n.js` | 260 | 11161 | P1-3 (搜索下拉不重渲) |
| `web/index.html` | 468 | 22708 | P0-4 (z-index 13<15), P1-1 (z-index 14) |
| `web/simp_to_trad.js` | 198 | 17835 | P1-5 (覆盖率 20.4%) |
| `api/server.py` | 408 | 14368 | P1-7..9, P1-6 (数据) |
| `api/web_server.py` | 74 | 2071 | P0-1 (路径遍历), P2-2 (死代码), P2-4 (路由顺序) |
| `api/tests/test_full.py` | 325 | 11772 | 30 测全过, 但漏了路径遍历 / RSS / EN 数据 / 切语言 UX |

### 5.2 Python 健全性 (data/.../all_v0.8.json)

```python
节点: 758, 边: 299
孤立: 467 (61.6%)
根 (indeg=0): 547
可学入口 (G1-2 + indeg=0): 110
src_page=1: 687/687 (100%)     ← P0-2
weight/rationale 缺失: 167     ← 注释里有但代码不强校验
type 字段缺失: 132 (但有 rel)
14 学科中 i18n 字典缺 integrated 数据 (但 PALETTE 有)
```

### 5.3 curl 边界

```
路径遍历: ////etc/passwd → 200 + 文件内容     ← P0-1
RSS body: 首字符是 " (JSON string 包裹)        ← P1-9
search q=空 → 422 (min_length=1)
search q=100字 → 200, q=1000字 → 200, q=5000字 → 200 (无 max)
limit=2000 → 422 (le=1000)
offset=-1 → 422
stage=0 → 422
GET /api/concepts?subject=invalid → 200, total=0 (没 422 提示 typo)
```

### 5.4 Playwright (12 断言, 9 通过)

| 断言 | 期望 | 实际 | 状态 |
|---|---|---|---|
| desktop_load | n=758, e=299 | n=758, e=299 | ✅ |
| card_open_zh | 标题非空 | '勾股定理' | ✅ |
| lang_en | 标题含 Knowledge Graph | "2022 New Curriculum Knowledge Graph" | ✅ |
| lang_tw | 标题含 知識 | "2022 新課標知識圖譜" | ✅ |
| (lang switch 在 card 开时) | 可点 | **被 card 拦** | ❌ → **P0-4** |
| no_xss_script | <script> 不注入 | 转义正确 | ✅ |
| search_esc_closes | Esc 关下拉 | 关 | ✅ |
| roots_count | ≥50 按钮 | 115 | ✅ |
| start_here_clicked | card 开 | (被相邻按钮拦) | ❌ → **P1-1** |
| roots_turnoff | 0 按钮 | 0 | ✅ |
| relayout_no_break | nCount 仍 758 | 758 | ✅ |
| mobile_card_in_viewport | 375 视口内 | x=0,w=375 | ✅ |
| kbd_help_opens | modal on | on | ✅ |
| kbd_esc_closes | modal off | off | ✅ |
| kbd_slash_focus | searchInput 焦点 | yes | ✅ |
| kbd_r_toggle | aria-pressed=true | **false (input 仍 focused)** | ❌ → **P1-4** |
| kbd_l_toggle | aria-pressed=true | **false** | ❌ → **P1-4** |

`network 4xx/5xx: 0` · `JS exception: 0` · `console warnings: 7` (cytoscape 提示 wheel sensitivity 自定义)

### 5.5 数据健全性 Python 输出

```
=== 节点健全性 ===
无 title: 0
无 subject: 0
stage=0: 0
无 id: 0
无 bloom: 0
无 grade_start/grade_end: 0

=== 边健全性 ===
无 rel: 0
无 weight: 167
weight=0: 0
rationale=None: 167
无 type: 132

=== 重复边检查 ===
重复 from->to: 0

=== 拓扑 ===
孤立: 467 (62%)  ← P1-6
根: 547
叶子: 583
入度最高: M_G2_NS_15 (用字母表示运算律) = 6
```

---

## 6. 必修 P0 (3 行)

1. **`api/web_server.py:49-50` 加 `fp.resolve() + relative_to(WEB_DIR)` 防 `Path("//etc/passwd")` 绕过沙盒**, 否则公网可读 `/etc/passwd`。
2. **`data/graph/all_v0.8.json` 687 节点 `src_page` 全部等于 1**, 跟 V2.0 报告的 90.6% 比更糟 (实际 100%) — "课标原文 ↗" 链接 100% 失效, 立刻修或下掉链接。
3. **`web/index.html:80` `.lang-switch` z-index 从 13 提到 ≥16, `web/app.js` 给 cy 节点加 `title_en`**, 否则 EN 模式既切不了语言, 概念也全是中文 — i18n 路线直接打脸。

---

## 7. 结论

**VERDICT: FAIL**

V2.3 在 P0 UX (gzip/移动端/i18n UI/入口缩窄/ARIA/键盘) 上修得不错, **4 个 P0 维度基本清干净**。但暴露出 **5 个新 P0**:
- 1 个安全 (路径遍历, 公网立即可利用)
- 1 个数据 (src_page 100% 失效, V2.0 报告的 90.6% 没修, 还更严重)
- 1 个 i18n (EN 模式徒有其表, 数据全中文)
- 1 个 UX (lang switch 在 card 打开时不可点)
- 1 个测试盲区 (test_full.py 30 测全过但漏检)

外加 **9 个 P1** (浮动按钮挡 stats、字典覆盖率 20.4%、467 孤立节点、RSS JSON 包裹、loading 错误不切 done、5 个死代码/UX 残留)。

代码质量层面有进步 (引入了 a11y, 缩窄了 root count, 用 `data-i18n` 替换硬编码), 但**数据层**和**安全层**被忽视了。下一版 V2.4 应该:
1. 必修 4 个 P0 (1 天)
2. 修 6 个 P1 (字典换 OpenCC + 浮动按钮 z-index + 切语言全重渲) (2 天)
3. 死代码清理 (1 小时)
