"""
OCR 处理扫描版 PDF 课标
- 用 pymupdf 把每一页渲染为高清图片
- 用 tesseract (chi_sim) 提取文字
- 输出 JSON 包含 page, text, headings
"""
import fitz
import subprocess
import tempfile
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "curriculum_2022"
PARSED_DIR = Path(__file__).parent.parent.parent / "data" / "parsed"
PARSED_DIR.mkdir(parents=True, exist_ok=True)

DPI = 200  # 200 DPI 在 tesseract 准确率和速度之间平衡

def ocr_page(pdf_path: Path, page_num: int) -> dict:
    """OCR 单页 PDF"""
    doc = fitz.open(pdf_path)
    if page_num > doc.page_count:
        return None
    page = doc[page_num - 1]
    pix = page.get_pixmap(dpi=DPI)
    img_bytes = pix.tobytes("png")
    doc.close()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(img_bytes)
        tmp_path = f.name

    try:
        # tesseract chi_sim+eng
        result = subprocess.run(
            ["tesseract", tmp_path, "stdout", "-l", "chi_sim+eng", "--psm", "6"],
            capture_output=True, text=True, timeout=60
        )
        text = result.stdout.strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {
        "page": page_num,
        "text": text,
        "char_count": len(text),
    }

def ocr_pdf(pdf_path: Path, max_pages: int = None) -> dict:
    """OCR 整本 PDF"""
    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    doc.close()

    if max_pages:
        total_pages = min(total_pages, max_pages)

    pages = []
    for i in range(1, total_pages + 1):
        p = ocr_page(pdf_path, i)
        if p:
            pages.append(p)
        if i % 20 == 0:
            print(f"  OCR {pdf_path.stem}: {i}/{total_pages}", flush=True)

    return {
        "subject_name": pdf_path.stem,
        "file_size_kb": pdf_path.stat().st_size // 1024,
        "page_count": total_pages,
        "pages": pages,
        "ocr_engine": "tesseract-5.5.2-chi_sim+eng-DPI200",
        "ocr_at": datetime.now().isoformat(),
    }

def main(targets: list = None, max_pages: int = None):
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if targets:
        pdfs = [p for p in pdfs if any(t in p.stem for t in targets)]

    print(f"OCR 目标: {len(pdfs)} 本 PDF")
    if max_pages:
        print(f"限制每本: 前 {max_pages} 页 (测试用)")
    print()

    for pdf in pdfs:
        out_path = PARSED_DIR / f"{pdf.stem}_ocr.json"
        if out_path.exists() and out_path.stat().st_size > 1000:
            with open(out_path) as f:
                data = json.load(f)
            if data.get("page_count", 0) > 0:
                print(f"⏭️  跳过 {pdf.stem} (已 OCR, {data['page_count']} 页)")
                continue
        print(f"📄 OCR {pdf.stem}...", flush=True)
        data = ocr_pdf(pdf, max_pages=max_pages)
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
        total_chars = sum(p["char_count"] for p in data["pages"])
        print(f"  ✅ {pdf.stem}: {data['page_count']} 页, {total_chars:,} 字符")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # python ocr_curriculum.py 数学 30
        targets = [sys.argv[1]]
        max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else None
        main(targets, max_pages)
    else:
        main()
