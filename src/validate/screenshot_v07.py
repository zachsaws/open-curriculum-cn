"""V0.7 截图 — 点击数学节点,展示新 detail 面板"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def main():
    out = Path("/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/data/screenshots")
    out.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
        page = await context.new_page()
        await page.goto("http://127.0.0.1:8000/index.html")
        # 等 758 节点两步 layout 完成
        await page.wait_for_timeout(15000)

        # 截图 1: 整体
        path1 = out / "v07_overview.png"
        await page.screenshot(path=str(path1))
        print(f"✅ {path1}")

        # 关闭数学外的其他学科, 让数学块更清晰
        # 点击图例 chip 关掉非数学的
        chips_to_off = ['chinese', 'english', 'physics', 'chemistry', 'biology', 'history', 'geography', 'science', 'morality_law', 'info_tech', 'pe_health', 'art', 'labor']
        for s in chips_to_off:
            try:
                await page.click(f'.chip[data-subject="{s}"]')
                await page.wait_for_timeout(80)
            except Exception as e:
                pass
        await page.wait_for_timeout(2000)
        path2 = out / "v07_math_only.png"
        await page.screenshot(path=str(path2))
        print(f"✅ {path2}")

        # 点击一个具体的数学节点 — emit tap 事件触发 showCard
        for cid, fname in [('M_G1_NS_06', 'v07_math_detail_1.png'),
                           ('M_G4_GM_08', 'v07_math_detail_2.png'),
                           ('M_G4_QR_05', 'v07_math_detail_3.png')]:
            await page.evaluate(f"""
                () => {{
                    const n = cy.getElementById('{cid}');
                    if (n.length) {{
                        n.emit('tap');
                    }}
                }}
            """)
            await page.wait_for_timeout(800)
            p_out = out / fname
            await page.screenshot(path=str(p_out))
            print(f"✅ {p_out}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
