"""
抓取教育部/人教社 2022 义教课标 16 门学科 + 课程方案的 PDF
数据源: https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/index.html
"""
import asyncio
import aiohttp
import os
from pathlib import Path
from datetime import datetime

# 17 个 PDF 链接 (教育部人教社官方, CC 版权)
SOURCES = [
    ("00_课程方案", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512580666241913.pdf"),
    ("01_道德与法治", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512572835086724.pdf"),
    ("02_语文", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512590091048327.pdf"),
    ("03_历史", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512581594448963.pdf"),
    ("04_数学", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512583134605579.pdf"),
    ("05_英语", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512588239545871.pdf"),
    ("06_日语", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512582155736624.pdf"),
    ("07_俄语", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512579125060752.pdf"),
    ("08_地理", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512575462407993.pdf"),
    ("09_科学", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512580391748349.pdf"),
    ("10_物理", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512585406488643.pdf"),
    ("11_化学", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512579587471333.pdf"),
    ("12_生物", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512582539224892.pdf"),
    ("13_信息科技", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512586269887954.pdf"),
    ("14_体育与健康", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512583679664759.pdf"),
    ("15_艺术", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512587098987233.pdf"),
    ("16_劳动", "https://www.pep.com.cn/xw/zt/rjwy/yjkb2022/202205/P020220512581096283281.pdf"),
]

OUT_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "curriculum_2022"

async def download_one(session, name, url, out_dir):
    out_path = out_dir / f"{name}.pdf"
    if out_path.exists() and out_path.stat().st_size > 1000:
        print(f"⏭️  跳过 {name} (已存在, {out_path.stat().st_size//1024} KB)")
        return out_path
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            resp.raise_for_status()
            content = await resp.read()
            out_path.write_bytes(content)
            print(f"✅ {name} → {out_path.stat().st_size//1024} KB")
            return out_path
    except Exception as e:
        print(f"❌ {name} 失败: {e}")
        return None

async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"下载目标目录: {OUT_DIR}")
    print(f"开始下载 {len(SOURCES)} 个 PDF...\n")

    async with aiohttp.ClientSession(
        headers={"User-Agent": "Mozilla/5.0 (Open-Curriculum-CN data collection)"}
    ) as session:
        tasks = [download_one(session, name, url, OUT_DIR) for name, url in SOURCES]
        results = await asyncio.gather(*tasks)

    success = sum(1 for r in results if r)
    fail = len(results) - success
    print(f"\n完成: 成功 {success}/{len(SOURCES)}, 失败 {fail}")
    print(f"时间: {datetime.now().isoformat()}")

if __name__ == "__main__":
    asyncio.run(main())
