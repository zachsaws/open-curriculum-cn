"""debug 2: 检查 3D 状态"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1600, "height": 1000})
        page = await context.new_page()
        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGEERROR] {err}"))
        await page.goto("http://127.0.0.1:8000/index.html")
        # 等更久
        await page.wait_for_timeout(12000)
        # 看节点位置 + 摄像机
        info = await page.evaluate("""() => {
          // 找 graph 引用
          const fns = Object.getOwnPropertyNames(window).filter(k => k.includes('graph') || k.includes('Graph'));
          // 直接拿 canvas 像素
          const c = document.getElementById('cv');
          const ctx = c.getContext('webgl2') || c.getContext('webgl');
          return {
            canvas: {w: c.width, h: c.height},
            globalFns: fns,
            hasWebgl: !!ctx,
            loading: document.getElementById('loading').classList.contains('done'),
            nCount: document.getElementById('nCount').textContent,
          };
        }""")
        print(f"[INFO] {info}")
        # 再等几秒看 d3 force 是否收敛
        await page.wait_for_timeout(5000)
        info2 = await page.evaluate("""() => {
          return {
            loading: document.getElementById('loading').classList.contains('done'),
            nCount: document.getElementById('nCount').textContent,
          };
        }""")
        print(f"[INFO2] {info2}")
        await page.screenshot(path="/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn/data/screenshots/debug2.png")
        print("screenshot saved")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
