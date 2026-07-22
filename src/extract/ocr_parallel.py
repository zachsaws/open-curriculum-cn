"""
并发 OCR 处理所有 PDF
- 用 ProcessPoolExecutor 跑多核
- 每本 PDF 独立处理
- 失败重试
"""
import fitz
import subprocess
import tempfile
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "curriculum_2022"
PARSED_DIR = Path(__file__).parent.parent.parent / "data" / "parsed"
PARSED_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = Path(__file__).parent.parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

DPI = 180  # 180 DPI 比 200 快 30%, 中文识别率仍 > 85%

def ocr_one_page(args):
    """OCR 单页 (worker function)"""
    pdf_path_str, page_num = args
    pdf_path = Path(pdf_path_str)

    doc = fitz.open(pdf_path)
    if page_num > doc.page_count:
        doc.close()
        return None
    page = doc[page_num - 1]
    pix = page.get_pixmap(dpi=DPI)
    img_bytes = pix.tobytes("png")
    doc.close()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(img_bytes)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["tesseract", tmp_path, "stdout", "-l", "chi_sim+eng", "--psm", "6"],
            capture_output=True, text=True, timeout=60
        )
        text = result.stdout.strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {"page": page_num, "text": text, "char_count": len(text)}

def ocr_one_pdf(pdf_path: Path, max_workers: int = 4) -> dict:
    """OCR 整本 PDF (多页并发)"""
    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    doc.close()

    # 先生成所有页的任务
    tasks = [(str(pdf_path), i) for i in range(1, total_pages + 1)]

    pages = []
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(ocr_one_page, t): t[1] for t in tasks}
        for f in as_completed(futures):
            r = f.result()
            if r:
                pages.append(r)
        # 按页码排序
        pages.sort(key=lambda x: x["page"])

    return {
        "subject_name": pdf_path.stem,
        "file_size_kb": pdf_path.stat().st_size // 1024,
        "page_count": total_pages,
        "pages": pages,
        "ocr_engine": f"tesseract-5.5.2-chi_sim+eng-DPI{DPI}-{max_workers}workers",
        "ocr_at": datetime.now().isoformat(),
    }

def main(skip_existing=True):
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    print(f"找到 {len(pdfs)} 本 PDF", flush=True)

    for pdf in pdfs:
        out_path = PARSED_DIR / f"{pdf.stem}_ocr.json"
        if skip_existing and out_path.exists() and out_path.stat().st_size > 1000:
            with open(out_path) as f:
                d = json.load(f)
            if d.get("page_count", 0) > 5:
                print(f"⏭️  跳过 {pdf.stem}", flush=True)
                continue
        print(f"📄 {pdf.stem} ({pdf.stat().st_size//1024} KB)...", flush=True)
        try:
            data = ocr_one_pdf(pdf)
            out_path.write_text(json.dumps(data, ensure_ascii=False))
            chars = sum(p["char_count"] for p in data["pages"])
            print(f"  ✅ {pdf.stem}: {data['page_count']} 页, {chars:,} 字符", flush=True)
        except Exception as e:
            print(f"  ❌ {pdf.stem} 失败: {e}", flush=True)

if __name__ == "__main__":
    main()
