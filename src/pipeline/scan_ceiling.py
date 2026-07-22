"""
新课标知识上限盘点 — 扫描 14 学科 OCR 的"内容要求"条款数
目标: 不预设要 1000 还是 2000 概念,先看课标本身能拆出多少
"""

import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent.parent
OCR_DIR = ROOT / "data" / "parsed"

# 课标结构: 几乎所有学科用 "内容要求" / "学习内容" / "学业要求" / "内容要求"
# 计数口径: "内容要求" 段下的所有 (数字). 条款

CONTENT_REQ_KEYWORDS = ["内容要求", "学习内容", "学段目标", "学习要求", "内容要求."]
ACADEMIC_REQ_KEYWORDS = ["学业要求"]
# 一些学科用 "一级主题" / "学习主题" / "大概念" / "任务群" 作内容组织
TOPIC_KEYWORDS = ["一级主题", "学习主题", "大概念", "主题活动", "任务群", "内容要求"]


def extract_requirements(pages, kw):
    """从 OCR 页面里提所有 kw 段下的 (数字). 条款"""
    items = []
    in_section = False
    cur_section = None
    for p in pages:
        text = p['text']
        lines = text.split('\n')
        for ln in lines:
            # 段标: 【内容要求】 / 【学习内容】 等
            if '【' in ln and any(k in ln for k in kw):
                in_section = True
                cur_section = ln
                continue
            # 段结束: 【学业要求】 / 【教学提示】 / 下一【...】
            if in_section and ('【' in ln and not any(k in ln for k in kw)):
                in_section = False
                cur_section = None
                continue
            if in_section:
                # 匹配 "(1) xxx" / "1.1.1 xxx" / "1.1 xxx" / "(CL) xxx"
                m = re.match(r'^\s*[\(（]?(\d+(?:[\.\d]*)?)[\)）\.、]\s*(.{8,200})', ln)
                if m:
                    items.append({
                        'section': cur_section,
                        'num': m.group(1),
                        'text': m.group(2).strip(),
                    })
    return items


def extract_topic_or_bullet_lists(pages):
    """从 OCR 页面里提所有'1. xxx' / '主题 N: xxx' / 列表项"""
    items = []
    for p in pages:
        text = p['text']
        lines = text.split('\n')
        for ln in lines:
            # 匹配 "1. xxx" / "主题 1: xxx" / "(1) xxx"
            m = re.match(r'^\s*[\(（]?(\d+(?:[\.\d]*)?)[\)）\.、:：]\s*(.{8,200})', ln)
            if m:
                items.append({
                    'num': m.group(1),
                    'text': m.group(2).strip(),
                })
            # 任务群 / 主题活动 / 一级主题
            if re.match(r'^\s*(任务群|主题活动|一级主题|大概念|学习主题)\s*[\d一二三四五六七八九十]+', ln):
                items.append({
                    'num': '0',
                    'text': ln.strip()[:120],
                })
    return items


def count_concepts_in_text(text):
    """估算一条要求里能拆几个知识点
    启发: 数 '和'/'与'/'/' 等并列连词数量, 加上主谓宾
    """
    if not text:
        return 1
    # 数 (a) (b) (c) 形式
    paren = len(re.findall(r'[①②③④⑤⑥⑦⑧⑨]|[\(（][a-z一二三四五六七八九][\)）]', text))
    # 数并列: 和/与/以及/、/;/"
    parallel = text.count('和') + text.count('与') + text.count('以及') + text.count('、')
    # 数动词: 会/能/了解/认识/掌握/理解/经历/探索/知道/发现
    verbs = len(re.findall(r'会|能|了解|认识|掌握|理解|经历|探索|知道|发现|感受|体会|运用|分析|比较|计算|推导|说明|设计|制作|实验|调查|查阅|识别|分类|描述|表达|欣赏|朗读|背诵|复述|转述|讲述|默写|拼写|拼读|认读|识记|背诵', text))
    # 估算
    base = 1
    base += min(paren, 4)
    base += min(parallel, 3)
    base += min(verbs // 2, 3)
    return min(base, 6)


SUBJECT_FILES = {
    'math': '04_数学_ocr.json',
    'chinese': '02_语文_ocr.json',
    'english': '05_英语_ocr.json',
    'physics': '10_物理_ocr.json',
    'chemistry': '11_化学_ocr.json',
    'biology': '12_生物_ocr.json',
    'history': '03_历史_ocr.json',
    'geography': '08_地理_ocr.json',
    'morality_law': '01_道德与法治_ocr.json',
    'science': '09_科学_ocr.json',
    'info_tech': '13_信息科技_ocr.json',
    'art': '15_艺术_ocr.json',
    'pe_health': '14_体育与健康_ocr.json',
    'labor': '16_劳动_ocr.json',
}


def scan_subject(name, fname):
    path = OCR_DIR / fname
    if not path.exists():
        return None
    with open(path) as f:
        d = json.load(f)
    pages = d['pages']
    # 字面搜"内容要求"/"学习内容"/"学段目标" 作为锚点,取其前后 800 字作为一段
    cr_items = []
    for p in pages:
        text = p['text']
        for kw in ['内容要求', '学习内容', '学段目标', '学习要求']:
            idx = 0
            while True:
                i = text.find(kw, idx)
                if i < 0:
                    break
                # 取该位置之后的 600 字符作为一段
                snippet = text[i:i+600]
                # 在这段里提 (1) (2) 条款
                for ln in snippet.split('\n'):
                    m = re.match(r'^\s*[\(（]?(\d+(?:[\.\d]*)?)[\)）\.、]\s*(.{8,200})', ln)
                    if m:
                        cr_items.append({
                            'kw': kw,
                            'num': m.group(1),
                            'text': m.group(2).strip(),
                        })
                idx = i + len(kw)

    ar_items = []
    for p in pages:
        text = p['text']
        idx = 0
        while True:
            i = text.find('学业要求', idx)
            if i < 0:
                break
            snippet = text[i:i+400]
            for ln in snippet.split('\n'):
                m = re.match(r'^\s*[\(（]?(\d+(?:[\.\d]*)?)[\)）\.、]\s*(.{8,200})', ln)
                if m:
                    ar_items.append({
                        'num': m.group(1),
                        'text': m.group(2).strip(),
                    })
            idx = i + 4

    # 去重 (相同 num + text 视为重复)
    seen = set()
    cr_unique = []
    for it in cr_items:
        key = (it['num'], it['text'][:50])
        if key in seen:
            continue
        seen.add(key)
        cr_unique.append(it)

    # 估算概念数
    total_concepts_est = sum(count_concepts_in_text(it['text']) for it in cr_unique)
    # 学段数估算
    all_text = ' '.join(p['text'] for p in pages)
    stage_count = len(set(re.findall(r'(第一|第二|第三|第四)学段', all_text)))
    # 任务群 / 主题活动
    activity_items = []
    for p in pages:
        for ln in p['text'].split('\n'):
            if re.match(r'^\s*(主题活动|任务群|学习主题|一级主题|大概念|核心素养|学习任务群)\s*[\d一二三四五六七八九十]+', ln):
                activity_items.append(ln.strip()[:80])

    return {
        'subject': name,
        'pages': len(pages),
        'content_req_items': len(cr_unique),
        'academic_req_items': len(ar_items),
        'concepts_ceiling': total_concepts_est,
        'stages': stage_count,
        'activity_items': len(activity_items),
        'sample_items': cr_unique[:3],
    }


def main():
    print("=" * 80)
    print("📊 2022 新课标知识上限盘点")
    print("=" * 80)
    results = []
    for name, fname in SUBJECT_FILES.items():
        r = scan_subject(name, fname)
        if r:
            results.append(r)
    # 按理论上限排
    results.sort(key=lambda x: -x['concepts_ceiling'])

    print(f"\n{'学科':<12} {'页数':<6} {'内容要求条款':<14} {'理论上限概念':<14} {'主题/任务群':<10} {'学段':<6}")
    print("-" * 78)
    total_ceiling = 0
    total_current = 758  # V0.6 已完成
    for r in results:
        print(f"{r['subject']:<12} {r['pages']:<6} {r['content_req_items']:<14} {r['concepts_ceiling']:<14} {r.get('activity_items', 0):<10} {r.get('stages', 0):<6}")
        total_ceiling += r['concepts_ceiling']
    print("-" * 70)
    print(f"{'理论上限总计':<12} {'':<6} {'':<14} {total_ceiling:<14}")
    print(f"{'V0.6 已完成':<12} {'':<6} {'':<14} {total_current:<14}")
    print(f"{'完成度 (启发式)':<12} {'':<6} {'':<14} {total_current/total_ceiling*100:.1f}%")

    # 修正上限: 4 学科 OCR 颗粒度低, 实际应更高
    ocr_low_quality = ['morality_law', 'geography', 'art', 'labor']
    low_subjects = [r for r in results if r['subject'] in ocr_low_quality]
    ocr_low_count = len(low_subjects)
    # 4 学科每科补回 ~50 (实际课标平均)
    corrected = total_ceiling + ocr_low_count * 50
    # 主题/任务群细分增量: 实际可拆 1.3-1.5x
    corrected = int(corrected * 1.3)
    print(f"\n{'修正上限 (含 OCR 补回 + 主题细分)':<30} {'':<6} {'':<14} {corrected:<14}")
    print(f"{'修正完成度':<30} {'':<6} {'':<14} {total_current/corrected*100:.1f}%")
    print(f"\n⚠️ OCR 颗粒度低学科: {ocr_low_quality}")
    print(f"   道法/艺术/劳动/地理 实际课标内容丰富, OCR 标'内容要求'字面太少")
    print(f"   补回 4 学科 × 50 ≈ 200 + 主题细分 1.3x ≈ {corrected}")

    # 估算含主题/任务群的总上限
    print("\n" + "=" * 80)
    print("📌 理论上限拆解说明")
    print("=" * 80)
    print("""
1. 内容要求条款: OCR 里"【内容要求】"段下的 (1) (2) (3) ... 条款
2. 理论上限: 每条按"并列/动词/并列号"启发式拆 1-6 个知识点
3. 主题/任务群: OCR 里的"主题活动N"/"任务群N"/"一级主题"/"大概念"等大粒度内容
4. 实际可拆上限 = 内容要求拆解上限 + 主题/任务群

⚠️ 这是"启发式估算"上限,不是"承诺一定能做多少"
   实际拆解会因学段差异/课标粗细不同而浮动 ±20%
""")

    # 详细写每学科前 3 条 sample
    print("\n" + "=" * 80)
    print("📋 各学科前 3 条内容要求样本")
    print("=" * 80)
    for r in results:
        print(f"\n--- {r['subject']} ---")
        for it in r['sample_items']:
            print(f"  ({it['num']}) {it['text'][:100]}")

    # ============================================================================
    # V3.0 实际概念数 (从 data/graph/all_v3.0.json 读)
    # ============================================================================
    GRAPH_DIR = Path(__file__).parent.parent.parent / "data" / "graph"
    print("\n" + "=" * 80)
    print("📊 V3.0 实际概念数")
    print("=" * 80)
    all_v3 = GRAPH_DIR / 'all_v3.0.json'
    v3_stats = {
        'scanned_at': None,
        'total_ceiling': total_ceiling,
        'corrected_ceiling': corrected,
        'subjects': {},
    }
    if all_v3.exists():
        with open(all_v3) as f:
            d = json.load(f)
        from collections import Counter
        by_subject = Counter(n['subject'] for n in d['nodes'])
        v3_stats['total_v3_concepts'] = len(d['nodes'])
        v3_stats['total_v3_edges'] = len(d['edges'])
        v3_stats['total_v0_8_concepts'] = total_current
        v3_stats['growth'] = len(d['nodes']) - total_current
        v3_stats['growth_pct'] = round((len(d['nodes']) - total_current) / total_current * 100, 1)
        print(f"  V3.0 总数: {len(d['nodes'])} 节点 (V0.8 758 → +{len(d['nodes']) - total_current})")
        print(f"  V3.0 关系: {len(d['edges'])}")
        print(f"\n  {'学科':<14} {'V3.0':<6} {'理论上限':<10} {'达标率':<8}")
        for r in results:
            s = r['subject']
            v3_count = by_subject.get(s, 0)
            ceil = r['concepts_ceiling']
            ratio = (v3_count / ceil * 100) if ceil else 0
            v3_stats['subjects'][s] = {
                'v3_count': v3_count,
                'concepts_ceiling': ceil,
                'ratio_pct': round(ratio, 1),
            }
            print(f"  {s:<14} {v3_count:<6} {ceil:<10} {ratio:.1f}%")
    else:
        print(f"  ⚠️ {all_v3} 不存在, 请先跑 expand_concepts.py + merge_v3.0.py")

    # 达标检查
    if all_v3.exists():
        v3_total = len(d['nodes'])
        target = 1800
        print(f"\n  V3.0 目标: ≥ {target}")
        print(f"  实际: {v3_total}")
        if v3_total >= target:
            print(f"  ✅ 达标 (+{v3_total - target})")
        else:
            print(f"  ❌ 差 {target - v3_total}")

    # 写 v3.0_stats.json
    from datetime import datetime
    v3_stats['scanned_at'] = datetime.now().isoformat()
    stats_path = GRAPH_DIR / 'v3.0_stats.json'
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(v3_stats, f, ensure_ascii=False, indent=2)
    print(f"\n  📁 v3.0_stats.json: {stats_path}")


if __name__ == "__main__":
    main()
