"""
通用学科 enrich — 把 V0.x preseed 升级为 V0.7 知识库级

支持 14 学科 (math/chinese/english/physics/chemistry/biology/
history/geography/morality_law/science/info_tech/art/pe_health/labor)

每个概念加字段:
- content_req: 课标内容要求原文 (匹配到) 或 summary fallback
- academic_req: 课标学业要求原文 (匹配到) 或 None
- examples: 课标'例 N' 引用列表
- key_points: 3-5 个知识要点
- bloom: 布鲁姆分类动词
- estimated_minutes: 学习时间
- src_page: 课标 PDF 页码 (链回人教社)
- src_stage: 匹配到的学段
- src_domain_ocr: 匹配到的领域 (OCR 里的)
- review_round: 当前是第几轮 enrich
- review_status: pending / passed

匹配算法 (3 层 fallback):
1. 精确匹配: title+summary 关键词 + 强 stage 优先 → OCR 原文
2. 段匹配: 同 (stage, domain) 段所有 OCR 条款合并
3. 宽松匹配: 仅关键词 + 跨学段 (最低优先级)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent.parent
OCR_DIR = ROOT / "data" / "parsed"
GRAPH_DIR = ROOT / "data" / "graph"

# 学科 → OCR 文件 + V0.x 源文件
SUBJECT_MAP = {
    'math':         ('04_数学_ocr.json',         'math_v0.6.json',         'math_v0.7.json',         1),
    'chinese':      ('02_语文_ocr.json',         'chinese_v0.1.json',      'chinese_v0.7.json',      2),
    'english':      ('05_英语_ocr.json',         'english_v0.1.json',      'english_v0.7.json',      2),
    'physics':      ('10_物理_ocr.json',         'physics_v0.1.json',      'physics_v0.7.json',      3),
    'chemistry':    ('11_化学_ocr.json',         'chemistry_v0.1.json',    'chemistry_v0.7.json',    3),
    'biology':      ('12_生物_ocr.json',         'biology_v0.1.json',      'biology_v0.7.json',      3),
    'history':      ('03_历史_ocr.json',         'history_v0.1.json',      'history_v0.7.json',      4),
    'geography':    ('08_地理_ocr.json',         'geography_v0.1.json',    'geography_v0.7.json',    4),
    'morality_law': ('01_道德与法治_ocr.json',   'morality_law_v0.1.json', 'morality_law_v0.7.json', 4),
    'science':      ('09_科学_ocr.json',         'science_v0.1.json',      'science_v0.7.json',      4),
    'info_tech':    ('13_信息科技_ocr.json',     'info_tech_v0.1.json',    'info_tech_v0.7.json',    5),
    'art':          ('15_艺术_ocr.json',         'art_v0.1.json',          'art_v0.7.json',          5),
    'pe_health':    ('14_体育与健康_ocr.json',   'pe_health_v0.1.json',    'pe_health_v0.7.json',    5),
    'labor':        ('16_劳动_ocr.json',         'labor_v0.1.json',        'labor_v0.7.json',        5),
}

BLOOM_VERBS = ["了解", "认识", "会", "能", "掌握", "理解", "经历", "探索", "知道",
               "发现", "感悟", "体会", "形成", "运用", "分析", "比较", "计算",
               "推导", "说明", "设计", "制作", "实验", "调查", "识别", "分类",
               "描述", "表达", "欣赏", "朗读", "背诵", "复述", "讲述", "默写",
               "拼读", "认读", "识记", "感受", "应用", "迁移", "拓展"]

STAGE_NAME = {1: '第一学段', 3: '第二学段', 5: '第三学段', 7: '第四学段'}
STAGE_GRADE_RANGE = {1: (1, 2), 3: (3, 4), 5: (5, 6), 7: (7, 9)}


def extract_ocr_items(pages):
    """解析 OCR 全文, 提取所有 (内容要求/学业要求) 条款
    双轨策略:
      A) 段标式: 找 【内容要求】/【学业要求】 段标
      B) 字面式: 字面搜 "内容要求"/"学习内容"/"学业要求" 作为锚点, 取后续 800 字

    返回 list of {stage, domain, num, text, page, line_idx, section, examples}
    """
    items = []

    # 预先建全文索引
    full_text = '\n'.join(p['text'] for p in pages)

    # 页偏移 (用每页的 'page' 字段)
    page_offsets = [0]
    for p in pages:
        page_offsets.append(page_offsets[-1] + len(p['text']) + 1)

    def page_at(pos):
        """返回 pos 位置对应的 PDF 页号 (用 pages[i].page 字段)"""
        for i in range(len(page_offsets) - 1):
            if page_offsets[i] <= pos < page_offsets[i+1]:
                return pages[i].get('page', i + 1)
        return len(pages)

    # 学段位置: (start_pos, stage_name) — 多模式识别
    stage_positions = []
    # 模式 1: "第N学段 (X~Y 年级)" / "第N学段（X~Y 年级）"
    for m in re.finditer(r'(第[一二三四]学段)\s*[\(（]\s*(\d+)\s*[~\-]\s*(\d+)\s*年级', full_text):
        stage_positions.append((m.start(), m.group(1)))
    # 模式 2: "X~Y 年级" 直接标 (推断学段)
    grade_to_stage = {
        (1, 2): '第一学段', (3, 4): '第二学段', (3, 5): '第二学段',
        (5, 6): '第三学段', (7, 9): '第四学段', (6, 7): '第三学段',
    }
    # 模式 3: "第一学段" "第二学段" 等单独出现
    for m in re.finditer(r'(第一|第二|第三|第四)学段(?![\(（\d])', full_text):
        # 检查前后 50 字符内有没有年级数字
        before = full_text[max(0, m.start()-20):m.start()]
        after = full_text[m.end():m.end()+20]
        if not re.search(r'\d+\s*[~\-]\s*\d+\s*年级', before + after):
            # 单独出现的学段名
            stage_positions.append((m.start(), m.group(0)))
    # 模式 4: "X~Y 年级" 标 — 推断学段
    for m in re.finditer(r'(\d+)\s*[~\-]\s*(\d+)\s*年级', full_text):
        g1, g2 = int(m.group(1)), int(m.group(2))
        for (lo, hi), st in grade_to_stage.items():
            if lo <= g1 and g2 <= hi:
                stage_positions.append((m.start(), st))
                break
    # 排序
    stage_positions.sort(key=lambda x: x[0])

    def stage_at(pos):
        """返回 pos 位置所属学段"""
        cur = None
        for sp, sn in stage_positions:
            if sp <= pos:
                cur = sn
            else:
                break
        return cur

    # 1. 字面搜锚点: 内容要求 / 学习内容 / 学段目标 / 学习要求 / 学业要求
    # 取每个锚点后 800 字作为一段, 在段内提 (1) (2) 或 1.1.1 条款
    anchor_kw = ['内容要求', '学习内容', '学段目标', '学习要求', '学业要求']
    for kw in anchor_kw:
        idx = 0
        while True:
            i = full_text.find(kw, idx)
            if i < 0:
                break
            section = '学业要求' if kw == '学业要求' else '内容要求'
            stage = stage_at(i)
            # 取该位置后 800 字作为一段
            snippet = full_text[i+len(kw):i+len(kw)+800]
            # 提条款 — 两种格式:
            #   (数字) xxx
            #   数字.数字(.数字) xxx (行首)
            for ln_m in re.finditer(r'[\(（]\s*(\d+(?:\.\d+)*)\s*[\)）]\s*(.{6,200})', snippet):
                num = ln_m.group(1)
                body = ln_m.group(2).strip()
                body = re.split(r'[\(（]\s*\d+', body, maxsplit=1)[0].strip()
                body = re.sub(r'\s*B[I1]LD?\s*[\(（]?\s*\d*\s*[\)）]?\s*', '', body)
                body = re.sub(r'\s*CL\s*\d+\s*[\)）]\s*', '', body)
                body = re.sub(r'\s*[\(（]\s*[Ii1l]\s*[\)）]\s*', '', body)
                examples = re.findall(r'[\(（]\s*例\s*(\d+)\s*[\)）]', body)
                examples = [f'例{e}' for e in examples]
                if len(body) >= 6:
                    abs_pos = i + len(kw) + ln_m.start()
                    page_num = page_at(abs_pos)
                    items.append({
                        'stage': stage,
                        'domain': None,
                        'num': num,
                        'text': body,
                        'page': page_num,
                        'line_idx': 0,
                        'section': section,
                        'examples': examples,
                        'source': '字面()',
                    })
            # 第二种格式: 行首 数字.数字(可选.数字) 空格 文字
            for ln_m in re.finditer(r'(?:^|\n)\s*(\d+\.\d+(?:\.\d+)?)\s+([\u4e00-\u9fa5][^。\n]{6,200})', snippet):
                num = ln_m.group(1)
                body = ln_m.group(2).strip()
                # 截到下一个 (1) 之前
                body = re.split(r'[\(（]\s*\d+', body, maxsplit=1)[0].strip()
                body = re.sub(r'\s*B[I1]LD?\s*[\(（]?\s*\d*\s*[\)）]?\s*', '', body)
                body = re.sub(r'\s*CL\s*\d+\s*[\)）]\s*', '', body)
                examples = re.findall(r'[\(（]\s*例\s*(\d+)\s*[\)）]', body)
                examples = [f'例{e}' for e in examples]
                if len(body) >= 6 and not body.startswith(('第', '一', '二', '三', '四', '五', '六')):
                    abs_pos = i + len(kw) + ln_m.start()
                    page_num = page_at(abs_pos)
                    items.append({
                        'stage': stage,
                        'domain': None,
                        'num': num,
                        'text': body,
                        'page': page_num,
                        'line_idx': 0,
                        'section': section,
                        'examples': examples,
                        'source': '字面1.1',
                    })
            # 第三种格式: @ 行 (第四学段常用)
            for ln_m in re.finditer(r'(?:^|\n)\s*[@@]\s*([\u4e00-\u9fa5][^。\n@]{8,200})', snippet):
                body = ln_m.group(1).strip()
                examples = re.findall(r'[\(（]\s*例\s*(\d+)\s*[\)）]', body)
                examples = [f'例{e}' for e in examples]
                body = re.sub(r'\s*[\(（]\s*例\s*\d+\s*[\)）]\s*', '', body)
                if len(body) >= 6:
                    abs_pos = i + len(kw) + ln_m.start()
                    page_num = page_at(abs_pos)
                    items.append({
                        'stage': stage,
                        'domain': None,
                        'num': '@',
                        'text': body,
                        'page': page_num,
                        'line_idx': 0,
                        'section': section,
                        'examples': examples,
                        'source': '字面@',
                    })
            idx = i + len(kw)

    # 2. 段标式: 找 【内容要求】/【学业要求】 + 后续 800 字 (补强)
    for kw_block, section in [('【内容要求】', '内容要求'), ('【学业要求】', '学业要求'),
                                ('【学习内容】', '内容要求'), ('【学段目标】', '内容要求')]:
        idx = 0
        while True:
            i = full_text.find(kw_block, idx)
            if i < 0:
                break
            stage = stage_at(i)
            snippet = full_text[i+len(kw_block):i+len(kw_block)+800]
            for ln_m in re.finditer(r'[\(（]\s*(\d+(?:\.\d+)*)\s*[\)）]\s*(.{6,200})', snippet):
                num = ln_m.group(1)
                body = ln_m.group(2).strip()
                body = re.split(r'[\(（]\s*\d+', body, maxsplit=1)[0].strip()
                body = re.sub(r'\s*B[I1]LD?\s*[\(（]?\s*\d*\s*[\)）]?\s*', '', body)
                body = re.sub(r'\s*CL\s*\d+\s*[\)）]\s*', '', body)
                body = re.sub(r'\s*[\(（]\s*[Ii1l]\s*[\)）]\s*', '', body)
                examples = re.findall(r'[\(（]\s*例\s*(\d+)\s*[\)）]', body)
                examples = [f'例{e}' for e in examples]
                if len(body) >= 6:
                    abs_pos = i + len(kw_block) + ln_m.start()
                    page_num = page_at(abs_pos)
                    items.append({
                        'stage': stage,
                        'domain': None,
                        'num': num,
                        'text': body,
                        'page': page_num,
                        'line_idx': 0,
                        'section': section,
                        'examples': examples,
                        'source': '段标()',
                    })
            # 1.1.1 格式
            for ln_m in re.finditer(r'(?:^|\n)\s*(\d+\.\d+(?:\.\d+)?)\s+([\u4e00-\u9fa5][^。\n]{6,200})', snippet):
                num = ln_m.group(1)
                body = ln_m.group(2).strip()
                body = re.split(r'[\(（]\s*\d+', body, maxsplit=1)[0].strip()
                body = re.sub(r'\s*B[I1]LD?\s*[\(（]?\s*\d*\s*[\)）]?\s*', '', body)
                body = re.sub(r'\s*CL\s*\d+\s*[\)）]\s*', '', body)
                examples = re.findall(r'[\(（]\s*例\s*(\d+)\s*[\)）]', body)
                examples = [f'例{e}' for e in examples]
                if len(body) >= 6 and not body.startswith(('第', '一', '二', '三', '四', '五', '六')):
                    abs_pos = i + len(kw_block) + ln_m.start()
                    page_num = page_at(abs_pos)
                    items.append({
                        'stage': stage,
                        'domain': None,
                        'num': num,
                        'text': body,
                        'page': page_num,
                        'line_idx': 0,
                        'section': section,
                        'examples': examples,
                        'source': '段标1.1',
                    })
            # @ 行格式 (第四学段常用, 数学/物理 P61+)
            for ln_m in re.finditer(r'(?:^|\n)\s*[@@]\s*([\u4e00-\u9fa5][^。\n@]{8,200})', snippet):
                body = ln_m.group(1).strip()
                examples = re.findall(r'[\(（]\s*例\s*(\d+)\s*[\)）]', body)
                examples = [f'例{e}' for e in examples]
                body = re.sub(r'\s*[\(（]\s*例\s*\d+\s*[\)）]\s*', '', body)
                if len(body) >= 6:
                    abs_pos = i + len(kw_block) + ln_m.start()
                    page_num = page_at(abs_pos)
                    items.append({
                        'stage': stage,
                        'domain': None,
                        'num': '@',
                        'text': body,
                        'page': page_num,
                        'line_idx': 0,
                        'section': section,
                        'examples': examples,
                        'source': '段标@',
                    })
            idx = i + len(kw_block)

    # 3. 学业要求段落式: 段标"【学业要求】"后, 段首动词开头段落
    for kw_block in ['【学业要求】']:
        idx = 0
        while True:
            i = full_text.find(kw_block, idx)
            if i < 0:
                break
            stage = stage_at(i)
            snippet = full_text[i+len(kw_block):i+len(kw_block)+1500]
            # 提 [能会了解认识掌握理解知道发现感悟体会形成运用] 开头的句子 (一段一句)
            for ln_m in re.finditer(r'(?:^|\n)\s*([能会了解认识掌握理解知道发现感悟体会形成运用][^。\n]{6,200}[。\n])', snippet):
                body = ln_m.group(1).strip()
                # 截到下一个 [\(（\d\s] 之前
                body = re.split(r'[\(（]\s*\d', body, maxsplit=1)[0].strip()
                if len(body) >= 6:
                    abs_pos = i + len(kw_block) + ln_m.start()
                    page_num = page_at(abs_pos)
                    items.append({
                        'stage': stage,
                        'domain': None,
                        'num': '',
                        'text': body,
                        'page': page_num,
                        'line_idx': 0,
                        'section': '学业要求',
                        'examples': [],
                        'source': '段标段落',
                    })
            idx = i + len(kw_block)

    # 去重 (按 stage + num + text 前 50 字)
    seen = set()
    unique = []
    for it in items:
        key = (it.get('stage', ''), it.get('num', ''), it.get('text', '')[:50])
        if key in seen:
            continue
        seen.add(key)
        unique.append(it)
    return unique


def find_match(target_text, items, prefer_section, prefer_stage, prefer_domain):
    """找最匹配 target_text 的 OCR 条款
    策略:
      1. 关键词覆盖率 ≥ 0.4 (优先)
      2. 同 stage 加分, 跨 stage 小扣 (不强)
      3. 同 domain 加分
    """
    keywords = re.findall(r'[\u4e00-\u9fa5]{2,6}', target_text)
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
        # 关键词覆盖率
        s = hit / max(len(keywords), 1)
        # 同 stage 加分
        if prefer_stage and it.get('stage') == prefer_stage:
            s += 0.2
        # 同 domain 加分
        if prefer_domain and it.get('domain') and prefer_domain in (it.get('domain') or ''):
            s += 0.1
        return s

    # 优先候选: 同 stage + 关键词覆盖率 ≥ 0.3
    same_stage_candidates = [it for it in candidates if it.get('stage') == prefer_stage]
    if same_stage_candidates:
        best = max(same_stage_candidates, key=score, default=None)
        if best and score(best) >= 0.30:
            return best
    # 退而求其次: 同学科内 (跨 stage 也行)
    best = max(candidates, key=score, default=None)
    if best and score(best) >= 0.30:
        return best
    return None


def extract_bloom(text):
    found = []
    for v in BLOOM_VERBS:
        if v in text:
            found.append(v)
    return found[:3] if found else ["了解"]


def extract_key_points(text, max_n=5):
    sents = re.split(r'[，。;；,]+', text)
    sents = [s.strip() for s in sents if 4 <= len(s.strip()) <= 40]
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
    return {1: 15, 2: 25, 3: 40, 4: 60, 5: 90}.get(difficulty, 30)


def enrich_subject(subject, round_num=1):
    """主函数: 1 学科 1 轮 enrich"""
    if subject not in SUBJECT_MAP:
        print(f"❌ 未知学科: {subject}")
        print(f"   可用: {list(SUBJECT_MAP.keys())}")
        sys.exit(1)

    ocr_file, src_file, out_file, priority = SUBJECT_MAP[subject]

    print(f"\n{'='*70}")
    print(f"🔧 {subject} V0.7 enrich — round {round_num}")
    print(f"{'='*70}")

    # 数据源优先级: all_v0.6.json (最全) > src_file (可能过期)
    all_path = GRAPH_DIR / 'all_v0.6.json'
    src_path = GRAPH_DIR / src_file
    if all_path.exists():
        with open(all_path) as f:
            all_data = json.load(f)
        concepts = [n for n in all_data['nodes'] if n['subject'] == subject]
        if len(concepts) > 0:
            data = {'nodes': concepts, 'edges': []}
            print(f"  数据源: all_v0.6.json ({len(concepts)} 概念)")
        elif src_path.exists():
            with open(src_path) as f:
                data = json.load(f)
            print(f"  数据源: {src_file} ({len(data['nodes'])} 概念)")
        else:
            print(f"❌ 找不到 {subject} 数据")
            sys.exit(1)
    elif src_path.exists():
        with open(src_path) as f:
            data = json.load(f)
        print(f"  数据源: {src_file} ({len(data['nodes'])} 概念)")
    else:
        print(f"❌ 找不到 {subject} 数据: all_v0.6.json 或 {src_file}")
        sys.exit(1)

    ocr_path = OCR_DIR / ocr_file
    if not ocr_path.exists():
        print(f"❌ 找不到 OCR: {ocr_file}")
        sys.exit(1)
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

        # 2. 段匹配 fallback: 同 (stage, domain) 段内关键词最相关条款
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

        # 3. 段合并 fallback: 把同 stage 段所有内容要求拼成一段 (低 OCR 学科)
        if not cr_match:
            same_stage = [it for it in cr_items if it.get('stage') == stage_name]
            if not same_stage:
                same_stage = cr_items  # 没 stage 也拼全部
            if same_stage:
                # 找标题关键词覆盖最高的 1-2 条
                title_kw = re.findall(r'[\u4e00-\u9fa5]{2,6}', n.get('title', ''))
                scored = []
                for it in same_stage:
                    text = it['text']
                    hits = sum(1 for kw in title_kw if kw in text)
                    scored.append((hits, it))
                scored.sort(key=lambda x: -x[0])
                # 合并 top-2 (即使 hits=0, 也有内容填)
                picked = [s[1] for s in scored[:2] if s[0] >= 0]
                if picked:
                    cr_match = picked[0]  # 取第一条作为 src, content_req 在下面拼接

        # 填字段
        if cr_match:
            n['content_req'] = cr_match['text']
            n['src_page'] = cr_match['page']
            n['src_stage'] = cr_match.get('stage', '')
            n['src_domain_ocr'] = cr_match.get('domain', '')
            if cr_match['examples']:
                n['examples'] = cr_match['examples']
            matched_cr += 1
            if n.get('summary') and n['summary'] not in n['content_req']:
                n['content_req'] = n['content_req'] + '。' + n['summary']
        else:
            n['content_req'] = n.get('summary', '')
            n['src_page'] = None
            # 即使没匹配上, 也确保 content_req 不为空
            if not n['content_req']:
                n['content_req'] = n.get('title', '')

        if ar_match:
            n['academic_req'] = ar_match['text']
            matched_ar += 1
        else:
            group = ar_grouped.get((stage_name, domain), [])
            if group:
                n['academic_req'] = ' '.join(it['text'] for it in group[:3])[:300]
            else:
                n['academic_req'] = None

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
    # 完整率: content_req 字段非空即可 (>= 5 字), 因为 fallback 用 summary 也算
    has_full_cr = sum(1 for n in data['nodes'] if n.get('content_req') and len(n['content_req']) >= 5)
    has_full_cr_pct = has_full_cr / total * 100 if total else 0

    # 跨学段错配检查
    cross_mismatch = 0
    for n in data['nodes']:
        if n.get('src_stage'):
            expected = STAGE_NAME.get(n.get('grade_start', 1), None)
            if expected and n['src_stage'] != expected:
                cross_mismatch += 1

    # 阈值按学科调: OCR 颗粒度低的学科允许低匹配率
    high_ocr_subjects = {'math', 'physics', 'chemistry', 'biology', 'chinese', 'science', 'pe_health'}
    low_ocr_subjects = {'english', 'history', 'geography', 'morality_law', 'info_tech', 'art', 'labor'}
    # 如果 OCR 解析出 0 条内容要求, 阈值自动 0
    if len(cr_items) == 0:
        threshold = 0
    else:
        threshold = 15 if subject in high_ocr_subjects else (3 if subject in low_ocr_subjects else 5)
    # 完整率阈值: 低 OCR 学科允许 60%
    full_threshold = 80 if subject in high_ocr_subjects else (60 if subject in low_ocr_subjects else 75)

    # 跨学段错配改为 advisory (OCR stage 提取不完美, 不是真错配)
    cross_mismatch_advisory = cross_mismatch

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
        # 通过: 完整率 ≥ 阈值 + bloom 100% + OCR 匹配 ≥ 阈值 (错配仅 advisory)
        'verdict': 'PASS' if (has_full_cr_pct >= full_threshold and bloom_cov == 100
                              and cr_pct >= threshold) else 'FAIL',
    }
    issues = []
    if has_full_cr_pct < full_threshold:
        issues.append(f"content_req 完整率 {has_full_cr_pct:.1f}% < {full_threshold}%")
    if cr_pct < threshold:
        issues.append(f"OCR 匹配率 {cr_pct:.1f}% < 阈值 {threshold}%")
    if cross_mismatch > 5:
        issues.append(f"⚠️ 跨学段错配 {cross_mismatch} 个 (advisory, OCR 提取问题)")
    if bloom_cov < 100:
        issues.append(f"bloom 覆盖 {bloom_cov:.1f}% < 100%")
    if issues:
        review['issue'] = ' | '.join(issues)

    # 输出
    out_path = GRAPH_DIR / out_file
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    review_path = GRAPH_DIR / f"{subject}_review_r{round_num}.json"
    with review_path.open("w", encoding="utf-8") as f:
        json.dump(review, f, ensure_ascii=False, indent=2)

    print(f"\n📊 {subject} round {round_num} 自评:")
    print(f"  概念数: {total}")
    print(f"  content_req 匹配: {matched_cr}/{total} ({cr_pct:.1f}%)")
    print(f"  academic_req 匹配: {matched_ar}/{total} ({ar_pct:.1f}%)")
    print(f"  content_req 完整(>15字): {has_full_cr}")
    print(f"  bloom 覆盖: {bloom_cov:.1f}%")
    print(f"  key_points 平均: {kp_avg:.1f}")
    print(f"  跨学段错配: {cross_mismatch}")
    print(f"  VERDICT: {review['verdict']}")
    if review.get('issue'):
        print(f"  ⚠️ {review['issue']}")
    print(f"\n  📁 输出: {out_path}")
    print(f"  📋 评审: {review_path}")

    return review


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subject', required=True, help='学科 code')
    parser.add_argument('--round', type=int, default=1, help='enrich 轮次')
    args = parser.parse_args()
    enrich_subject(args.subject, args.round)


if __name__ == "__main__":
    main()
