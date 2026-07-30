#!/usr/bin/env python3
"""
V4.1.2 演示视频录屏 (Playwright record_video)
"""
import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = 'http://localhost:8766'
ROOT = Path('/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn')
OUT_DIR = ROOT / 'web' / 'preview'
OUT_DIR.mkdir(parents=True, exist_ok=True)
MP4 = OUT_DIR / 'v4.1.2-demo.mp4'
GIF = OUT_DIR / 'v4.1.2-demo.gif'

VIDEO_DIR = Path('/tmp/v412_video')
VIDEO_DIR.mkdir(exist_ok=True)
for f in VIDEO_DIR.glob('*'):
    f.unlink()

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--use-gl=swiftshader'])
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            record_video_dir=str(VIDEO_DIR),
            record_video_size={'width': 1280, 'height': 800},
        )
        page = context.new_page()

        try:
            # 1. 主页
            page.goto(f'{BASE}/', wait_until='domcontentloaded')
            time.sleep(2.5)
            # 2. explore
            page.goto(f'{BASE}/explore.html?debug=1', wait_until='domcontentloaded')
            time.sleep(7)  # 3D 球
            # 3. 点勾股定理节点
            page.evaluate('''() => {
                const idx = window.__occ3d.DATA.nodes.findIndex(n => n.id === 'M_G4_GM_08');
                if (idx >= 0) window.__occ3d.selectNode(idx);
            }''')
            time.sleep(2)
            # 4. 点 📺 讲解视频
            page.locator('#card-video-btn').click()
            time.sleep(2)
            # 5. 点 智能诊断
            page.locator("a:has-text('智能诊断')").click()
            page.wait_for_load_state('domcontentloaded')
            time.sleep(2)
            # 6. 答错 5 题
            for i in range(8):
                opts = page.locator('.opt, .option, [data-opt]')
                if opts.count() == 0:
                    break
                opts.last.click()
                time.sleep(0.5)
                nxt = page.locator("button:has-text('下一题'), button:has-text('提交')")
                if nxt.count() > 0:
                    nxt.first.click()
                    time.sleep(0.8)
                on3 = page.evaluate("() => document.getElementById('content') && document.getElementById('content').className.includes('step3')")
                if on3:
                    break
            time.sleep(2)
            # 7. 滚动到 step3 复习路径
            page.evaluate("window.scrollTo(0, 1000)")
            time.sleep(1)
            # 8. 错题本
            page.goto(f'{BASE}/wrongbook.html', wait_until='domcontentloaded')
            time.sleep(2)
            # 9. 返回主页
            page.goto(f'{BASE}/', wait_until='domcontentloaded')
            time.sleep(2)
        finally:
            page.close()
            context.close()
            browser.close()

    # 看录的视频
    webm_files = list(VIDEO_DIR.glob('*.webm'))
    print(f'录了 {len(webm_files)} 个 webm')
    if not webm_files:
        print('没录到, 退')
        return

    # 拼 mp4 (合并多个 webm + 转码)
    # 用 ffmpeg concat
    concat_file = Path('/tmp/v412_concat.txt')
    concat_file.write_text('\n'.join(f"file '{f.absolute()}'" for f in webm_files))
    subprocess.run([
        '/opt/homebrew/bin/ffmpeg', '-y',
        '-f', 'concat', '-safe', '0',
        '-i', str(concat_file),
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-vf', 'scale=1280:800',
        str(MP4),
    ], check=True, capture_output=True)
    print(f'✅ MP4: {MP4}')

    # 拼 GIF (用 palette, 限帧数防过大)
    palette = Path('/tmp/v412_palette.png')
    subprocess.run([
        '/opt/homebrew/bin/ffmpeg', '-y',
        '-i', str(MP4),
        '-vf', 'fps=8,scale=800:-1:flags=lanczos,palettegen',
        str(palette),
    ], check=True, capture_output=True)
    subprocess.run([
        '/opt/homebrew/bin/ffmpeg', '-y',
        '-i', str(MP4),
        '-i', str(palette),
        '-lavfi', 'fps=8,scale=800:-1:flags=lanczos,paletteuse',
        '-t', '30',  # 限 30 秒
        str(GIF),
    ], check=True, capture_output=True)
    print(f'✅ GIF: {GIF}')


if __name__ == '__main__':
    main()
