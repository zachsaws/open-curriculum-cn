"""
V3.0 enrich — 把 {subject}_v3.0.json 重新 enrich 一遍
- 读取 all_v3.0.json 作为数据源
- 用 V0.7 enrich 逻辑重新匹配 OCR
- 保留已有关系
- 写回 {subject}_v3.0.json (含 enrich 字段)
- 输出 {subject}_review_r3.json

跑法:
  python src/pipeline/enrich_v3.0.py --subject math
  python src/pipeline/enrich_v3.0.py  # all
"""

import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

# 直接 import enrich_subject 的内部函数
sys.path.insert(0, str(Path(__file__).parent))
from enrich_subject import (
    extract_ocr_items, find_match, extract_bloom, extract_key_points,
    estimate_minutes, OCR_DIR, GRAPH_DIR,
    BLOOM_VERBS, STAGE_NAME, STAGE_GRADE_RANGE,
    SUBJECT_MAP,
)
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
OCR_DIR = ROOT / "data" / "parsed"
GRAPH_DIR = ROOT / "data" / "graph"


def enrich_subject_v30(subject, round_num=3):
    """对 V3.0 单学科 enrich"""
    ocr_file, _, _, priority = SUBJECT_MAP[subject]
    print(f"\n{'='*70}")
    print(f"🔧 {subject} V3.0 enrich — round {round_num}")
    print(f"{'='*70}")

    # 加载 V3.0 概念
    src_path = GRAPH_DIR / f"{subject}_v3.0.json"
    if not src_path.exists():
        print(f"❌ {src_path} 缺失")
        return None
    with open(src_path) as f:
        data = json.load(f)

    # 加载 OCR
    ocr_path = OCR_DIR / ocr_file
    with open(ocr_path) as f:
        ocr = json.load(f)

    items = extract_ocr_items(ocr['pages'])
    cr_items = [it for it in items if it.get('section') == '内容要求']
    ar_items = [it for it in items if it.get('section') == '学业要求']
    print(f"OCR 解析: {len(items)} 条 ({len(cr_items)} 内容要求 + {len(ar_items)} 学业要求)")

    # 按 (stage, domain) 分组
    cr_grouped = defaultdict(list)
    ar_grouped = defaultdict(list)
    for it in cr_items:
        cr_grouped[(it.get('stage', ''), it.get('domain', ''))].append(it)
    for it in ar_items:
        ar_grouped[(it.get('stage', ''), it.get('domain', ''))].append(it)

    matched_cr = 0
    matched_ar = 0
    for n in data['nodes']:
        summary = n.get('summary', '') + ' ' + n.get('title', '')
        gs = n.get('grade_start', 1)
        stage_name = STAGE_NAME.get(gs, None)
        domain = n.get('domain', '')

        # 1. 精确匹配
        cr_match = find_match(summary, cr_items, '内容要求', stage_name, domain)
        ar_match = find_match(summary, ar_items, '学业要求', stage_name, domain)

        # 2. 段匹配 fallback
        if not cr_match:
            group = cr_grouped.get((stage_name, domain), [])
            if group:
                title_kw = re.findall(r'[\u4e00-\u9fa5]{2,6}', n.get('title', ''))
                best_in_group = None
                best_kw_hits = 0
                for it in group:
                    text = it['text']
                    hits = sum(1 for kw in title_kw if kw in text)
                    if hits > best_kw_hits:
                        best_kw_hits = hits
                        best_in_group = it
                cr_match = best_in_group if best_kw_hits > 0 else group[0]

        if not ar_match:
            group = ar_grouped.get((stage_name, domain), [])
            if group:
                title_kw = re.findall(r'[\u4e00-\u9fa5]{2,6}', n.get('title', ''))
                best_in_group = None
                best_kw_hits = 0
                for it in group:
                    text = it['text']
                    hits = sum(1 for kw in title_kw if kw in text)
                    if hits > best_kw_hits:
                        best_kw_hits = hits
                        best_in_group = it
                ar_match = best_in_group if best_kw_hits > 0 else group[0]

        # 3. 段合并 fallback
        if not cr_match:
            same_stage = [it for it in cr_items if it.get('stage') == stage_name]
            if not same_stage:
                same_stage = cr_items
            if same_stage:
                title_kw = re.findall(r'[\u4e00-\u9fa5]{2,6}', n.get('title', ''))
                scored = []
                for it in same_stage:
                    text = it['text']
                    hits = sum(1 for kw in title_kw if kw in text)
                    scored.append((hits, it))
                scored.sort(key=lambda x: -x[0])
                picked = [s[1] for s in scored[:2] if s[0] >= 0]
                if picked:
                    cr_match = picked[0]

        # 填字段
        if cr_match:
            # 只在 content_req 短或不存在时覆盖
            existing_cr = n.get('content_req', '')
            if not existing_cr or len(existing_cr) < 5:
                n['content_req'] = cr_match['text']
            else:
                # 保留原有 (可能更长), 但记录 OCR 原文
                if cr_match['text'] and cr_match['text'] not in n['content_req']:
                    n['content_req'] = n['content_req'] + '。' + cr_match['text'][:200]
            n['src_page'] = cr_match['page']
            n['src_stage'] = cr_match.get('stage', '')
            n['src_domain_ocr'] = cr_match.get('domain', '')
            if cr_match['examples']:
                n['examples'] = cr_match['examples']
            matched_cr += 1
        else:
            if not n.get('content_req'):
                n['content_req'] = n.get('summary', '')
            if not n.get('src_page'):
                n['src_page'] = 1

        if ar_match:
            n['academic_req'] = ar_match['text']
            matched_ar += 1
        else:
            group = ar_grouped.get((stage_name, domain), [])
            if group:
                n['academic_req'] = ' '.join(it['text'] for it in group[:3])[:300]
            else:
                n['academic_req'] = None

        # 重新计算 bloom
        n['bloom'] = extract_bloom(n['content_req'] + ' ' + n.get('summary', ''))
        n['key_points'] = extract_key_points(n['content_req'])
        n['estimated_minutes'] = estimate_minutes(n.get('difficulty', 2))
        n['review_round'] = round_num
        n['review_status'] = 'pending'

    # 自评
    total = len(data['nodes'])
    cr_pct = matched_cr / total * 100 if total else 0
    ar_pct = matched_ar / total * 100 if total else 0
    bloom_cov = sum(1 for n in data['nodes'] if n.get('bloom')) / total * 100 if total else 0
    kp_avg = sum(len(n.get('key_points', [])) for n in data['nodes']) / total if total else 0
    has_full_cr = sum(1 for n in data['nodes'] if n.get('content_req') and len(n['content_req']) >= 5)
    has_full_cr_pct = has_full_cr / total * 100 if total else 0

    # 跨学段错配
    cross_mismatch = 0
    for n in data['nodes']:
        if n.get('src_stage'):
            expected = STAGE_NAME.get(n.get('grade_start', 1), None)
            if expected and n['src_stage'] != expected:
                cross_mismatch += 1

    # 阈值
    high_ocr_subjects = {'math', 'physics', 'chemistry', 'biology', 'chinese', 'science', 'pe_health'}
    low_ocr_subjects = {'english', 'history', 'geography', 'morality_law', 'info_tech', 'art', 'labor'}
    if len(cr_items) == 0:
        threshold = 0
    else:
        threshold = 15 if subject in high_ocr_subjects else (3 if subject in low_ocr_subjects else 5)
    full_threshold = 80 if subject in high_ocr_subjects else (60 if subject in low_ocr_subjects else 75)

    review = {
        'subject': subject,
        'round': round_num,
        'total_concepts': total,
        'content_req_matched': matched_cr,
        'content_req_matched_pct': round(cr_pct, 1),
        'academic_req_matched': matched_ar,
        'academic_req_matched_pct': round(ar_pct, 1),
        'content_req_full': has_full_cr,
        'content_req_full_pct': round(has_full_cr_pct, 1),
        'bloom_coverage_pct': round(bloom_cov, 1),
        'key_points_avg': round(kp_avg, 1),
        'cross_stage_mismatch': cross_mismatch,
        'ocr_threshold': threshold,
        'full_threshold': full_threshold,
        'verdict': 'PASS' if (has_full_cr_pct >= full_threshold and bloom_cov == 100
                              and cr_pct >= threshold) else 'FAIL',
    }
    issues = []
    if has_full_cr_pct < full_threshold:
        issues.append(f"content_req 完整率 {has_full_cr_pct:.1f}% < {full_threshold}%")
    if cr_pct < threshold:
        issues.append(f"OCR 匹配率 {cr_pct:.1f}% < 阈值 {threshold}%")
    if bloom_cov < 100:
        issues.append(f"bloom 覆盖 {bloom_cov:.1f}% < 100%")
    if issues:
        review['issue'] = ' | '.join(issues)

    # 输出
    out_path = GRAPH_DIR / f"{subject}_v3.0.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    review_path = GRAPH_DIR / f"{subject}_review_r{round_num}.json"
    with open(review_path, "w", encoding="utf-8") as f:
        json.dump(review, f, ensure_ascii=False, indent=2)

    print(f"\n📊 {subject} round {round_num} 自评:")
    print(f"  概念数: {total}")
    print(f"  content_req 匹配: {matched_cr}/{total} ({cr_pct:.1f}%)")
    print(f"  content_req 完整(>=5): {has_full_cr}/{total} ({has_full_cr_pct:.1f}%)")
    print(f"  bloom 覆盖: {bloom_cov:.1f}%")
    print(f"  VERDICT: {review['verdict']}")
    if review.get('issue'):
        print(f"  ⚠️ {review['issue']}")

    return review


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subject', help='学科 code, 留空处理全部')
    args = parser.parse_args()

    SUBJECTS = ['math', 'chinese', 'english', 'physics', 'chemistry', 'biology',
                'history', 'geography', 'morality_law', 'science', 'info_tech',
                'art', 'pe_health', 'labor']
    if args.subject:
        SUBJECTS = [args.subject]

    results = []
    for s in SUBJECTS:
        r = enrich_subject_v30(s, round_num=3)
        if r:
            results.append(r)

    print(f"\n{'='*70}")
    print(f"📊 V3.0 enrich 总览")
    print(f"{'='*70}")
    print(f"{'学科':<14} {'概念':<6} {'CR匹配':<8} {'CR完整':<8} {'bloom':<8} {'verdict':<8}")
    pass_count = 0
    for r in results:
        print(f"{r['subject']:<14} {r['total_concepts']:<6} {r['content_req_matched_pct']:<8} {r['content_req_full_pct']:<8} {r['bloom_coverage_pct']:<8} {r['verdict']:<8}")
        if r['verdict'] == 'PASS':
            pass_count += 1
    print(f"{'='*70}")
    print(f"  通过: {pass_count}/14")


if __name__ == "__main__":
    main()
