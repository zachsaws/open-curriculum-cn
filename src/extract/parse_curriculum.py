"""
把 PDF 课标解析为结构化文本
- 提取所有文字（按页）
- 提取目录（用字体大小识别）
- 输出 JSON: {subject, page_count, toc: [...], pages: [{page, text, headings: [...]}]}
"""
import fitz  # pymupdf
import json
import re
from pathlib import Path
from datetime import datetime

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "curriculum_2022"
PARSED_DIR = Path(__file__).parent.parent.parent / "data" / "parsed"
PARSED_DIR.mkdir(parents=True, exist_ok=True)

def parse_pdf(pdf_path: Path) -> dict:
    """解析单本 PDF, 返回结构化数据"""
    doc = fitz.open(pdf_path)
    pages = []
    toc = []

    for page_num, page in enumerate(doc):
        # 提取文字
        text = page.get_text("text")
        text = text.strip()

        # 提取该页的标题 (用大字号判断)
        blocks = page.get_text("dict")["blocks"]
        headings = []
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    size = span["size"]
                    text_span = span["text"].strip()
                    if text_span and size > 13:  # 标题阈值
                        headings.append({
                            "text": text_span,
                            "size": round(size, 1),
                            "page": page_num + 1,
                        })

        pages.append({
            "page": page_num + 1,
            "text": text,
            "headings": headings,
        })

    # 提取 PDF 自带目录
    pdf_toc = doc.get_toc()
    for entry in pdf_toc:
        level, title, page = entry
        toc.append({
            "level": level,
            "title": title.strip(),
            "page": page,
        })

    # 提取文档元数据
    subject_code = pdf_path.stem.split("_", 1)[1] if "_" in pdf_path.stem else pdf_path.stem

    return {
        "subject_name": pdf_path.stem,
        "subject_code": subject_code,
        "file_size_kb": pdf_path.stat().st_size // 1024,
        "page_count": doc.page_count,
        "toc": toc,
        "pages": pages,
        "parsed_at": datetime.now().isoformat(),
    }

def main():
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    print(f"找到 {len(pdfs)} 个 PDF\n")

    for pdf in pdfs:
        out_path = PARSED_DIR / f"{pdf.stem}.json"
        if out_path.exists() and out_path.stat().st_size > 1000:
            print(f"⏭️  跳过 {pdf.stem} (已解析)")
            continue
        try:
            data = parse_pdf(pdf)
            out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
            headings_count = sum(len(p["headings"]) for p in data["pages"])
            print(f"✅ {pdf.stem} → {len(data['pages'])} 页, {headings_count} 个标题, TOC {len(data['toc'])} 条")
        except Exception as e:
            print(f"❌ {pdf.stem} 失败: {e}")

if __name__ == "__main__":
    main()
