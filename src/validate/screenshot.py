"""用 playwright 截图验证可视化"""
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
        # 等 3D 图渲染
        await page.wait_for_timeout(6000)
        # 截图
        path1 = out / "demo_initial.png"
        await page.screenshot(path=str(path1))
        print(f"✅ {path1}")
        # 模拟点击中央节点（如果有）
        # 等更多渲染
        await page.wait_for_timeout(2000)
        path2 = out / "demo_after_5s.png"
        await page.screenshot(path=str(path2))
        print(f"✅ {path2}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
