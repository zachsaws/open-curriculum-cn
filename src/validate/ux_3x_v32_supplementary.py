"""
补充测试 - 验证 P0 问题细节
"""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/data/screenshots")
PUBLIC_URL = "https://vnbke2vo1l8z4.space.mcode.cn/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # ============== 1. 移动端 #toggleMode 按钮被遮挡实测 ==============
    print("\n=== 移动端 toggleMode 按钮遮挡测试 ===")
    ctx = browser.new_context(viewport={"width": 375, "height": 812})
    page = ctx.new_page()
    page.goto(PUBLIC_URL, wait_until="networkidle")
    page.wait_for_function("window.DATA && window.DATA.nodes.length > 0", timeout=30000)
    page.wait_for_timeout(2000)
    overlap = page.evaluate("""() => {
        const t = document.getElementById('toggleMode');
        const s = document.getElementById('searchInput');
        const tr = t.getBoundingClientRect();
        const sr = s.getBoundingClientRect();
        // 检查重叠
        const overlapX = Math.max(0, Math.min(tr.right, sr.right) - Math.max(tr.left, sr.left));
        const overlapY = Math.max(0, Math.min(tr.bottom, sr.bottom) - Math.max(tr.top, sr.top));
        return {
            toggle: {x: tr.x, y: tr.y, w: tr.width, h: tr.height},
            search: {x: sr.x, y: sr.y, w: sr.width, h: sr.height},
            overlapX, overlapY,
            // 找最顶层的元素
            topAtCenter: document.elementFromPoint(tr.x + tr.width/2, tr.y + tr.height/2)?.id || document.elementFromPoint(tr.x + tr.width/2, tr.y + tr.height/2)?.tagName,
        };
    }""")
    print(f"  toggle: {overlap['toggle']}")
    print(f"  search: {overlap['search']}")
    print(f"  重叠: x={overlap['overlapX']}, y={overlap['overlapY']}")
    print(f"  点击点最顶层: {overlap['topAtCenter']}")
    if overlap['overlapX'] > 0 and overlap['topAtCenter'] != 'toggleMode':
        print(f"  ❌ P0: 移动端 #toggleMode 被 #searchInput 完全遮挡")
    ctx.close()

    # ============== 2. 概念地图模式 search 与 tree 重叠 ==============
    print("\n=== 概念地图模式 search vs tree 重叠 ===")
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(PUBLIC_URL, wait_until="networkidle")
    page.wait_for_function("window.DATA && window.DATA.nodes.length > 0", timeout=30000)
    page.wait_for_timeout(2000)
    page.evaluate("() => document.getElementById('toggleMode').click()")
    page.wait_for_timeout(800)
    map_overlap = page.evaluate("""() => {
        const s = document.getElementById('searchInput');
        const m = document.getElementById('map-panel');
        const sr = s.getBoundingClientRect();
        const mr = m.getBoundingClientRect();
        const ox = Math.max(0, Math.min(sr.right, mr.right) - Math.max(sr.left, mr.left));
        return {
            search: {x: sr.x, y: sr.y, w: sr.width, h: sr.height},
            mapPanel: {x: mr.x, y: mr.y, w: mr.width, h: mr.height},
            overlapX: ox,
            topAtSearchCenter: document.elementFromPoint(sr.x + sr.width/2, sr.y + sr.height/2)?.id,
        };
    }""")
    print(f"  search: {map_overlap['search']}")
    print(f"  mapPanel: {map_overlap['mapPanel']}")
    print(f"  重叠: x={map_overlap['overlapX']}")
    print(f"  search 中心最顶层: {map_overlap['topAtSearchCenter']}")
    if map_overlap['topAtSearchCenter'] == 'searchInput' and map_overlap['overlapX'] > 50:
        print(f"  ❌ P1: 概念地图模式下 search input 仍占据原位置 (左 20-340), 与 tree panel (左 0-280) 重叠 260px, 用户可看到 search 但点击效果奇怪")

    # ============== 3. 详情卡 软关联混入 ==============
    print("\n=== 详情卡: 软关联 relates_to 混入先决列表 ===")
    page.evaluate("() => { const n = window.cy.getElementById('M_G1_NS_01'); if (n.length) n.emit('tap'); }")
    page.wait_for_timeout(800)
    # 检查先决中是否有非数学 (跨学科) 概念
    prereq_check = page.evaluate("""() => {
        // 万以内数的认识 的 indegree 边中, 有哪些 subject?
        const id = 'M_G1_NS_01';
        const node = window.cy.getElementById(id);
        if (!node.length) return null;
        const inEdges = node.incomers('edge');
        return inEdges.map(e => {
            const src = e.source();
            return {
                title: src.data('title'),
                subject: src.data('subject'),
                rel: e.data('type') || e.data('rel'),
                reason: e.data('reason') || e.data('rationale') || '',
            };
        });
    }""")
    print(f"  万以内数的认识 的所有入边 ({len(prereq_check)}):")
    for e in prereq_check:
        print(f"    - [{e['subject']:12}] {e['title']} ({e['rel']})")
    # 跨学科的有几个?
    cross = [e for e in prereq_check if e['subject'] != 'math']
    print(f"  跨学科先决: {len(cross)} 条 (无区分标识)")

    # ============== 4. zh-TW 字典缺字测试 ==============
    print("\n=== zh-TW 字典缺字测试 ===")
    # 先切到 zh-TW
    page.locator("#lang-zh-TW").click()
    page.wait_for_timeout(500)
    # 测更多概念标题
    tw_test = page.evaluate("""() => {
        if (!window.cy) return null;
        const samples = ['M_G1_NS_01', 'M_G3_GS_01', 'C_G1_RS_01', 'E_G1_LW_01', 'S_G1_MM_01'];
        return samples.map(id => {
            const n = window.cy.getElementById(id);
            if (!n.length) return {id, error: 'not found'};
            return {
                id,
                orig: n.data('title_orig'),
                tw: n.data('title'),
                unchanged: n.data('title_orig') === n.data('title'),
            };
        });
    }""")
    print(f"  zh-TW 翻译结果:")
    for s in tw_test:
        if 'error' in s:
            print(f"    [{s['id']}] {s['error']}")
        else:
            mark = "❌" if s['unchanged'] else "✅"
            print(f"    {mark} {s['id']}: '{s['orig']}' → '{s['tw']}'")
    ctx.close()

    # ============== 5. EN 模式概念标题仍是中文 ==============
    print("\n=== EN 模式: 概念标题未翻译 ===")
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(PUBLIC_URL, wait_until="networkidle")
    page.wait_for_function("window.DATA && window.DATA.nodes.length > 0", timeout=30000)
    page.wait_for_timeout(2000)
    page.locator("#lang-en").click()
    page.wait_for_timeout(500)
    en_check = page.evaluate("""() => {
        const samples = window.cy.nodes().slice(0, 10);
        return samples.map(n => {
            const t = n.data('title');
            const hasChinese = /[\\u4e00-\\u9fff]/.test(t);
            return {id: n.data('id'), title: t, hasChinese};
        });
    }""")
    print(f"  EN 模式下前 10 节点标题:")
    for n in en_check:
        mark = "❌" if n['hasChinese'] else "✅"
        print(f"    {mark} {n['id']}: {n['title']} (含中文: {n['hasChinese']})")
    ctx.close()

    # ============== 6. ARIA label 中的节点数硬编码 ==============
    print("\n=== ARIA label 硬编码检查 ===")
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(PUBLIC_URL, wait_until="networkidle")
    page.wait_for_function("window.DATA && window.DATA.nodes.length > 0", timeout=30000)
    page.wait_for_timeout(1500)
    aria_issue = page.evaluate("""() => {
        const cy = document.getElementById('cy-container');
        return {
            ariaLabel: cy.getAttribute('aria-label'),
            actualNodes: window.DATA.nodes.length,
        };
    }""")
    print(f"  cy aria-label: '{aria_issue['ariaLabel']}'")
    print(f"  实际节点数: {aria_issue['actualNodes']}")
    if '758' in (aria_issue['ariaLabel'] or '') and aria_issue['actualNodes'] != 758:
        print(f"  ❌ P1: aria-label 硬编码 '758 节点' 但实际 {aria_issue['actualNodes']}")
    ctx.close()

    # ============== 7. 启动根节点 (可学起) 数据真实性 ==============
    print("\n=== 可学起入口 (G1-2 阶段无先决) 实际样例 ===")
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(PUBLIC_URL, wait_until="networkidle")
    page.wait_for_function("window.DATA && window.DATA.nodes.length > 0", timeout=30000)
    page.wait_for_timeout(2000)
    # 按 r 键
    page.locator("#cy-container").click()
    page.wait_for_timeout(200)
    page.evaluate("() => document.activeElement?.blur()")
    page.keyboard.press("r")
    page.wait_for_timeout(800)
    sample = page.evaluate("""() => {
        if (!window.cy) return null;
        const roots = window.cy.nodes('.root-node');
        return roots.slice(0, 8).map(n => ({
            id: n.data('id'),
            title: n.data('title'),
            subject: n.data('subject'),
            grade: n.data('grade_start'),
        }));
    }""")
    print(f"  可学起入口前 8 个:")
    for s in sample:
        print(f"    [{s['subject']:12}] G{s['grade']} {s['title']} ({s['id']})")
    ctx.close()

    # ============== 8. header 在 map mode 下的层叠问题 ==============
    print("\n=== 概念地图模式 header 被 tree panel 遮挡 ===")
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(PUBLIC_URL, wait_until="networkidle")
    page.wait_for_function("window.DATA && window.DATA.nodes.length > 0", timeout=30000)
    page.wait_for_timeout(2000)
    page.evaluate("() => document.getElementById('toggleMode').click()")
    page.wait_for_timeout(800)
    header_state = page.evaluate("""() => {
        const h = document.querySelector('.header');
        const m = document.getElementById('map-panel');
        const hr = h.getBoundingClientRect();
        const mr = m.getBoundingClientRect();
        return {
            header: {x: hr.x, y: hr.y, w: hr.width, h: hr.height, zIndex: window.getComputedStyle(h).zIndex},
            mapPanel: {x: mr.x, y: mr.y, w: mr.width, h: mr.height, zIndex: window.getComputedStyle(m).zIndex},
            overlapX: Math.max(0, Math.min(hr.right, mr.right) - Math.max(hr.left, mr.left)),
        };
    }""")
    print(f"  header z-index: {header_state['header']['zIndex']}, position: {header_state['header']}")
    print(f"  mapPanel z-index: {header_state['mapPanel']['zIndex']}, position: {header_state['mapPanel']}")
    print(f"  重叠: x={header_state['overlapX']}")
    if header_state['overlapX'] > 100 and int(header_state['header']['zIndex'] or 0) < int(header_state['mapPanel']['zIndex']):
        print(f"  ❌ P1: 概念地图模式下, header (z={header_state['header']['zIndex']}) 被 map-panel (z={header_state['mapPanel']['zIndex']}) 遮挡, '2022 新课标知识图谱' 标题和副标题在树后不可读")
    # 截图
    page.screenshot(path=str(OUT / "v32-ux-09_header_behind_tree.png"))
    ctx.close()

    browser.close()
    print("\n✅ 补充测试完成")
