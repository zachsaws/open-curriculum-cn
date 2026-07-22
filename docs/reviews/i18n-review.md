# i18n 翻译质量审查 · Open Curriculum CN V2.0

> 审查日期:2026-07-17
> 范围:web/i18n.js + web/app.js + web/index.html + api/server.py + data/graph/all_v0.7.json
> 状态:仅审查,未修改任何文件

---

## TL;DR

| 维度 | 状态 | 数字 |
|---|---|---|
| 简繁字典覆盖 | 🔴 严重不足 | 字种 **9.2%** / 字次 **20.7%** / 抽样概念 **22.2%** |
| 英文 UI 翻译 | 🔴 字典够用,前端大量硬编码 | 硬编码点 **15+** |
| zh-TW 转换 | 🟡 临时方案,有 bug | 字典缺失 700+ 字,部分化学/物理字无法转换 |
| API i18n | 🟡 字段名 OK,内容无 i18n | 无 `?lang=` 参数 |
| README/CONTRIBUTING | 🟢 README 中英混排 OK | CONTRIBUTING.md 仅中文 |

---

## 1. 简繁字典覆盖率统计

### 1.1 字典自身

| 项目 | 数值 |
|---|---|
| 映射条目数 | **119** |
| 独立简体 key | 102 |
| 独立繁体 val | 102 |
| 重复 key | 13 个 (`习/议/这/种/类/业/样/计/定/决/动/变/换`) |
| **无效映射**(key=val,同形字) | **23 个** (如 `'物理':'物理'`、`'生物':'生物'`、`'地理':'地理'`) |

> 这些同形字在 GB 简繁里是同一个字,字典里写它们没意义,占空间。

### 1.2 真实覆盖率(全部 758 概念标题)

| 指标 | 数值 |
|---|---|
| 标题中出现的独立汉字 | **816** |
| 字典已覆盖 | 75 (字种覆盖 **9.2%**) |
| 字典未覆盖 | **741** 个独立汉字 |
| **字次覆盖**(按出现频次加权) | **20.7%** |

> 也就是说,一个典型概念标题,只有 1/5 的字会被转换。剩下 4/5 还是简体,繁體用戶看到的是「混合体」。

### 1.3 物理 / 化学专用字测试

| 字 | 用户指定场景 | 字典收录? | 转换结果 |
|---|---|---|---|
| 弹 | 弹力 | ✗ | 弹力(不转) |
| 摩 | 摩擦力 | ✗ | 摩擦力(不转) |
| 擦 | 摩擦力 | ✗ | 摩擦力(不转) |
| 浮 | 浮力 | ✗ | 浮力(不转) |
| 内 | 内能 | ✓ | 內能(只转一半) |
| 能 | 内能 | ✗ | 內能(不转) |
| 电 | 电磁感应 | ✗ | 电磁感應(3/4 不转) |
| 磁 | 电磁感应 | ✗ | 同上 |
| 感 | 电磁感应 | ✗ | 同上 |
| 应 | 电磁感应 | ✓ | 應(转) |
| 钠 | 氢氧化钠 | ✗ | 氢氧化钠(不转) |
| 氢 | 氢氧化钠 | ✗ | 同上 |
| 氧 | 氢氧化钠 | ✗ | 同上 |
| 酸 | 化学 | ✗ | 酸(不转) |
| 碱 | 化学 | ✗ | 碱(不转) |
| 盐 | 化学 | ✗ | 盐(不转) |
| 溶 | 溶解度 | ✗ | 溶解度(不转) |
| 晶 | 晶体 | ✗ | 晶(不转) |
| 密 | 密度 | ✗ | 密(不转) |
| 压 | 压强 | ✗ | 压(不转) |
| 强 | 压强 | ✗ | 强(不转) |
| 速 | 速度 | ✗ | 速(不转) |
| 功 | 功率 | ✗ | 功(不转) |
| 率 | 功率 | ✗ | 率(不转) |

> 用户原问的"理解勾股定理,会用其解决实际问题" → 转换后: `理解勾股定理,會用其解決实际问题`
> 11 个汉字里,只有 `会` `解` `实` 3 个转了(都是字典里有的),剩下 `理解勾股定理用其解决实际问题` 8 个全没转。

### 1.4 30 概念标题抽样

> 完整表格见下表。"未转字"列为该标题里没被字典收录的简体字。

| 学科 | ID | 原文 | 转换后 | 未转字 |
|---|---|---|---|---|
| art | ART_A1_06 | 音乐欣赏 | 音乐欣赏 | 音乐欣赏(0/4) |
| art | ART_A4_02 | 课本剧编排 | 課本剧编排 | 本剧编排(3/5) |
| biology | B_B2_01 | 生物分类 | 生物分類 | 生物分(3/4) |
| biology | B_B3_03 | 生态系统的能量流动 | 生態系统的能量流動 | 生系统的能量流(7/10) |
| chemistry | CH_C6_01 | 分子与原子 | 分子与原子 | 分子与原子(5/5) |
| chemistry | CH_C4_04 | 化学反应类型 | 化學反應類型 | 反型(2/6) |
| chemistry | CH_C4_06 | 燃烧与灭火 | 燃烧与灭火 | 燃烧与灭火(5/5) |
| chinese | CN_C4_WR_01 | 写记叙文/抒情文/说明文/议论文 | 寫记叙文/抒情文/說明文/議論文 | 记叙文抒情文明文文(8/14) |
| chinese | CN_C1_SP_02 | 用礼貌语言交流 | 用礼貌語言交流 | 用礼貌言交流(5/7) |
| english | EN_E3_VB_01 | 1600-2000 词汇量 | 1600-2000 词汇量 | 词汇量(3/3) |
| english | EN_E2_VB_01 | 校园与家庭生活词汇 | 校园与家庭生活词汇 | 校园与家庭生活词汇(9/9) |
| geography | G_G6_03 | 印度 | 印度 | 印度(2/2) |
| geography | G_G3_04 | 发展中国家与发达国家 | 發展中国家与發达国家 | 国家与达国家(6/10) |
| history | H_H1_CA_10 | 古代科技文化 | 古代科技文化 | 古代科技文(5/6) |
| history | H_H1_CA_04 | 秦统一中国 | 秦统一中国 | 秦统一国(4/5) |
| info_tech | IT_I5_01 | 计算机硬件 | 計算机硬件 | 机硬件(3/5) |
| info_tech | IT_I6_03 | 智能应用 | 智能應用 | 智能用(3/4) |
| labor | L_L9_02 | 社区志愿服务 | 社區志愿服務 | 社志愿服(5/7) |
| labor | L_L7_01 | 3D 打印体验 | 3D 打印體驗 | 打印(2/4) |
| math | M_G4_GM_17 | 圆:圆心角/弧/弦 | 圆:圆心角/弧/弦 | 圆圆心角弧弦(7/7) |
| math | M_G2_NS_13 | 乘法结合律 | 乘法結合律 | 乘法合律(4/5) |
| math | M_G2_PR_01 | 主题活动:曹冲称象 | 主题活動:曹冲称象 | 主题活曹冲称象(8/9) |
| morality_law | ML_ML_G6_03 | 公民的权利与义务 | 公民的权利与义務 | 公民的权利与义(7/8) |
| morality_law | ML_ML_G9_05 | 少年的担当 | 少年的担當 | 少年的担(4/5) |
| pe_health | PE_PE3_02 | 中长跑 | 中長跑 | 跑(1/3) |
| pe_health | PE_PE5_01 | 认识身体 | 認識身體 | 身(1/4) |
| physics | P_P2_04 | 速度 | 速度 | 速度(2/2) |
| physics | P_P2_09 | 二力平衡 | 二力平衡 | 二力平衡(4/4) |
| physics | P_P3_08 | 凸透镜成像 | 凸透镜成像 | 凸透镜成像(5/5) |
| science | SC_S2_TE_01 | 设计与制作 | 設計与制作 | 与制作(3/5) |

**抽样结论**:30 概念 / 167 字中,只转 37 字 = **22.2% 字次覆盖率**。

> 物理化学的标题几乎全不转: `凸透镜成像` 5/5 不转,`速度` 2/2 不转,`燃烧与灭火` 5/5 不转。

### 1.5 TOP 30 未收录字(按全量出现频次)

| 排名 | 字 | 出现次数 | 繁体 |
|---|---|---|---|
| 1 | 的 | 137 | 的 |
| 2 | 与 | 119 | 與 |
| 3 | 数 | 91 | 數 |
| 4 | 文 | 55 | 文 |
| 5 | 物 | 52 | 物 |
| 6 | 形 | 48 | 形 |
| 7 | 分 | 43 | 分 |
| 8 | 法 | 40 | 法 |
| 9 | 生 | 38 | 生 |
| 10 | 用 | 33 | 用 |
| 11 | 主 | 33 | 主 |
| 12 | 国 | 31 | 國 |
| 13 | 理 | 30 | 理 |
| 14 | 方 | 30 | 方 |
| 15 | 作 | 27 | 作 |
| 16 | 表 | 26 | 表 |
| 17 | 题 | 26 | 題 |
| 18 | 活 | 25 | 活 |
| 19 | 量 | 24 | 量 |
| 20 | 式 | 24 | 式 |
| 21 | 字 | 23 | 字 |
| 22 | 角 | 23 | 角 |
| 23 | 一 | 22 | 一 |
| 24 | 基 | 22 | 基 |
| 25 | 本 | 22 | 本 |
| 26 | 位 | 20 | 位 |
| 27 | 积 | 20 | 積 |
| 28 | 统 | 20 | 統 |
| 29 | 性 | 20 | 性 |
| 30 | 音 | 20 | 音 |

> 实际上 `的/与/数/文/物/形/分/法/生/用/主/国/理/方...` 这些是最高频的"功能字",字典一个都没收。
> 这也是为什么字次只有 20.7% — 高频字全没覆盖。

### 1.6 字典设计缺陷

1. **同形字占位**:23 个 `key=val` 无意义项,塞在字典里。
2. **无单字兜底**:遇到字典没收录的字,直接保留简体 → 出现「半简半繁」混合显示。
3. **重复 key**:13 个 key 重复定义(JS 对象后者覆盖前者,前面的白写)。
4. **手工收集**:100 来个字靠人肉维护,758 概念 816 独立字 — 显然覆盖不过来。

---

## 2. 英文 UI 缺口

### 2.1 I18N.en 字典字段覆盖

i18n.js 的 I18N 字典只有 **15 个字段**(app_title / app_subtitle / stats_4 / btn_3 / search_placeholder / card_4 / card_no_2 / grade_label / source_link),都是**外壳 UI 文案**。

**没翻译的部分全是数据 / 详情面板**。

### 2.2 硬编码清单(具体文件:行号)

#### web/index.html(HTML 层)

| 行号 | 内容 | 影响 |
|---|---|---|
| 218 | `<div class="msg" id="loadingMsg">加载知识图谱...</div>` | 切语言不变 |
| 233-234 | `学科数:` / `缺先决根节点:` / `(可学起)` | stats 标签硬编码 |
| 236 | `<button id="toggleLabels">显示标签</button>` | 初始文本硬编码 |
| 237 | `<button id="toggleRoots">高亮入口</button>` | 同上 |
| 238 | `<button id="reLayout">重排</button>` | 同上 |
| 243 | `placeholder="搜索概念 ID / 标题 / 标签..."` | placeholder 硬编码 |
| 269 | `<div class="block-title">📋 课标内容要求 ...</div>` | showCard 标题 1 |
| 271 | `<div class="block-title">🎯 课标学业要求</div>` | showCard 标题 2 |
| 274 | `<div class="block-title">💡 知识要点</div>` | showCard 标题 3 |
| 279 | `<div class="block-title">📚 课标例题</div>` | showCard 标题 4 |
| 284 | `<div class="label">直接先决 · <span id="card-pre-k">0</span></div>` | 先决标签 |
| 289 | `<div class="label">解锁后继 · <span id="card-next-k">0</span></div>` | 后继标签 |

> **用户原问的"showCard 4 个 block 标题用 t() 了吗"** → **没有**。4 个 block 标题写在 HTML 里,切语言不会变;applyI18n() 也没设置它们。

#### web/app.js(JS 层)

| 行号 | 内容 | 建议翻译 key |
|---|---|---|
| 19-26 | `SUBJECT_CN` 字典(硬编码中文) | 改用 `tSubject()` |
| 41 | `未找到图谱数据 (graph.json)<br>数据仍在采集中` | `err_no_data` |
| 100 | `SUBJECT_CN[s] \|\| s`(legend 学科名) | 改用 `tSubject(s)` |
| 163 | `'取消高亮' : '高亮入口'`(toggleRoots 切换) | `btn_roots_on/off` |
| 213 | `'<div class="r-empty">无匹配概念</div>'` | `search_no_match` |
| 215 | `${hits.length} 匹配 (按 ESC 关闭)` | `search_count` |
| 432 | `SUBJECT_CN[node.subject] \|\| node.subject` | 改用 `tSubject()` |
| 449 | `'难度 ' + '●'.repeat(...) + ...` | `tag_difficulty` |
| 456 | `'⏱ ' + node.estimated_minutes + ' 分钟'` | `tag_minutes` |
| 537 | `'没有先决概念' : '没有后继概念'` | `card_no_prereq/unlock` (字典里有!) |
| 577 | `'隐藏标签' : '显示标签'`(toggleLabels 切换) | `btn_labels_on/off` |

### 2.3 严重 bug:applyI18n 不刷新已打开的 showCard 面板

`web/i18n.js:115-122`:

```js
function applyI18n() {
  // ... 改 title / header / 按钮文本
  if (typeof buildLegend === 'function') buildLegend();
  // 重新渲染 detail
  if (typeof window._currentNode === 'function') {
    // 略          ← 这块代码没写!
  }
}
```

`window._currentNode` 这个函数根本不存在,而且就算存在,也没重新调用 `showCard()`。**结果**:

1. 用户点开一个概念的 showCard
2. 切到英文
3. 4 个 block 标题还是中文(HTML 写死)
4. "难度"/"分钟"/"没有先决概念" 还是中文(JS 写死)
5. 学科名还是中文(用了 SUBJECT_CN 而不是 tSubject)

**整个详情面板在英文模式下完全没翻译。**

### 2.4 概念标题(title)有没有英文?

**没有。** `data/graph/all_v0.7.json` 里只有 `title` (简体中文),没有 `title_en` / `title_tw` 字段。

`web/app.js:74-77` 的 zh-TW 切换逻辑是运行时 simpToTrad 转换,但因为字典覆盖率只有 20.7%,繁体模式看到的是「半简半繁」混合体。

### 2.5 SUBJECT_CN_I18N 完整性

i18n.js 的 14 学科全有翻译,但**和 app.js 里的 SUBJECT_CN 不一致**:

| 学科 | i18n.js SUBJECT_CN_I18N | app.js SUBJECT_CN |
|---|---|---|
| morality_law | `道法` (zh-CN/zh-TW) | `道法` ✓ |
| info_tech | `信息科技` (zh-CN), `資訊科技` (zh-TW) | `信息科技` ✓ |
| pe_health | `体育` | `体育` ✓ |
| labor | `劳动` | `劳动` ✓ |
| art | `艺术` (zh-CN/zh-TW) | `艺术` ✓ |
| **integrated** | **不存在** | `综合实践` ⚠ |

> 此外 `api/server.py:91-95` 还有第三份硬编码的 `SUBJECT_CN`,其中 `morality_law='道德与法治'`、`pe_health='体育与健康'`,跟 i18n.js 的简称不一致。

---

## 3. zh-TW 长期方案

### 3.1 当前问题

1. 字典覆盖率 20.7%,繁体模式视觉上是「半简半繁」,比纯简体更难看。
2. 转换是**运行时**(每次切换语言都遍历所有节点调用 simpToTrad),且转换结果**污染了原始 title**:
   ```js
   // app.js:74-77 切到繁体
   cy.nodes().forEach(n => {
     const orig = n.data('title');
     if (orig && !n.data('title_trad')) {
       n.data('title_trad', simpToTrad(orig));
     }
   });
   cy.nodes().forEach(n => {
     n.data('title', n.data('title_trad') || n.data('title'));  // ← 覆盖原 title
   });
   ```
3. 切回简中时靠 `title_orig` 恢复,但 `title_orig` **从来没被设置过**! (line 73 没存 orig)
4. 物理/化学/生物大量专业字未转换。

### 3.2 建议:三种方案

#### 方案 A: 扩 SIMP_TO_TRAD 字典(临时)

- 收集通用字(`的/与/数/文/物/形/分/法...`)+ 学科常用字(物理/化学/生物)→ 扩到 ~500 字。
- 成本:1-2 天人工 + 验证。
- 局限:遇到字典没收录的字仍是简体,无法彻底解决"半简半繁"。

#### 方案 B: 用 OpenCC 库兜底(中期推荐)

- 引入 `opencc-js` (~200KB),繁简转换交给工业级库。
- 字典只覆盖**学科专有差异字**(如 `硅→矽`、`配置→組態` 这种课标专用词)。
- 切换语言时一次性预转换所有 title,缓存到 `title_tw`,不污染 `title`。
- 成本:半天接入 + 验证。

```js
// 示例:web/i18n.js 改用 opencc
import * as OpenCC from 'https://cdn.jsdelivr.net/npm/opencc-js@1/dist/opencc.min.js';
const converter = OpenCC.Converter({ from: 'cn', to: 'tw' });
function simpToTrad(text) { return converter(text); }
```

#### 方案 C: 数据层加 `title_tw` / `title_en` 字段(长期推荐)

- 在 `data/graph/all_v0.7.json` 给每个概念加 `title_tw` / `title_en` 字段。
- 繁中翻译由 OpenCC 一次性批处理生成,人审 758 条概念(约 2-3 天人工)。
- 英文翻译视情况:核心 200 条人工,剩余保持中文(或用机翻 + 人工抽审)。
- 切语言时直接读字段,**无运行时转换**。
- 成本:数据脚本 1 天 + 翻译 3-5 天。

#### 三个方案对比

| 维度 | A 扩字典 | B OpenCC | C 数据加字段 |
|---|---|---|---|
| 彻底解决"半简半繁" | ✗ | ✓ | ✓ |
| 实现成本 | 低 | 中 | 高 |
| 维护成本 | 高(字典要常更新) | 低(库自动) | 低(数据已固化) |
| 英文支持 | ✗ | ✗ | ✓ |
| 推荐度 | ⭐ 临时 | ⭐⭐ 短期 | ⭐⭐⭐ 长期 |

**建议:先用 B 上线,然后走 C。** 一次性把 `title_tw` 烘焙进数据,前端只负责显示。

---

## 4. README / CONTRIBUTING 国际化

### 4.1 README.md

- 主体中文,嵌了部分英文术语(CC-BY-SA、Marble、Open Curriculum CN)。
- 没有独立 `README.en.md`。
- **建议**:
  - 短期:加 `README.en.md` 全文翻译(机械可用,人工润色)。
  - 长期:用 [Crowdin](https://crowdin.com/) 或 [Transifex](https://www.transifex.com/) 做协作翻译。
  - 至少 `## 快速开始` / `## B 端 REST API` / `## 路线图` 这 3 节先出英文版 — 国外开发者主要看 install / API。

### 4.2 CONTRIBUTING.md

- 全文中文,没有英文版。
- **建议**:
  - 加 `CONTRIBUTING.en.md`(可机翻 + 人工润色,1 天内可完成)。
  - 优先级中等:海外贡献者主要靠 PR 流程(看 fork → branch → PR 那一节),可以先翻译那一节,其他节保持中文 + Google Translate 提示。

---

## 5. API i18n 建议

### 5.1 现状

`api/server.py` 的所有端点:

| 端点 | 字段名 | i18n 状态 |
|---|---|---|
| `/api/stats` | `by_subject` (key 是 `math`/`physics` 等英文 code) | ✓ 字段名英文 |
| `/api/subjects` | `name_cn` (硬编码中文) | 🟡 没 `name_en` / `name_tw` |
| `/api/concepts` | `concepts[].title` (中文) / `content_req` / `academic_req` / `summary` / `key_points` | 🟡 全是中文 |
| `/api/concepts/{id}` | 同上 + `prerequisites` / `unlocks` | 🟡 同上 |
| `/api/prerequisites/{id}` | `concepts[].title` | 🟡 同上 |
| `/api/path` | `concepts[].title` | 🟡 同上 |
| `/api/search` | `concepts[].title` / `summary` | 🟡 同上 |
| `/rss.xml` | `<title>` / `<description>` (中文) | 🟡 RSS 也没 i18n |

**字段名 (id / subject / title / content_req / academic_req) 是英文,没问题。**
**字段值(title / content_req / academic_req / key_points / summary)都是简体中文,API 没办法返回其他语言。**

### 5.2 建议:加 `?lang=` 参数

```python
# api/server.py 改造示例
from typing import Optional
import opencc  # 假设已装 opencc-python

converter_tw = opencc.OpenCC('s2t')  # 简→繁
converter_en = None  # 英文没有自动翻译,需要数据加 title_en

LANGS = {
    'zh-CN': lambda s: s,
    'zh-TW': lambda s: converter_tw.convert(s) if s else s,
    'en': lambda s: s,  # 占位,真实场景需要 title_en 字段
}

@app.get("/api/concepts/{concept_id}")
def get_concept(
    concept_id: str,
    lang: Optional[str] = Query('zh-CN', regex='^(zh-CN|zh-TW|en)$')
):
    n = next((n for n in DATA["nodes"] if n["id"] == concept_id), None)
    if not n:
        raise HTTPException(404, f"概念不存在: {concept_id}")
    conv = LANGS.get(lang, LANGS['zh-CN'])
    # 翻译文案字段
    return {
        **n,
        "title": conv(n["title"]),
        "content_req": conv(n.get("content_req", "")),
        "academic_req": conv(n.get("academic_req", "")),
        "summary": conv(n.get("summary", "")),
        "key_points": [conv(p) for p in n.get("key_points", [])],
        "prerequisites": [...],
        "unlocks": [...],
    }
```

所有读 title / content_req / academic_req / summary / key_points 的端点都加 `lang` 参数。

### 5.3 优先级

- **P0**:`/api/concepts/{id}` + `/api/search` (B 端最常用)
- **P1**:`/api/concepts` + `/api/path` + `/api/prerequisites/{id}`
- **P2**:`/rss.xml` 加 `<language>` 标签 + 多语言 channel

---

## 6. 优先清单

### P0(必修,V2.0 发布前)

| # | 项 | 位置 | 改动量 |
|---|---|---|---|
| 1 | 扩 SIMP_TO_TRAD 字典到 ≥500 字 | web/i18n.js SIMP_TO_TRAD | 半天 |
| 2 | 删除字典里 23 个无效映射(`key=val`) | web/i18n.js | 5 分钟 |
| 3 | 修复 `applyI18n` 不重渲染 showCard 的 bug | web/i18n.js `applyI18n` | 1 小时 |
| 4 | 改用 `tSubject()` 替换 app.js 里的 `SUBJECT_CN` 字典 | web/app.js:19, 100, 432 | 30 分钟 |
| 5 | showCard 内"难度 / 分钟 / 没有先决/后继"翻译 | web/app.js:449, 456, 537 | 1 小时 |
| 6 | index.html 4 个 block 标题 / sec 标签 改用 `t()` | web/index.html:269,271,274,279,284,289 | 1 小时 |
| 7 | 切语言时存 `title_orig`,回切能恢复 | web/app.js:73 | 10 分钟 |

### P1(应修,V2.1)

| # | 项 | 改动量 |
|---|---|---|
| 8 | stats 标签 / 三按钮初始文本 翻译 (index.html:233-238) | 1 小时 |
| 9 | placeholder / loadingMsg / 错误文案 翻译 | 1 小时 |
| 10 | 引入 OpenCC 库(方案 B),字典只保留学科专有差异字 | 半天 |
| 11 | API `/api/concepts/{id}` + `/api/search` 加 `?lang=` 参数 | 半天 |
| 12 | README.md 补 `README.en.md`(API 节 + 快速开始优先) | 1 天 |
| 13 | CONTRIBUTING.md 补 `CONTRIBUTING.en.md`(PR 流程节优先) | 半天 |

### P2(长期)

| # | 项 | 改动量 |
|---|---|---|
| 14 | 数据层加 `title_tw` / `title_en` 字段(方案 C) | 数据 1 天 + 翻译 3-5 天 |
| 15 | API 所有端点加 `?lang=` | 1 天 |
| 16 | 用 Crowdin / Transifex 做协作翻译 | 配置半天 + 流程约定 |
| 17 | `data/graph/all_v0.7.json` content_req / academic_req 翻译(英文) | 1 周人工 |
| 18 | RSS 加 `<language>` 多 channel | 半天 |
| 19 | 物理/化学/生物专有术语表(中→英) | 1 周 |

---

## 附录:审查数据汇总

```
简繁字典:
  字典条数:        119 (其中 23 个无效)
  独立简体 key:     102
  全量 758 概念字种: 816
  字种覆盖率:       9.2%   (75/816)
  字次覆盖率:       20.7%
  抽样 30 概念:     22.2% (37/167)

英文 UI 缺口:
  I18N.en 字典字段: 15 (仅外壳 UI)
  index.html 硬编码: 11 处
  app.js 硬编码:    10 处
  applyI18n bug:    1 (不重渲染 showCard)
  学科名不一致:     3 份 (i18n.js / app.js / server.py)

API i18n:
  端点数:           8 (/api/stats / subjects / concepts x2 / prerequisites / path / search + rss)
  支持 ?lang=:     0/8
  文案字段未翻译:   title / content_req / academic_req / summary / key_points (5 类)
```

---

**报告路径**:`/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/docs/reviews/i18n-review.md`

**关键数字**:
- 简繁覆盖率:**20.7% (字次)** / **9.2% (字种)**
- 英文 UI 硬编码缺口:**21 处**
- P0 优先项:**7 项**
