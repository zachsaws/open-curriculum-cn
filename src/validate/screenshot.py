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
        # 等 758 节点两步 layout 完成
        await page.wait_for_timeout(15000)
        # 截图 1: 默认 (无 label)
        path1 = out / "demo_initial.png"
        await page.screenshot(path=str(path1))
        print(f"✅ {path1}")
        # 点"显示标签"按钮
        await page.click("#toggleLabels")
        await page.wait_for_timeout(3000)
        path2 = out / "demo_with_labels.png"
        await page.screenshot(path=str(path2))
        print(f"✅ {path2}")
        # 等更多
        await page.wait_for_timeout(2000)
        path3 = out / "demo_after_5s.png"
        await page.screenshot(path=str(path3))
        print(f"✅ {path3}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
