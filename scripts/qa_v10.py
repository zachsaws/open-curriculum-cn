#!/usr/bin/env python3
"""V1.0 打包端到端验证: 主页 + 5 核心页 + 404 + 隐私 + favicon"""
from playwright.sync_api import sync_playwright
import json, sys

BASE = "http://127.0.0.1:8766"
PAGES = [
    ("index", "/index.html", "V1.0"),
    ("explore", "/explore.html", "explore"),
    ("funnel", "/funnel.html", "funnel"),
    ("diagnose", "/diagnose.html", "diagnose"),
    ("exercise", "/exercise.html", "exercise"),
    ("wrongbook", "/wrongbook.html", "wrongbook"),
    ("test", "/test.html", "test"),
    ("video-admin", "/video-admin.html", "video-admin"),
    ("404", "/404.html", "404"),
    ("privacy", "/privacy.html", "隐私"),
]

results = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()

    for name, path, expect_text in PAGES:
        try:
            resp = page.goto(BASE + path, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(500)
            status = resp.status if resp else "no-resp"
            title = page.title()
            content = page.content()
            has_expect = expect_text in content
            results.append({"name": name, "path": path, "status": status, "title": title, "has_expect": has_expect})
            print(f"  [{name}] {status} | title={title[:30]} | expect({expect_text})={has_expect}")
        except Exception as e:
            results.append({"name": name, "path": path, "error": str(e)[:100]})
            print(f"  [{name}] ERROR: {str(e)[:100]}")

    # 主页专项: V1.0 banner + FAB + favicon
    page.goto(BASE + "/index.html", wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    checks = {
        "favicon_link": page.locator('link[rel="icon"]').count() > 0,
        "canonical": page.locator('link[rel="canonical"]').count() > 0,
        "og_url": page.locator('meta[property="og:url"]').count() > 0,
        "twitter_card": page.locator('meta[name="twitter:card"]').count() > 0,
        "v10_banner": page.locator('#v10-banner').count() > 0,
        "feedback_fab": page.locator('.feedback-fab').count() > 0,
        "hero_eyebrow_v10": "V1.0 正式版" in page.content(),
    }
    print("\n=== 主页 V1.0 专项 ===")
    for k, v in checks.items():
        print(f"  {k}: {'✓' if v else '✗'}")

    # 截图主页 V1.0 状态
    page.screenshot(path="/tmp/v10_index.png", full_page=False)
    print("\n截图: /tmp/v10_index.png")

    # 验证 explore 沉浸式页无 banner 但有 FAB
    page.goto(BASE + "/explore.html", wait_until="domcontentloaded")
    page.wait_for_timeout(2500)  # 3D 球加载
    checks_immersive = {
        "no_v10_banner": page.locator('.v10-banner').count() == 0,
        "has_feedback_fab": page.locator('.feedback-fab').count() > 0,
        "v10_badge": page.locator('.v10-badge').count() > 0,
        "three_canvas": page.locator('#three-canvas canvas, canvas').count() > 0,
    }
    print("\n=== explore.html 沉浸式检查 ===")
    for k, v in checks_immersive.items():
        print(f"  {k}: {'✓' if v else '✗'}")
    page.screenshot(path="/tmp/v10_explore.png", full_page=False)

    # 验证 diagnose 有 banner + FAB
    page.goto(BASE + "/diagnose.html", wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    checks_diag = {
        "has_v10_banner": page.locator('.v10-banner').count() > 0,
        "has_feedback_fab": page.locator('.feedback-fab').count() > 0,
    }
    print("\n=== diagnose.html 检查 ===")
    for k, v in checks_diag.items():
        print(f"  {k}: {'✓' if v else '✗'}")
    page.screenshot(path="/tmp/v10_diagnose.png", full_page=False)

    browser.close()

# 总结
total = len(results)
ok = sum(1 for r in results if r.get("status") == 200 and r.get("has_expect"))
print(f"\n=== 总结: {ok}/{total} 页通过 ===")
sys.exit(0 if ok == total else 1)
