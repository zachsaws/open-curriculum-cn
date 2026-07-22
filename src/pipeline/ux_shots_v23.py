#!/usr/bin/env python3
"""
V2.3 UX 改造后截图验证 (zh-CN / EN / zh-TW 三种)
"""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path("data/screenshots/v23")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LANGS = [
    ("zh-CN", "01-zh-CN"),
    ("en", "02-en"),
    ("zh-TW", "03-zh-TW"),
]

URL = "http://localhost:8766/index.html"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for lang, name in LANGS:
                ctx = browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    locale=lang,
                )
                page = ctx.new_page()
                page.on("pageerror", lambda e: print(f"[pageerror] {e}", file=sys.stderr))
                page.on("console", lambda m: m.type == "error" and print(f"[console.error] {m.text}", file=sys.stderr))
                page.goto(URL, wait_until="networkidle", timeout=30000)
                # 等待数据加载 (loading 消失 + rCount 有值)
                try:
                    page.wait_for_function(
                        "() => document.getElementById('loading')?.classList.contains('done') && document.getElementById('rCount')?.textContent !== '-'",
                        timeout=15000,
                    )
                except Exception as e:
                    print(f"[wait warn {lang}] {e}", file=sys.stderr)
                time.sleep(2.0)  # 留出 layout 收尾时间

                # 切换语言
                page.evaluate(f"window.setLang('{lang}')")
                time.sleep(0.5)

                out1 = OUT_DIR / f"{name}-default.png"
                page.screenshot(path=str(out1), full_page=False)
                print(f"  -> {out1}")

                # 触发"高亮入口"以触发"从这里学起"按钮
                page.evaluate("document.getElementById('toggleRoots').click()")
                time.sleep(0.6)
                # 等浮动按钮出现
                try:
                    page.wait_for_selector(".start-here-btn", timeout=3000)
                except Exception:
                    pass
                out2 = OUT_DIR / f"{name}-with-roots.png"
                page.screenshot(path=str(out2), full_page=False)
                print(f"  -> {out2}")

                # 关掉高亮 (避免影响 modal 截图)
                page.evaluate("document.getElementById('toggleRoots').click()")
                time.sleep(0.4)

                # 显示键盘 modal (按 ?)
                page.evaluate("document.getElementById('showKbd').click()")
                time.sleep(0.4)
                out3 = OUT_DIR / f"{name}-kbd-modal.png"
                page.screenshot(path=str(out3), full_page=False)
                print(f"  -> {out3}")
                page.evaluate("document.getElementById('kbdModalClose').click()")
                time.sleep(0.3)

                # 测一下 ESC 关闭逻辑 + 打开一个节点验证详情面板
                # 找第一个 cytoscape 节点, 单击
                page.evaluate("""
                    const cy = window.cy;
                    if (cy && cy.nodes().length > 0) {
                      // 选个 grade=1 入口节点 (math)
                      const n = cy.nodes().filter(n => n.data('subject') === 'math' && n.data('grade_start') === 1).first()
                            || cy.nodes().first();
                      n.emit('tap');
                    }
                """)
                time.sleep(0.6)
                out4 = OUT_DIR / f"{name}-card.png"
                page.screenshot(path=str(out4), full_page=False)
                print(f"  -> {out4}")

                ctx.close()

            # 移动端 375x812 iPhone 截图
            print("[Mobile] 375x812 iPhone")
            ctx = browser.new_context(
                viewport={"width": 375, "height": 812},
                device_scale_factor=2,
            )
            page = ctx.new_page()
            page.on("pageerror", lambda e: print(f"[pageerror mobile] {e}", file=sys.stderr))
            page.goto(URL, wait_until="networkidle", timeout=30000)
            try:
                page.wait_for_function(
                    "() => document.getElementById('loading')?.classList.contains('done') && document.getElementById('rCount')?.textContent !== '-'",
                    timeout=15000,
                )
            except Exception as e:
                print(f"[wait warn mobile] {e}", file=sys.stderr)
            time.sleep(1.5)
            out5 = OUT_DIR / "04-mobile-375-default.png"
            page.screenshot(path=str(out5), full_page=False)
            print(f"  -> {out5}")

            # 移动端: 触发高亮入口, 验证浮动按钮在窄屏也能看见
            page.evaluate("document.getElementById('toggleRoots').click()")
            time.sleep(0.6)
            out6 = OUT_DIR / "04-mobile-375-with-roots.png"
            page.screenshot(path=str(out6), full_page=False)
            print(f"  -> {out6}")

            # 移动端: 打开详情面板
            page.evaluate("document.getElementById('toggleRoots').click()")  # 关掉
            time.sleep(0.3)
            page.evaluate("""
                const cy = window.cy;
                if (cy && cy.nodes().length > 0) {
                  const n = cy.nodes().filter(n => n.data('subject') === 'math').first();
                  n.emit('tap');
                }
            """)
            time.sleep(0.5)
            out7 = OUT_DIR / "04-mobile-375-card.png"
            page.screenshot(path=str(out7), full_page=False)
            print(f"  -> {out7}")
            ctx.close()
        finally:
            browser.close()

    print("All screenshots done.")

if __name__ == "__main__":
    main()
