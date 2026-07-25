"""9:16 竖屏录屏 9 个镜头 (shot1, 2, 3, 4, 5, 6, 7, 8, 9)"""
import time
import shutil
import glob
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent
SHOTS = [
    ('shot1.html', 'shot1.webm', 3.2),
    ('shot2.html', 'shot2.webm', 3.2),
    ('shot3.html', 'shot3.webm', 3.2),
    ('shot4_concept.html', 'shot4_concept.webm', 3.2),
    ('shot5_concept.html', 'shot5_concept.webm', 3.2),
    ('shot6_concept.html', 'shot6_concept.webm', 3.2),
    ('shot7.html', 'shot7.webm', 3.5),  # 4 句对仗 4 个 0.7s = 2.8s + buffer
    ('shot8.html', 'shot8.webm', 3.2),
    ('shot9.html', 'shot9.webm', 3.2),  # CTA 段
]

with sync_playwright() as p:
    b = p.chromium.launch()
    for html, out, dur in SHOTS:
        ctx = b.new_context(
            viewport={'width': 720, 'height': 1280},
            record_video_dir=str(OUT / 'tmp'),
            record_video_size={'width': 720, 'height': 1280},
        )
        page = ctx.new_page()
        page.goto(f'file://{OUT / html}', wait_until='load', timeout=10000)
        time.sleep(dur)
        ctx.close()
        videos = sorted(glob.glob(str(OUT / 'tmp' / '*.webm')))
        if videos:
            Path(videos[-1]).rename(OUT / out)
            print(f"saved: {out}")
    b.close()

shutil.rmtree(OUT / 'tmp', ignore_errors=True)
print("done.")
