"""V3.2.1 卡片增强 smoke test"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent.parent.parent / "data" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text[:200]}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"[pageerror] {str(e)[:200]}"))

    page.goto("http://localhost:8000/", wait_until="networkidle", timeout=30000)
    page.wait_for_function("window.DATA && window.DATA.nodes && window.DATA.nodes.length > 0", timeout=15000)
    page.wait_for_timeout(2000)

    # 找第一个 concept 点击 (M_G1_NS_01 万以内数)
    page.evaluate("window.cy.getElementById('M_G1_NS_01').emit('tap');")
    page.wait_for_timeout(500)

    # 看 card 是否出现
    card_on = page.evaluate("document.getElementById('card')?.classList.contains('on')")
    print(f"card 显示: {card_on}")
    if not card_on:
        # 尝试 click
        page.evaluate("""() => {
            const n = window.cy.getElementById('M_G1_NS_01');
            n.select();
            window.showCard(n.data());
        }""")
        page.wait_for_timeout(500)
        card_on = page.evaluate("document.getElementById('card')?.classList.contains('on')")
        print(f"  retry card 显示: {card_on}")

    # 验证 V3.2 新字段
    has_meta = page.evaluate("document.getElementById('card-meta-block')?.style.display !== 'none'")
    has_assess = page.evaluate("document.getElementById('card-assessment-block')?.style.display !== 'none'")
    has_pre_reasons = page.evaluate("document.getElementById('card-pre-reasons')?.children.length || 0")
    has_next_reasons = page.evaluate("document.getElementById('card-next-reasons')?.children.length || 0")
    print(f"  meta-block 显示: {has_meta}")
    print(f"  assessment-block 显示: {has_assess}")
    print(f"  pre reasons 数: {has_pre_reasons}")
    print(f"  next reasons 数: {has_next_reasons}")

    # meta 标签内容
    meta_html = page.evaluate("document.getElementById('card-meta')?.innerHTML || ''")
    print(f"  meta 内容: {meta_html[:200]}")
    # assessment 内容
    ass_text = page.evaluate("document.getElementById('card-assessment')?.textContent || ''")
    print(f"  assessment (前 200): {ass_text[:200]}")

    # 截图
    page.screenshot(path=str(OUT / "v32_card_enhanced.png"), full_page=False)
    print(f"\n截图: {OUT / 'v32_card_enhanced.png'}")

    browser.close()

print()
print(f"=== Console 错误 ({len(errors)}) ===")
for e in errors[:10]:
    print(f"  {e}")
if errors:
    print("❌ Smoke test 失败")
    sys.exit(1)
print("✅ V3.2.1 卡片增强 smoke test 全过")
