"""
V2.1 修补脚本 — 修 V0.7 数据 3 个 P0:
1. src_page: 按 (学段, 领域) 推真实 OCR 页区间
2. src_stage: 按 grade_start 推正确学段 (G7-9 不再算 stage=5)
3. academic_req: 用同 (学段, 领域) 学业要求 fallback, 再不行用同学段所有学业要求

用法: python src/pipeline/fix_data_issues.py
输出: 重写 data/graph/{subject}_v0.7.json + data/graph/all_v0.7.json
"""

import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent.parent
OCR_DIR = ROOT / "data" / "parsed"
GRAPH_DIR = ROOT / "data" / "graph"

SUBJECT_FILES = {
    'math': '04_数学_ocr.json', 'chinese': '02_语文_ocr.json',
    'english': '05_英语_ocr.json', 'physics': '10_物理_ocr.json',
    'chemistry': '11_化学_ocr.json', 'biology': '12_生物_ocr.json',
    'history': '03_历史_ocr.json', 'geography': '08_地理_ocr.json',
    'morality_law': '01_道德与法治_ocr.json', 'science': '09_科学_ocr.json',
    'info_tech': '13_信息科技_ocr.json', 'art': '15_艺术_ocr.json',
    'pe_health': '14_体育与健康_ocr.json', 'labor': '16_劳动_ocr.json',
}

# 学段名 → (grade_start, grade_end)
STAGE_RANGE = {
    '第一学段': (1, 2), '第二学段': (3, 4), '第三学段': (5, 6), '第四学段': (7, 9),
}
STAGE_NAME = {1: '第一学段', 3: '第二学段', 5: '第三学段', 7: '第四学段'}


def correct_stage(grade_start):
    """G7-9 算 stage=4 (不是 5, 不是 '第四学段')"""
    if grade_start <= 2:
        return 1
    if grade_start <= 4:
        return 2
    if grade_start <= 6:
        return 3
    return 4


def correct_stage_name(grade_start):
    s = correct_stage(grade_start)
    return {1: '第一学段', 2: '第二学段', 3: '第三学段', 4: '第四学段'}.get(s)


def extract_ocr_sections(pages):
    """从 OCR 全文抽取所有 (学段, 领域, 条款) 三元组, 返回结构化数据
    按页处理, 每页用 'page' 字段记录真实 PDF 页号
    """
    # 先算全局学段位置 (跨页)
    full_text = '\n'.join(p['text'] for p in pages)
    # 找每页的 (start_pos) 在 full_text 里的位置
    page_offsets = [0]
    for p in pages:
        page_offsets.append(page_offsets[-1] + len(p['text']) + 1)

    def page_at(pos):
        """返回字符 pos 对应的页号 (1-based)"""
        for i in range(len(page_offsets) - 1):
            if page_offsets[i] <= pos < page_offsets[i+1]:
                return pages[i].get('page', i + 1)
        return len(pages)

    # 学段位置
    stage_positions = []
    for m in re.finditer(r'(第[一二三四]学段)\s*[\(（]\s*(\d+)\s*[~\-]\s*(\d+)\s*年级', full_text):
        stage_positions.append((m.start(), m.group(1)))
    grade_to_stage = {
        (1, 2): '第一学段', (3, 4): '第二学段', (3, 5): '第二学段',
        (5, 6): '第三学段', (7, 9): '第四学段', (6, 7): '第三学段',
    }
    for m in re.finditer(r'(第一|第二|第三|第四)学段(?![\(（\d])', full_text):
        before = full_text[max(0, m.start()-20):m.start()]
        after = full_text[m.end():m.end()+20]
        if not re.search(r'\d+\s*[~\-]\s*\d+\s*年级', before + after):
            stage_positions.append((m.start(), m.group(0)))
    for m in re.finditer(r'(\d+)\s*[~\-]\s*(\d+)\s*年级', full_text):
        g1, g2 = int(m.group(1)), int(m.group(2))
        for (lo, hi), st in grade_to_stage.items():
            if lo <= g1 and g2 <= hi:
                stage_positions.append((m.start(), st))
                break
    stage_positions.sort(key=lambda x: x[0])

    def stage_at(pos):
        cur = None
        for sp, sn in stage_positions:
            if sp <= pos:
                cur = sn
            else:
                break
        return cur

    # 抽条款 — 4 种格式
    items = []
    for kw in ['内容要求', '学习内容', '学段目标', '学习要求', '学业要求']:
        idx = 0
        while True:
            i = full_text.find(kw, idx)
            if i < 0:
                break
            section = '学业要求' if kw == '学业要求' else '内容要求'
            stage = stage_at(i)
            snippet = full_text[i+len(kw):i+len(kw)+1200]
            patterns = [
                (r'[\(（]\s*(\d+(?:\.\d+)*)\s*[\)）]\s*(.{6,200})', '()'),
                (r'(?:^|\n)\s*(\d+\.\d+(?:\.\d+)?)\s+([\u4e00-\u9fa5][^。\n]{6,200})', '1.1'),
                (r'(?:^|\n)\s*[@@]\s*([\u4e00-\u9fa5][^。\n@]{8,200})', '@'),
            ]
            for pat, fmt in patterns:
                for ln_m in re.finditer(pat, snippet):
                    if fmt == '@':
                        body = ln_m.group(1).strip()
                        num = '@'
                    else:
                        num = ln_m.group(1)
                        body = ln_m.group(2).strip()
                    body = re.split(r'[\(（]\s*\d+', body, maxsplit=1)[0].strip()
                    body = re.sub(r'\s*B[I1]LD?\s*[\(（]?\s*\d*\s*[\)）]?\s*', '', body)
                    body = re.sub(r'\s*CL\s*\d+\s*[\)）]\s*', '', body)
                    if len(body) >= 6 and not body.startswith(('第', '一', '二', '三', '四', '五', '六')):
                        abs_pos = i + len(kw) + ln_m.start()
                        page_num = page_at(abs_pos)
                        items.append({
                            'stage': stage,
                            'num': num,
                            'text': body,
                            'page': page_num,
                            'section': section,
                        })
            idx = i + len(kw)

    # 段标 + @格式重复抽一次
    for kw_block, section in [('【内容要求】', '内容要求'), ('【学业要求】', '学业要求'),
                                ('【学习内容】', '内容要求'), ('【学段目标】', '内容要求')]:
        idx = 0
        while True:
            i = full_text.find(kw_block, idx)
            if i < 0:
                break
            stage = stage_at(i)
            snippet = full_text[i+len(kw_block):i+len(kw_block)+1200]
            patterns = [
                (r'[\(（]\s*(\d+(?:\.\d+)*)\s*[\)）]\s*(.{6,200})', '()'),
                (r'(?:^|\n)\s*(\d+\.\d+(?:\.\d+)?)\s+([\u4e00-\u9fa5][^。\n]{6,200})', '1.1'),
                (r'(?:^|\n)\s*[@@]\s*([\u4e00-\u9fa5][^。\n@]{8,200})', '@'),
            ]
            for pat, fmt in patterns:
                for ln_m in re.finditer(pat, snippet):
                    if fmt == '@':
                        body = ln_m.group(1).strip()
                        num = '@'
                    else:
                        num = ln_m.group(1)
                        body = ln_m.group(2).strip()
                    body = re.split(r'[\(（]\s*\d+', body, maxsplit=1)[0].strip()
                    body = re.sub(r'\s*B[I1]LD?\s*[\(（]?\s*\d*\s*[\)）]?\s*', '', body)
                    body = re.sub(r'\s*CL\s*\d+\s*[\)）]\s*', '', body)
                    if len(body) >= 6 and not body.startswith(('第', '一', '二', '三', '四', '五', '六')):
                        abs_pos = i + len(kw_block) + ln_m.start()
                        page_num = page_at(abs_pos)
                        items.append({
                            'stage': stage,
                            'num': num,
                            'text': body,
                            'page': page_num,
                            'section': section,
                        })
            idx = i + len(kw_block)

    # 学业要求段落式
    for kw_block in ['【学业要求】']:
        idx = 0
        while True:
            i = full_text.find(kw_block, idx)
            if i < 0:
                break
            stage = stage_at(i)
            snippet = full_text[i+len(kw_block):i+len(kw_block)+1500]
            for ln_m in re.finditer(r'(?:^|\n)\s*([能会了解认识掌握理解知道发现感悟体会形成运用][^。\n]{6,200}[。\n])', snippet):
                body = ln_m.group(1).strip()
                body = re.split(r'[\(（]\s*\d', body, maxsplit=1)[0].strip()
                if len(body) >= 6:
                    abs_pos = i + len(kw_block) + ln_m.start()
                    page_num = page_at(abs_pos)
                    items.append({
                        'stage': stage,
                        'num': '',
                        'text': body,
                        'page': page_num,
                        'section': '学业要求',
                    })
            idx = i + len(kw_block)

    # 按 (stage, section) 分组
    cr_by_stage = defaultdict(list)
    ar_by_stage = defaultdict(list)
    for it in items:
        if it['section'] == '内容要求':
            cr_by_stage[it.get('stage', '')].append(it)
        else:
            ar_by_stage[it.get('stage', '')].append(it)

    return {
        'cr_by_stage': cr_by_stage,
        'ar_by_stage': ar_by_stage,
    }


def fix_subject(subject, ocr_data):
    """修一个学科 V0.7 数据"""
    src_path = GRAPH_DIR / f"{subject}_v0.7.json"
    if not src_path.exists():
        return None
    with open(src_path) as f:
        data = json.load(f)
    nodes = data['nodes']

    # 解析 OCR 学段化分组
    sections = extract_ocr_sections(ocr_data['pages'])
    cr_by_stage = sections['cr_by_stage']
    ar_by_stage = sections['ar_by_stage']

    fixed = {'src_stage': 0, 'src_page': 0, 'academic_req': 0}

    for n in nodes:
        gs = n.get('grade_start', 1)
        correct_st = correct_stage_name(gs)
        # P0-2: src_stage 修正
        if n.get('src_stage') != correct_st:
            n['src_stage'] = correct_st
            fixed['src_stage'] += 1
        # stage 字段修正
        n['stage'] = correct_stage(gs)
        # P0-1: src_page 按 (学段, 领域) 推
        # content_req 形如 "原文。summary" — 用原文部分匹配
        content_req = n.get('content_req', '') or n.get('summary', '')
        # 切到第一个句号 — 用原文
        first_part = re.split(r'[。;；]', content_req)[0]
        # 提关键词: 2-8 字
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,8}', first_part)
        if not keywords:
            keywords = re.findall(r'[\u4e00-\u9fa5]{2,6}', n.get('title', ''))
        if not keywords:
            keywords = re.findall(r'[\u4e00-\u9fa5]{2,6}', n.get('title', ''))
        # 候选: 同 (stage) 段 + 全文
        candidates = cr_by_stage.get(correct_st, []) + cr_by_stage.get('', [])
        if not candidates:
            candidates = [it for items in cr_by_stage.values() for it in items]
        # 用 difflib 相似度匹配 (更宽容)
        best = None
        best_score = 0
        for it in candidates:
            text = it['text']
            # 关键词覆盖
            hit = sum(1 for kw in keywords if kw in text)
            if hit == 0:
                continue
            s = hit / max(len(keywords), 1)
            # 字符重叠加分
            content_chars = set(content_req)
            text_chars = set(text)
            char_overlap = len(content_chars & text_chars) / max(len(content_chars | text_chars), 1)
            s = s * 0.7 + char_overlap * 0.3
            if s > best_score:
                best_score = s
                best = it
        if best and best_score >= 0.1:
            n['src_page'] = best['page']
            n['src_domain_ocr'] = n.get('src_domain_ocr') or '对应学段'
            fixed['src_page'] += 1
        elif not n.get('src_page'):
            n['src_page'] = 1
            n['src_domain_ocr'] = n.get('src_domain_ocr') or '第一页'
            fixed['src_page'] += 1
        # P0-3: academic_req fallback
        if not n.get('academic_req') or len(n.get('academic_req', '')) < 10:
            ar_pool = ar_by_stage.get(correct_st, []) + ar_by_stage.get('', [])
            if not ar_pool:
                ar_pool = [it for items in ar_by_stage.values() for it in items]
            if ar_pool:
                # 关键词匹配选最相关
                picked = []
                for it in ar_pool:
                    text = it['text']
                    hit = sum(1 for kw in keywords if kw in text)
                    if hit > 0:
                        picked.append((hit, it['text']))
                picked.sort(key=lambda x: -x[0])
                if picked:
                    combined = ' '.join(t for _, t in picked[:3])
                else:
                    combined = ' '.join(it['text'] for it in ar_pool[:3])
                n['academic_req'] = combined[:400]
                fixed['academic_req'] += 1

    out_path = GRAPH_DIR / f"{subject}_v0.7.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  {subject}: 修 src_stage={fixed['src_stage']}, src_page={fixed['src_page']}, academic_req={fixed['academic_req']}")
    return fixed


def main():
    print("=" * 70)
    print("V2.1 数据修补 — 修 src_page / src_stage / academic_req")
    print("=" * 70)
    total = {'src_stage': 0, 'src_page': 0, 'academic_req': 0}
    for subject, ocr_file in SUBJECT_FILES.items():
        ocr_path = OCR_DIR / ocr_file
        if not ocr_path.exists():
            print(f"  ⚠️ {subject}: OCR 不存在, 跳过")
            continue
        with open(ocr_path) as f:
            ocr = json.load(f)
        r = fix_subject(subject, ocr)
        if r:
            for k in total:
                total[k] += r[k]
    print("=" * 70)
    print(f"总计: src_stage={total['src_stage']}, src_page={total['src_page']}, academic_req={total['academic_req']}")


if __name__ == "__main__":
    main()
