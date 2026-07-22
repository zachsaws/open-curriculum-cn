"""debug: 打印 console 错误"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1600, "height": 1000})
        page = await context.new_page()
        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGEERROR] {err}"))
        page.on("requestfailed", lambda req: print(f"[REQFAIL] {req.url} - {req.failure}"))
        await page.goto("http://127.0.0.1:8000/index.html")
        await page.wait_for_timeout(8000)
        # 看 canvas 内容
        info = await page.evaluate("""() => {
          const c = document.getElementById('cv');
          if (!c) return {err: 'no canvas'};
          const ctx = c.getContext('webgl2') || c.getContext('webgl');
          return {
            w: c.width, h: c.height,
            hasWebgl: !!ctx,
            loading_done: document.getElementById('loading').classList.contains('done'),
            nCount: document.getElementById('nCount').textContent,
          };
        }""")
        print(f"[INFO] {info}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
