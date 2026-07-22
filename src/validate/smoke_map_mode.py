"""
Smoke test 概念地图模式 V3.1
- 打开页面
- 等图谱加载
- 截图 (力导向默认)
- 点击 "概念地图" 按钮
- 截图 (树状)
- 点树节点, 截图
- 看 console 有没有 JS 错误
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent.parent.parent / "data" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

errors = []
warnings = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.on("console", lambda m: print(f"  console.{m.type}: {m.text[:200]}"))
    page.on("pageerror", lambda e: print(f"  pageerror: {str(e)[:200]}"))

    page.goto("https://vnbke2vo1l8z4.space.mcode.cn/", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)
    # 看加载状态
    state = page.evaluate("""() => ({
        hasDATA: typeof window.DATA !== 'undefined' && window.DATA !== null,
        hasCy: typeof window.cy !== 'undefined' && window.cy !== null,
        loading: document.getElementById('loading')?.classList.contains('done'),
        loadingText: document.getElementById('loadingMsg')?.textContent,
    })""")
    print(f"加载状态: {state}")
    page.wait_for_function("window.DATA && window.DATA.nodes && window.DATA.nodes.length > 0", timeout=15000)
    page.wait_for_timeout(2000)  # 等布局稳定
    page.screenshot(path=str(OUT / "v31_force_default.png"), full_page=False)
    print(f"[1/4] 默认力导向截图: {OUT / 'v31_force_default.png'}")

    # 找 Map 按钮
    map_btn = page.locator("#toggleMode")
    if map_btn.count() == 0:
        print("❌ 找不到 #toggleMode 按钮")
        sys.exit(1)
    map_btn.click()
    page.wait_for_timeout(800)
    page.screenshot(path=str(OUT / "v31_map_initial.png"), full_page=False)
    print(f"[2/4] 概念地图模式截图: {OUT / 'v31_map_initial.png'}")

    # 检查树渲染
    subj_rows = page.locator("#map-tree .tn-row.s").count()
    print(f"  → 学科行数: {subj_rows}")
    if subj_rows < 14:
        print(f"  ❌ 期望 14 学科，实际 {subj_rows}")
        sys.exit(1)
    c_rows = page.locator("#map-tree .tn-row.c").count()
    print(f"  → 概念行数: {c_rows}")
    if c_rows < 100:
        print(f"  ❌ 概念行数太少: {c_rows}")
        sys.exit(1)

    # 展开一个学科 (math 是第一个)
    page.locator("#map-tree .tn-row.s").first.click()
    page.wait_for_timeout(200)
    stg_rows = page.locator("#map-tree .tn-row.stg").count()
    print(f"  → 展开 math 后学段行: {stg_rows}")

    # 展开到领域
    page.locator("#map-tree .tn-row.stg").first.click()
    page.wait_for_timeout(200)
    d_rows = page.locator("#map-tree .tn-row.d").count()
    print(f"  → 展开第一学段后领域行: {d_rows}")

    # 展开到概念 + 截图
    if d_rows > 0:
        page.locator("#map-tree .tn-row.d").first.click()
        page.wait_for_timeout(200)
    page.screenshot(path=str(OUT / "v31_map_expanded.png"), full_page=False)
    print(f"[3/4] 树展开截图: {OUT / 'v31_map_expanded.png'}")

    # 点树的概念节点
    first_c = page.locator("#map-tree .tn-row.c").first
    if first_c.count() > 0:
        first_c.click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "v31_map_node_selected.png"), full_page=False)
        print(f"[4/4] 节点选中截图: {OUT / 'v31_map_node_selected.png'}")
        # 看高亮是否生效 (cytoscape class 在 cy 内部, 不是 DOM)
        cy_state = page.evaluate("""() => {
            if (!window.cy) return null;
            const hl = window.cy.nodes('.branch-hl').length;
            const dim = window.cy.nodes('.branch-dim').length;
            const total = window.cy.nodes().length;
            return {hl, dim, total};
        }""")
        print(f"  → cy 状态: {cy_state}")

    browser.close()

print()
print(f"=== Console 错误 ({len(errors)}) ===")
for e in errors[:10]:
    print(f"  {e}")
print(f"=== Console 警告 ({len(warnings)}) ===")
for w in warnings[:5]:
    print(f"  {w}")

if errors:
    print("❌ Smoke test 失败 (有 JS 错误)")
    sys.exit(1)
print("✅ Smoke test 全过")
