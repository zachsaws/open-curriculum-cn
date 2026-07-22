"""
数学 V0.7 — 给 V0.6 214 概念补 detail 字段
- content_req: 该概念在课标"内容要求"里的原文
- academic_req: 学业要求原文
- examples: 课标"例 N" 引用
- key_points: 知识要点 (3-5 短句)
- bloom: 布鲁姆分类动词 (了解/认识/会/能/掌握/理解/经历/探索/知道/发现/感悟/体会/形成)
- estimated_minutes: 估计学习时间

策略: 用 V0.6 标题 + summary 里的关键短语在数学 OCR 里做模糊匹配, 找最近邻原文
"""

import json
import re
from pathlib import Path
from difflib import SequenceMatcher

ROOT = Path(__file__).parent.parent.parent
OCR_FILE = ROOT / "data" / "parsed" / "04_数学_ocr.json"
SRC = ROOT / "data" / "graph" / "math_v0.6.json"
OUT = ROOT / "data" / "graph" / "math_v0.7.json"

BLOOM_VERBS = ["了解", "认识", "会", "能", "掌握", "理解", "经历", "探索", "知道",
               "发现", "感悟", "体会", "形成", "运用", "分析", "比较", "计算",
               "推导", "说明", "设计", "制作", "实验", "调查", "识别", "分类",
               "描述", "表达", "欣赏", "朗读", "背诵", "复述", "讲述", "默写",
               "拼读", "认读", "识记", "感受", "经历", "应用", "迁移", "拓展"]


def extract_items_with_anchor(ocr_pages):
    """解析数学 OCR, 提取所有 (数字) 内容要求条款
    返回 list of {stage, domain, num, text, page, line_idx, examples, academic_req}
    """
    items = []
    current_stage = None
    current_domain = None
    # 跨页继承
    in_requirement = False
    in_academic = False

    for p_idx, p in enumerate(ocr_pages):
        text = p['text']
        lines = text.split('\n')
        # 先扫本页所有 "学段 ( X~Y 年级)"
        page_last_stage = None
        for ln in lines:
            m = re.search(r'(第[一二三四]学段)\s*[\(（]\s*(\d+)\s*[~\-]\s*(\d+)\s*年级', ln)
            if m:
                page_last_stage = m.group(1)
        if page_last_stage:
            current_stage = page_last_stage

        # 跨页继承: 看看本页有没有"【教学提示】" (会重置 in_academic) 或新段标
        for li, ln in enumerate(lines):
            stripped = ln.strip()
            # 段标
            if '【' in stripped:
                if '内容要求' in stripped:
                    in_requirement = True
                    in_academic = False
                    continue
                if '学业要求' in stripped:
                    in_requirement = False
                    in_academic = True
                    continue
                if '教学提示' in stripped or '评价' in stripped or '试题' in stripped:
                    in_requirement = False
                    in_academic = False
                    continue
            # 领域标: "1. 数与运算" / "2. 数量关系" / "(一) 数与代数" 之类
            m = re.match(r'^[\(（]?([一二三四五六七八九十\d]+)[\)）\.、]\s*([\u4e00-\u9fa5]{2,12})', stripped)
            if m:
                num_str = m.group(1).rstrip('.')
                # 把中文数字转 int
                cn_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
                if num_str in cn_map:
                    num_int = cn_map[num_str]
                else:
                    try:
                        num_int = int(num_str)
                    except ValueError:
                        num_int = 0
                if 1 <= num_int <= 6 and len(stripped) < 30:
                    current_domain = m.group(2).strip()
            # 提取 (数字) 条款
            m = re.match(r'^\s*[\(（]\s*(\d+)\s*[\)）]\s*(.{10,300})', ln)
            if m:
                num = m.group(1)
                body = m.group(2).strip()
                # 去掉 OCR 噪声 (BILD / CL N) 之类
                body = re.sub(r'\s*B[I1]LD?\s*[\(（]?\s*\d*\s*[\)）]?\s*', '', body)
                body = re.sub(r'\s*CL\s*\d+\s*[\)）]\s*', '', body)
                body = re.sub(r'\s*[\(（]\s*[Ii1l]\s*[\)）]\s*', '', body)
                # 检测"例 N"
                examples = []
                ex_m = re.search(r'[\(（]\s*例\s*(\d+)\s*[\)）]', body)
                if ex_m:
                    examples.append(f"例{ex_m.group(1)}")
                # 同句多个 例
                for em in re.finditer(r'[\(（]\s*例\s*(\d+)\s*[\)）]', body):
                    examples.append(f"例{em.group(1)}")
                items.append({
                    'stage': current_stage,
                    'domain': current_domain,
                    'num': num,
                    'text': body,
                    'page': p_idx + 1,
                    'line_idx': li,
                    'section': '内容要求' if in_requirement else ('学业要求' if in_academic else None),
                    'examples': examples,
                })
            # 学业要求段下没有 (数字) 编号, 用段落式
            if in_academic and not m and stripped and len(stripped) > 8 and not stripped.startswith('【') and not re.match(r'^\d+\s*[\.、]', stripped) and not re.match(r'^[一二三四五六七八九十]\s*[\.、]', stripped):
                # 排除领域标
                if re.match(r'^[能会了解认识掌握理解知道发现感悟体会形成运用]', stripped):
                    items.append({
                        'stage': current_stage,
                        'domain': current_domain,
                        'num': '',
                        'text': stripped,
                        'page': p_idx + 1,
                        'line_idx': li,
                        'section': '学业要求',
                        'examples': [],
                    })
            # 提取 "例 N: xxxx" 形式 (但 (例 N) 已经捕获)
    return items


def find_matching_item(target_summary, items, prefer_section='内容要求', prefer_stage=None, prefer_domain=None):
    """找最匹配 target_summary 的 OCR 条款
    优先: 同 stage + 同 domain
    其次: 同 stage
    最后: 全文
    """
    keywords = re.findall(r'[\u4e00-\u9fa5]{2,8}', target_summary)
    if not keywords:
        return None

    candidates = [it for it in items if it.get('section') == prefer_section]
    if not candidates:
        return None

    def score(it):
        text = it['text']
        hit = sum(1 for kw in keywords if kw in text)
        if hit == 0:
            return 0
        s = hit / max(len(keywords), 1)
        # 强优先同 stage (学段不一致直接大幅扣分)
        if prefer_stage and it.get('stage') != prefer_stage:
            s -= 0.5
        # 同 domain 加分
        if prefer_domain and it.get('domain') and prefer_domain in (it.get('domain') or ''):
            s += 0.2
        return s

    best = max(candidates, key=score, default=None)
    if best and score(best) >= 0.15:
        return best
    return None


def extract_bloom(text):
    """从文本里提取布鲁姆动词 (按出现顺序)"""
    found = []
    for v in BLOOM_VERBS:
        if v in text:
            found.append(v)
    return found[:3] if found else ["了解"]


def extract_key_points(text, max_n=5):
    """从文本里抽 3-5 个关键短句
    按 ,。; 切, 保留 5-30 字的短句
    """
    sents = re.split(r'[，。;；,]+', text)
    sents = [s.strip() for s in sents if 4 <= len(s.strip()) <= 30]
    # 优先含动词的
    scored = []
    for s in sents:
        v_score = sum(1 for v in BLOOM_VERBS if v in s)
        scored.append((v_score, s))
    scored.sort(key=lambda x: -x[0])
    out = []
    for _, s in scored:
        if s not in out and len(out) < max_n:
            out.append(s)
    return out[:max_n] if out else [text[:30] + "..."]


def estimate_minutes(difficulty):
    """按难度估算学习时间 (分钟)"""
    return {1: 15, 2: 25, 3: 40, 4: 60, 5: 90}.get(difficulty, 30)


def enrich():
    with open(SRC) as f:
        data = json.load(f)
    with open(OCR_FILE) as f:
        ocr = json.load(f)
    items = extract_items_with_anchor(ocr['pages'])
    print(f"OCR 解析: {len(items)} 条条款 (含内容要求/学业要求)")

    # 按 section 拆
    cr_items = [it for it in items if it.get('section') == '内容要求']
    ar_items = [it for it in items if it.get('section') == '学业要求']
    print(f"  内容要求: {len(cr_items)}, 学业要求: {len(ar_items)}")

    # 关键词词典: 给一些重要概念手动标记
    enriched = 0
    # 按 (stage, domain) 分组 OCR 条款
    from collections import defaultdict
    cr_grouped = defaultdict(list)
    ar_grouped = defaultdict(list)
    for it in cr_items:
        k = (it.get('stage', ''), it.get('domain', ''))
        cr_grouped[k].append(it)
    for it in ar_items:
        k = (it.get('stage', ''), it.get('domain', ''))
        ar_grouped[k].append(it)

    for n in data['nodes']:
        summary = n.get('summary', '') + ' ' + n.get('title', '')
        # 推 stage
        gs = n.get('grade_start', 1)
        stage_name = {1: '第一学段', 3: '第二学段', 5: '第三学段', 7: '第四学段'}.get(gs, None)
        domain = n.get('domain', '')

        # 先尝试精确匹配
        cr_match = find_matching_item(summary, cr_items, '内容要求', stage_name, domain)
        ar_match = find_matching_item(summary, ar_items, '学业要求', stage_name, domain)

        # 若精确匹配失败, 用同 (stage, domain) 段所有内容要求合并
        if not cr_match:
            group = cr_grouped.get((stage_name, domain), [])
            if group:
                # 优先选包含 n 标题关键词的, 否则用该组第一条
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
                # 把同组学业要求合并成一段
                combined = ' '.join(it['text'] for it in group)
                # 找最相关的
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

        if cr_match:
            # 优先用原文; 如果原文和 summary 高度重合, 加 summary 补充
            n['content_req'] = cr_match['text']
            n['src_page'] = cr_match['page']
            n['src_stage'] = cr_match.get('stage', '')
            n['src_domain_ocr'] = cr_match.get('domain', '')
            if cr_match['examples']:
                n['examples'] = cr_match['examples']
            # 补上 summary 里的额外信息
            if n.get('summary') and n['summary'] not in n['content_req']:
                n['content_req'] = n['content_req'] + '。' + n['summary']
            enriched += 1
        else:
            n['content_req'] = n.get('summary', '')
            n['src_page'] = None

        if ar_match:
            n['academic_req'] = ar_match['text']
        else:
            # 找同 stage 同 domain 的学业要求合并
            group = ar_grouped.get((stage_name, domain), [])
            if group:
                n['academic_req'] = ' '.join(it['text'] for it in group[:3])[:300]

        n['bloom'] = extract_bloom(n['content_req'] + ' ' + n.get('summary', ''))
        n['key_points'] = extract_key_points(n['content_req'])
        n['estimated_minutes'] = estimate_minutes(n.get('difficulty', 2))

    print(f"匹配到原文: {enriched}/{len(data['nodes'])} ({enriched/len(data['nodes'])*100:.1f}%)")

    # 验证
    has_cr = sum(1 for n in data['nodes'] if n.get('content_req') and len(n['content_req']) > 15)
    has_ar = sum(1 for n in data['nodes'] if n.get('academic_req'))
    has_ex = sum(1 for n in data['nodes'] if n.get('examples'))
    has_bloom = sum(1 for n in data['nodes'] if n.get('bloom'))
    print(f"  content_req 完整: {has_cr}")
    print(f"  academic_req: {has_ar}")
    print(f"  examples: {has_ex}")
    print(f"  bloom: {has_bloom}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    enrich()
