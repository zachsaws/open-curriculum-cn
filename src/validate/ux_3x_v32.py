"""
V3.2 UI/UX 3 倍镜深度评测 - Playwright 自动化
- 8 个场景全部跑
- 每个场景截图为 data/screenshots/v32-ux-{scenario}.png
- 输出 JSON 报告到 /tmp/ux_3x_report.json
- console errors / pageerrors 全部捕获
"""
import json
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

OUT = Path("/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/data/screenshots")
OUT.mkdir(parents=True, exist_ok=True)
REPORT = Path("/tmp/ux_3x_report.json")

PUBLIC_URL = "https://vnbke2vo1l8z4.space.mcode.cn/"

# 全局收集
all_console = []
all_pageerrors = []
all_issues = []
findings = {}


def log(msg, level="info"):
    print(f"  [{level}] {msg}", flush=True)


def screenshot(page, name, full_page=False):
    p = OUT / f"v32-ux-{name}.png"
    page.screenshot(path=str(p), full_page=full_page)
    log(f"📸 {p.name}")
    return str(p)


def wait_loaded(page, timeout=30000):
    """等图谱加载完成"""
    page.wait_for_function(
        "window.DATA && window.DATA.nodes && window.DATA.nodes.length > 0",
        timeout=timeout,
    )
    page.wait_for_timeout(2000)  # 等布局稳定


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = ctx.new_page()

        page.on("console", lambda m: (
            all_console.append({"type": m.type, "text": m.text[:300]}),
            log(f"console.{m.type}: {m.text[:200]}", level=m.type) if m.type in ("error", "warning") else None,
        ))
        page.on("pageerror", lambda e: (
            all_pageerrors.append({"error": str(e)[:500]}),
            log(f"pageerror: {str(e)[:200]}", level="pageerror"),
        ))

        # ==================== 场景 1: 冷启动首屏 ====================
        log("\n=== 场景 1: 冷启动首屏 ===")
        t0 = time.time()
        page.goto(PUBLIC_URL, wait_until="domcontentloaded", timeout=30000)
        t_dom = time.time() - t0
        log(f"DOM 加载完成: {t_dom*1000:.0f}ms")

        # 0.5 秒截图 (白屏焦虑检查)
        page.wait_for_timeout(500)
        screenshot(page, "01a_loading_500ms")

        # 1.5 秒截图
        page.wait_for_timeout(1000)
        screenshot(page, "01b_loading_1500ms")

        # 等图谱完全加载
        wait_loaded(page, timeout=30000)
        t_full = time.time() - t0
        log(f"图谱完全加载: {t_full*1000:.0f}ms")

        # 检查 loading 状态
        loading_state = page.evaluate("""() => ({
            hasLoading: !!document.getElementById('loading'),
            loadingDone: document.getElementById('loading')?.classList.contains('done'),
            loadingMsg: document.getElementById('loadingMsg')?.textContent,
            loadingOpacity: window.getComputedStyle(document.getElementById('loading')).opacity,
        })""")
        findings["scenario1_loading"] = loading_state
        log(f"Loading 状态: {loading_state}")

        # 首屏完整截图
        screenshot(page, "01c_first_screen")

        # 测量关键渲染时间
        perf = page.evaluate("""() => {
            const nav = performance.getEntriesByType('navigation')[0];
            const res = performance.getEntriesByType('resource');
            return {
                domContentLoaded: nav?.domContentLoadedEventEnd,
                loadComplete: nav?.loadEventEnd,
                domInteractive: nav?.domInteractive,
                graphJsonSize: res.find(r => r.name.includes('graph.json'))?.transferSize,
                graphJsonDuration: res.find(r => r.name.includes('graph.json'))?.duration,
                cytoscapeSize: res.find(r => r.name.includes('cytoscape'))?.transferSize,
                appJsSize: res.find(r => r.name.includes('app.js'))?.transferSize,
            };
        }""")
        findings["scenario1_perf"] = perf
        log(f"性能指标: {perf}")

        # ==================== 场景 2: 概念地图模式 ====================
        log("\n=== 场景 2: 概念地图模式 (V3.1 特色) ===")
        page.wait_for_timeout(1500)
        toggle_mode = page.locator("#toggleMode")
        log(f"切换按钮存在: {toggle_mode.count() > 0}")
        log(f"切换按钮位置: {toggle_mode.bounding_box()}")
        log(f"切换按钮文字: {toggle_mode.text_content()}")
        toggle_mode.click()
        page.wait_for_timeout(800)
        screenshot(page, "02a_map_mode_initial")

        # 检查树渲染
        tree_state = page.evaluate("""() => ({
            subjectRows: document.querySelectorAll('#map-tree .tn-row.s').length,
            stageRows: document.querySelectorAll('#map-tree .tn-row.stg').length,
            domainRows: document.querySelectorAll('#map-tree .tn-row.d').length,
            conceptRows: document.querySelectorAll('#map-tree .tn-row.c').length,
            mapPanelVisible: document.getElementById('map-panel')?.offsetWidth > 0,
        })""")
        findings["scenario2_tree_initial"] = tree_state
        log(f"树初始状态: {tree_state}")

        # 测试 "全部展开" 按钮
        page.locator("#mapExpandAll").click()
        page.wait_for_timeout(500)
        tree_expanded = page.evaluate("""() => ({
            conceptRows: document.querySelectorAll('#map-tree .tn-row.c').length,
        })""")
        log(f"全部展开后: {tree_expanded}")
        screenshot(page, "02b_map_expand_all")

        # 测试搜索 → 树节点定位
        page.locator("#searchInput").fill("万以内")
        page.wait_for_timeout(500)
        search_state = page.evaluate("""() => ({
            searchResults: document.querySelectorAll('.search .r-item').length,
            highlightedInCy: window.cy ? window.cy.nodes('.search-hit').length : 0,
        })""")
        log(f"搜索 '万以内' 后: {search_state}")
        screenshot(page, "02c_map_search_1")

        # 关闭搜索
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

        # 测试 "只看本分支"
        # 先展开到学科 → 学段 → 领域
        page.locator("#mapCollapseAll").click()
        page.wait_for_timeout(300)
        # 展开数学
        math_row = page.locator("#map-tree .tn-row.s").first
        math_row.click()
        page.wait_for_timeout(300)
        # 展开第一个学段
        page.locator("#map-tree .tn-row.stg").first.click()
        page.wait_for_timeout(300)
        # 展开第一个领域
        page.locator("#map-tree .tn-row.d").first.click()
        page.wait_for_timeout(300)
        # 点击第一个概念
        first_concept = page.locator("#map-tree .tn-row.c").first
        if first_concept.count() > 0:
            first_concept.click()
            page.wait_for_timeout(800)
        screenshot(page, "02d_map_concept_clicked")
        cy_branch = page.evaluate("""() => {
            if (!window.cy) return null;
            return {
                branchHL: window.cy.nodes('.branch-hl').length,
                branchDim: window.cy.nodes('.branch-dim').length,
                totalNodes: window.cy.nodes().length,
            };
        }""")
        findings["scenario2_branch_highlight"] = cy_branch
        log(f"分支高亮状态: {cy_branch}")

        # 测 "只看本分支" toggle
        branch_only_btn = page.locator("#mapBranchOnly")
        log(f"只看本分支按钮文字: {branch_only_btn.text_content()}")
        branch_only_btn.click()
        page.wait_for_timeout(500)
        screenshot(page, "02e_map_branch_only")
        cy_branch_only = page.evaluate("""() => ({
            branchHL: window.cy.nodes('.branch-hl').length,
            branchDim: window.cy.nodes('.branch-dim').length,
            totalNodes: window.cy.nodes().length,
        })""")
        log(f"切换后: {cy_branch_only}")
        # 切回
        branch_only_btn.click()
        page.wait_for_timeout(300)

        # 关闭概念地图模式
        page.locator("#toggleMode").click()
        page.wait_for_timeout(500)

        # ==================== 场景 3: 概念详情卡 ====================
        log("\n=== 场景 3: 概念详情卡 ===")
        # 通过 cy 编程点击一个节点
        clicked = page.evaluate("""() => {
            if (!window.cy) return false;
            // 找一个有完整数据的节点: 万以内数的认识
            const n = window.cy.getElementById('M_G1_NS_01');
            if (n.length) {
                n.emit('tap');
                return n.data('title');
            }
            return false;
        }""")
        log(f"点击节点: {clicked}")
        page.wait_for_timeout(1000)
        screenshot(page, "03a_card_wannei")

        # 检查卡片所有字段
        card_fields = page.evaluate("""() => {
            const card = document.getElementById('card');
            const visible = card.classList.contains('on');
            const ctl = document.getElementById('card-ctl')?.textContent;
            const cs = document.getElementById('card-cs')?.textContent;
            const tags = Array.from(document.querySelectorAll('#card-tags .tag')).map(t => t.textContent);
            const contentReq = document.getElementById('card-content-req')?.textContent;
            const academicReq = document.getElementById('card-academic-req')?.textContent;
            const keyPoints = Array.from(document.querySelectorAll('#card-key-points .kp')).map(k => k.textContent);
            const examples = Array.from(document.querySelectorAll('#card-examples .ex')).map(e => e.textContent);
            const preRows = Array.from(document.querySelectorAll('#card-pre-rows .row')).map(r => r.textContent);
            const nextRows = Array.from(document.querySelectorAll('#card-next-rows .row')).map(r => r.textContent);
            const pageLink = document.getElementById('card-page-link')?.textContent;
            return {
                visible, ctl, cs, tags, contentReq: contentReq?.slice(0, 100),
                academicReq: academicReq?.slice(0, 100),
                keyPoints, examples, preRows: preRows.slice(0, 5),
                nextRows: nextRows.slice(0, 5),
                pageLink,
                hasAssessmentPrompt: !!document.querySelector('[id*="assessment"]'),
                hasReason: !!document.querySelector('[id*="reason"]'),
                hasRelatesTo: !!document.querySelector('[id*="relates"]'),
                cardHTML: card.innerHTML.length,
            };
        }""")
        findings["scenario3_card_fields"] = card_fields
        log(f"卡片字段: {json.dumps(card_fields, ensure_ascii=False, indent=2)[:1500]}")

        # 关键检查: assessment_prompt 是否有 {{name}} 占位符在 UI 中显示
        if not card_fields.get('hasAssessmentPrompt'):
            all_issues.append({
                "severity": "P0",
                "scenario": 3,
                "issue": "assessment_prompt 字段未在详情卡中显示 (数据有 {{name}} 占位符模板)",
                "data": "M_G1_NS_01.assessment_prompt = '在数学课上，{{name}}能否理解...'",
                "evidence": "showCard() 中无 assessment_prompt 渲染代码",
            })

        # 关键检查: reason 字段在 edges 中有但 UI 中没显示
        if not card_fields.get('hasReason'):
            all_issues.append({
                "severity": "P0",
                "scenario": 3,
                "issue": "边 reason (4736 条数据有) 未在先决/后继列表中显示",
                "evidence": "fillRows() 只显示 title 和 grade, 无 reason",
            })

        # 关键检查: relates_to 软关联 (2628 条) 未显示
        if not card_fields.get('hasRelatesTo'):
            all_issues.append({
                "severity": "P0",
                "scenario": 3,
                "issue": "relates_to 跨学科软关联 (2628 条) 完全未展示",
                "evidence": "card 模板中无 '跨学科关联' 区块",
            })

        # 检查移动端卡片显示 (用小 viewport 测)
        ctx_mobile = browser.new_context(
            viewport={"width": 375, "height": 812},
            device_scale_factor=2,
        )
        page_m = ctx_mobile.new_page()
        page_m.goto(PUBLIC_URL, wait_until="networkidle", timeout=30000)
        page_m.wait_for_function(
            "window.DATA && window.DATA.nodes && window.DATA.nodes.length > 0",
            timeout=30000,
        )
        page_m.wait_for_timeout(2000)
        # 点击节点
        page_m.evaluate("""() => {
            const n = window.cy.getElementById('M_G1_NS_01');
            if (n.length) n.emit('tap');
        }""")
        page_m.wait_for_timeout(1000)
        mobile_card = page_m.evaluate("""() => {
            const card = document.getElementById('card');
            const rect = card.getBoundingClientRect();
            const vw = window.innerWidth;
            const vh = window.innerHeight;
            return {
                cardWidth: rect.width,
                cardHeight: rect.height,
                visible: card.classList.contains('on'),
                fitsInViewport: rect.width <= vw && rect.height <= vh,
                vw, vh,
                right: rect.right,
                cardCssWidth: window.getComputedStyle(card).width,
            };
        }""")
        findings["scenario3_mobile_card"] = mobile_card
        log(f"移动端卡片: {mobile_card}")
        screenshot(page_m, "03b_card_mobile_375")
        ctx_mobile.close()

        # 继续主页面
        # 关闭卡片
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

        # ==================== 场景 4: 键盘快捷键 ====================
        log("\n=== 场景 4: 键盘快捷键 ===")
        # 先确保搜索框无焦点, 在画布上
        page.locator("#cy-container").click()
        page.wait_for_timeout(200)

        kb_results = {}

        # 测试 / 聚焦搜索框
        page.keyboard.press("/")
        page.wait_for_timeout(200)
        focused = page.evaluate("() => document.activeElement?.id")
        kb_results["slash"] = focused == "searchInput"
        log(f"/ 快捷键 → focus on: {focused}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        # 测试 ? 打开 modal (先确保 focus 在 body 而非 input)
        page.locator("#cy-container").click()
        page.wait_for_timeout(200)
        page.evaluate("() => document.activeElement?.blur()")
        page.wait_for_timeout(100)
        page.keyboard.press("?")
        page.wait_for_timeout(300)
        kbd_modal_visible = page.evaluate("() => document.getElementById('kbdModal')?.classList.contains('on')")
        kb_results["question_mark"] = kbd_modal_visible
        log(f"? 快捷键 → modal 打开: {kbd_modal_visible}")
        screenshot(page, "04a_kbd_modal")
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        # 测试 ? 在搜索框聚焦时 (按设计不触发, 但用户体验上这是死循环)
        page.locator("#searchInput").click()
        page.wait_for_timeout(200)
        page.keyboard.press("?")
        page.wait_for_timeout(300)
        # 此时按设计应不触发 modal (input 抢键), 但用户也无从知道有快捷键
        kb_results["question_mark_in_input"] = "skipped_by_design"
        log(f"? 在 input 内 → 设计跳过, 但用户无视觉提示快捷键存在")
        page.locator("#cy-container").click()
        page.wait_for_timeout(200)
        page.evaluate("() => document.activeElement?.blur()")
        page.wait_for_timeout(100)

        # 测试 1-9 数字键 (确保 focus 在 cy-container 而非 input)
        page.locator("#cy-container").click()
        page.wait_for_timeout(200)
        page.evaluate("() => document.activeElement?.blur()")
        page.wait_for_timeout(100)
        for i in range(1, 10):
            before = page.evaluate(f"""() => {{
                const c = document.querySelector('.chip[data-idx="{i-1}"]');
                return c?.classList.contains('off');
            }}""")
            page.keyboard.press(str(i))
            page.wait_for_timeout(150)
            after = page.evaluate(f"""() => {{
                const c = document.querySelector('.chip[data-idx="{i-1}"]');
                return c?.classList.contains('off');
            }}""")
            kb_results[f"key_{i}"] = before != after
            log(f"  按键 {i}: {before} → {after} (toggle 工作: {before != after})")
            # 再按一次还原
            page.keyboard.press(str(i))
            page.wait_for_timeout(100)

        # 测试 0 全部 toggle
        before0 = page.evaluate("""() => {
            const chips = document.querySelectorAll('.chip');
            return Array.from(chips).filter(c => c.classList.contains('off')).length;
        }""")
        page.keyboard.press("0")
        page.wait_for_timeout(200)
        after0 = page.evaluate("""() => {
            const chips = document.querySelectorAll('.chip');
            return Array.from(chips).filter(c => c.classList.contains('off')).length;
        }""")
        kb_results["key_0"] = before0 != after0
        log(f"0 键: 隐藏 {before0} → {after0}")
        page.keyboard.press("0")
        page.wait_for_timeout(200)

        # 测试 l 标签切换
        before_l = page.evaluate("() => document.getElementById('toggleLabels').textContent")
        page.keyboard.press("l")
        page.wait_for_timeout(200)
        after_l = page.evaluate("() => document.getElementById('toggleLabels').textContent")
        kb_results["key_l"] = before_l != after_l
        log(f"l 键: '{before_l}' → '{after_l}'")
        page.keyboard.press("l")
        page.wait_for_timeout(200)

        # 测试 r 入口高亮
        before_r = page.evaluate("() => window._rootsHighlighted")
        page.keyboard.press("r")
        page.wait_for_timeout(500)
        after_r = page.evaluate("() => window._rootsHighlighted")
        kb_results["key_r"] = before_r != after_r
        log(f"r 键: 高亮 {before_r} → {after_r}")
        page.keyboard.press("r")
        page.wait_for_timeout(300)

        # 测试 R 大写
        before_R = page.evaluate("() => document.getElementById('reLayout').textContent")
        page.keyboard.press("Shift+R")
        page.wait_for_timeout(800)
        # R 触发重排, 不会改文字, 看是否 console 有 action
        kb_results["key_R"] = "skip"  # R 是 layout 触发, 难以从 DOM 验证, 记录到 console
        log(f"R 键: 触发重排 (无 DOM 变化可验证)")

        # 测试 Esc
        # 先打开一个 card
        page.evaluate("() => { const n = window.cy.getElementById('M_G1_NS_01'); if (n.length) n.emit('tap'); }")
        page.wait_for_timeout(500)
        esc_before_card = page.evaluate("() => document.getElementById('card').classList.contains('on')")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        esc_after_card = page.evaluate("() => document.getElementById('card').classList.contains('on')")
        kb_results["key_esc"] = esc_before_card and not esc_after_card
        log(f"Esc 键: card {esc_before_card} → {esc_after_card}")

        findings["scenario4_keyboard"] = kb_results
        log(f"键盘测试结果: {json.dumps(kb_results, ensure_ascii=False)}")

        failed_keys = [k for k, v in kb_results.items() if v is False]
        if failed_keys:
            all_issues.append({
                "severity": "P1",
                "scenario": 4,
                "issue": f"键盘快捷键不响应: {', '.join(failed_keys)}",
                "evidence": f"测试结果: {kb_results}",
            })

        # ==================== 场景 5: i18n 切换 ====================
        log("\n=== 场景 5: i18n 切换 ===")
        # 切到繁體
        page.locator("#lang-zh-TW").click()
        page.wait_for_timeout(500)
        tw_state = page.evaluate("""() => ({
            statsConcepts: document.querySelector('[data-i18n=\"stats_concepts\"]')?.textContent,
            mapTitle: document.querySelector('[data-i18n=\"map_title\"]')?.textContent,
            cyNodeCount: window.cy?.nodes().length,
            sampleTitle: window.cy ? window.cy.getElementById('M_G1_NS_01').data('title') : null,
        })""")
        findings["scenario5_zh_TW"] = tw_state
        log(f"切到 zh-TW: {tw_state}")
        screenshot(page, "05a_lang_zh_tw")

        # 切到 en
        page.locator("#lang-en").click()
        page.wait_for_timeout(500)
        en_state = page.evaluate("""() => ({
            statsConcepts: document.querySelector('[data-i18n=\"stats_concepts\"]')?.textContent,
            mapTitle: document.querySelector('[data-i18n=\"map_title\"]')?.textContent,
            sampleTitle: window.cy ? window.cy.getElementById('M_G1_NS_01').data('title') : null,
        })""")
        findings["scenario5_en"] = en_state
        log(f"切到 en: {en_state}")
        screenshot(page, "05b_lang_en")

        # 检查概念标题是否被翻译 (en 下应仍为中文, 因为没有 en 翻译)
        if en_state.get('sampleTitle') and all('\u4e00' <= c <= '\u9fff' for c in en_state['sampleTitle']):
            all_issues.append({
                "severity": "P1",
                "scenario": 5,
                "issue": f"EN 模式下概念标题仍是中文: {en_state['sampleTitle']}",
                "evidence": "tConcept() 对英文未实现翻译, 应回退或显示 Pinyin/英文",
            })

        # 切回 zh-CN
        page.locator("#lang-zh-CN").click()
        page.wait_for_timeout(500)

        # ==================== 场景 6: 移动端响应式 ====================
        log("\n=== 场景 6: 移动端响应式 (375x812) ===")
        ctx_mob = browser.new_context(
            viewport={"width": 375, "height": 812},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
        )
        page_m = ctx_mob.new_page()
        page_m.goto(PUBLIC_URL, wait_until="networkidle", timeout=30000)
        page_m.wait_for_function(
            "window.DATA && window.DATA.nodes && window.DATA.nodes.length > 0",
            timeout=30000,
        )
        page_m.wait_for_timeout(2000)
        screenshot(page_m, "06a_mobile_initial")

        # 检查移动端布局
        mobile_layout = page_m.evaluate("""() => {
            const get = (sel) => {
                const el = document.querySelector(sel);
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return {x: r.x, y: r.y, w: r.width, h: r.height, visible: r.width > 0};
            };
            return {
                vw: window.innerWidth,
                vh: window.innerHeight,
                header: get('.header'),
                search: get('.search'),
                stats: get('.stats'),
                langSwitch: get('.lang-switch'),
                legend: get('.legend'),
                toggleMode: get('#toggleMode'),
            };
        }""")
        findings["scenario6_mobile_layout"] = mobile_layout
        log(f"移动端布局: {json.dumps(mobile_layout, ensure_ascii=False, indent=2)}")

        # 移动端打开概念地图 (用 JS click 绕过 z-index 重叠)
        page_m.evaluate("() => document.getElementById('toggleMode').click()")
        page_m.wait_for_timeout(800)
        screenshot(page_m, "06b_mobile_map_mode")

        # 移动端打开概念地图时, 检查树面板是否覆盖了图
        mobile_map_layout = page_m.evaluate("""() => {
            const get = (sel) => {
                const el = document.querySelector(sel);
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return {x: r.x, y: r.y, w: r.width, h: r.height, visible: r.width > 0};
            };
            return {
                mapPanel: get('#map-panel'),
                cyContainer: get('#cy-container'),
                bodyClass: document.body.className,
            };
        }""")
        findings["scenario6_mobile_map_layout"] = mobile_map_layout
        log(f"移动端概念地图: {json.dumps(mobile_map_layout, ensure_ascii=False, indent=2)}")

        # 移动端打开详情卡
        page_m.evaluate("() => document.getElementById('toggleMode').click()")  # 关掉 map
        page_m.wait_for_timeout(500)
        page_m.evaluate("() => { const n = window.cy.getElementById('M_G1_NS_01'); if (n.length) n.emit('tap'); }")
        page_m.wait_for_timeout(800)
        screenshot(page_m, "06c_mobile_card")

        # 测滚动详情卡
        page_m.evaluate("""() => {
            const c = document.getElementById('card');
            if (c) c.scrollTo(0, c.scrollHeight);
        }""")
        page_m.wait_for_timeout(300)
        screenshot(page_m, "06d_mobile_card_scrolled")

        ctx_mob.close()

        # ==================== 场景 7: a11y ====================
        log("\n=== 场景 7: a11y ===")
        # Tab 键导航
        page.evaluate("() => document.body.focus()")
        page.wait_for_timeout(200)
        tab_path = []
        for i in range(15):
            page.keyboard.press("Tab")
            page.wait_for_timeout(50)
            f = page.evaluate("() => { const a = document.activeElement; return {id: a?.id, tag: a?.tagName, role: a?.getAttribute('role'), text: (a?.textContent || a?.value || '').slice(0,30)} }")
            tab_path.append(f)
        findings["scenario7_tab_path"] = tab_path
        log(f"Tab 路径: {tab_path}")

        # 检查 ARIA 完整性
        aria_audit = page.evaluate("""() => {
            const results = {
                cyAriaLabel: document.getElementById('cy-container')?.getAttribute('aria-label'),
                cardAriaLabel: document.getElementById('card')?.getAttribute('aria-label'),
                searchAriaLabel: document.querySelector('.search input')?.getAttribute('aria-label'),
                skipLink: !!document.querySelector('.skip-link'),
                roleApplication: document.getElementById('cy-container')?.getAttribute('role'),
                imgsMissingAlt: Array.from(document.querySelectorAll('img')).filter(i => !i.alt).length,
                buttonsMissingAriaLabel: Array.from(document.querySelectorAll('button')).filter(b => !b.getAttribute('aria-label') && !b.textContent.trim()).length,
            };
            return results;
        }""")
        findings["scenario7_aria"] = aria_audit
        log(f"ARIA 审计: {aria_audit}")
        screenshot(page, "07a_a11y_keyboard_focus")

        # color contrast 检查 (header 文字 vs 背景)
        contrast = page.evaluate("""() => {
            const getContrast = (fg, bg) => {
                const lum = (c) => {
                    const s = c.replace('#','');
                    const r = parseInt(s.slice(0,2),16)/255, g = parseInt(s.slice(2,4),16)/255, b = parseInt(s.slice(4,6),16)/255;
                    const f = (v) => v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4);
                    return 0.2126*f(r) + 0.7152*f(g) + 0.0722*f(b);
                };
                const L1 = Math.max(lum(fg), lum(bg));
                const L2 = Math.min(lum(fg), lum(bg));
                return (L1 + 0.05) / (L2 + 0.05);
            };
            // 主背景 #0a0d18
            // 主要文字 #e6e9f2
            // 副文字 #8a92a8
            // 弱文字 #5a6278
            return {
                mainText: getContrast('#e6e9f2', '#0a0d18').toFixed(2),
                subText: getContrast('#8a92a8', '#0a0d18').toFixed(2),
                dimText: getContrast('#5a6278', '#0a0d18').toFixed(2),
            };
        }""")
        findings["scenario7_contrast"] = contrast
        log(f"对比度: {contrast}")
        # WCAG AA 标准: 正常文字 >= 4.5, 大文字 >= 3
        if float(contrast.get('dimText', 0)) < 4.5:
            all_issues.append({
                "severity": "P1",
                "scenario": 7,
                "issue": f"辅助对比度过低 (#5a6278 on #0a0d18 = {contrast.get('dimText')}:1, WCAG AA 需 4.5:1)",
                "evidence": f"完整对比度: {contrast}",
            })

        # 触发 focus 截图
        page.keyboard.press("Tab")
        page.wait_for_timeout(200)
        screenshot(page, "07b_focus_state")

        # ==================== 场景 8: Marble 视觉对比 (description only) ====================
        log("\n=== 场景 8: Marble 3D 视觉对比 ===")
        # 截一张当前 V3.2 的力导向布局全屏图
        screenshot(page, "08a_current_v32_layout")

        # 测量节点默认大小, 看是否过密
        density = page.evaluate("""() => {
            if (!window.cy) return null;
            const nodes = window.cy.nodes();
            const total = nodes.length;
            // 计算节点之间的平均距离
            const positions = nodes.map(n => n.position());
            let totalDist = 0, count = 0;
            for (let i = 0; i < Math.min(positions.length, 50); i++) {
                for (let j = i+1; j < Math.min(positions.length, 50); j++) {
                    const dx = positions[i].x - positions[j].x;
                    const dy = positions[i].y - positions[j].y;
                    totalDist += Math.sqrt(dx*dx + dy*dy);
                    count++;
                }
            }
            return {
                totalNodes: total,
                avgDist: (totalDist / count).toFixed(1),
                zoom: window.cy.zoom(),
                extent: window.cy.extent(),
            };
        }""")
        findings["scenario8_density"] = density
        log(f"图密度: {density}")

        # 完成
        log("\n=== 测试完成 ===")
        log(f"Console 消息: {len(all_console)}, PageErrors: {len(all_pageerrors)}")

        # 错误汇总
        errors_only = [c for c in all_console if c.get('type') == 'error']
        if errors_only:
            log(f"\n=== Console 错误 ({len(errors_only)}) ===")
            for e in errors_only[:10]:
                log(f"  {e['text'][:200]}")

        if all_pageerrors:
            log(f"\n=== Page Errors ({len(all_pageerrors)}) ===")
            for e in all_pageerrors[:5]:
                log(f"  {e['error'][:200]}")

        browser.close()

    # 写入报告
    report = {
        "findings": findings,
        "issues": all_issues,
        "console_errors": [c for c in all_console if c.get('type') == 'error'],
        "page_errors": all_pageerrors,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    log(f"\n报告写入: {REPORT}")
    log(f"发现 P0/P1/P2 问题: {len(all_issues)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 测试脚本异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
