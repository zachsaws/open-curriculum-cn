"""V0.8 截图 — 工具增强验证"""
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
        await page.wait_for_timeout(15000)
        # 截图 1: 整体 + 搜索框 + 入口数
        await page.screenshot(path=str(out / "v08_overview.png"))
        print(f"✅ v08_overview.png")
        # 点"高亮入口"
        await page.click("#toggleRoots")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(out / "v08_roots_highlighted.png"))
        print(f"✅ v08_roots_highlighted.png")
        # 搜索"勾股"
        await page.fill("#searchInput", "勾股")
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(out / "v08_search_pythagorean.png"))
        print(f"✅ v08_search_pythagorean.png")
        # 点击第一个结果
        await page.click(".r-item")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(out / "v08_search_jump.png"))
        print(f"✅ v08_search_jump.png")
        # 双击 chip 数学 → fly to
        await page.dblclick('.chip[data-subject="math"]')
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(out / "v08_fly_to_math.png"))
        print(f"✅ v08_fly_to_math.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
