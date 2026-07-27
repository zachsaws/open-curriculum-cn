#!/usr/bin/env python3
"""
Open Curriculum CN — 概念质量审查脚本 (V3.6.10c)
扫描 data/graph/all_v3.3.json 里每个概念, 检查缺什么字段 / 质量如何.
输出: 控制台报告 + JSON 报告 (audit_report.json) + 概念缺字段排行 (top 30).

用法:
  python3 tools/audit_concepts.py
  python3 tools/audit_concepts.py --subject math
  python3 tools/audit_concepts.py --json audit_report.json

检查项 (V3.3.5 LLM 增强后):
- 内容三件套: description / assessment_prompt / key_points (3 条)
- 教学三件套: teaching_voice / real_examples / common_mistakes / teaching_activity
- 基础元数据: title / grade_start+end / type / difficulty / bloom / centrality
- 课标引用: content_req / academic_req / src_page
- 质量: description 长度 (期望 60-150) / assessment_prompt 长度 (期望 100-220) / teaching_voice 长度 (>= 30)
- 占位符: {{name}} 在 description / assessment / teaching_voice 里 3 次
- 禁词: 理解/培养/掌握/运用/含义/定义 (V3.3.5 后处理不该出现)
"""
import json
import argparse
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
DATA = ROOT / 'data' / 'graph' / 'all_v3.7_p1.json'  # V3.7+ P0 补完版本
DATA_FALLBACK = ROOT / 'data' / 'graph' / 'all_v3.3.json'  # 旧版本

# V3.7.1: 默认读 V3.7, 不存在则回退 V3.3.5
if not DATA.exists() and DATA_FALLBACK.exists():
    DATA = DATA_FALLBACK

REQUIRED_FIELDS = ['id', 'title', 'subject', 'grade_start', 'grade_end']
CONTENT_TRIPLE = ['description', 'assessment_prompt', 'key_points']
TEACHING_TRIPLE = ['teaching_voice', 'real_examples', 'common_mistakes', 'teaching_activity']
METADATA = ['type', 'difficulty', 'bloom', 'centrality', 'estimated_minutes']
CURRICULUM = ['content_req', 'academic_req', 'src_page']

# 长度阈值 (V3.3.5 LLM 增强规范)
DESC_MIN, DESC_MAX = 50, 200
ASSESS_MIN, ASSESS_MAX = 80, 280
TV_MIN = 25  # teaching_voice
NAME_PLACEHOLDER = '{{name}}'
NAME_EXPECT = 3
FORBIDDEN = ['理解', '培养', '掌握', '运用', '含义', '定义']


def audit_node(node):
    """检查一个概念, 返回缺什么 + 质量问题."""
    issues = []  # 字段缺失
    quality = []  # 质量问题 (长度/占位符/禁词)
    score = 100  # 完整度 (扣分制)

    # 1. 必填字段
    for f in REQUIRED_FIELDS:
        if not node.get(f):
            issues.append(f'缺 {f}')
            score -= 5

    # 2. 内容三件套
    desc = (node.get('description') or '').strip()
    assess = (node.get('assessment_prompt') or '').strip()
    kp = node.get('key_points') or []
    if not desc:
        issues.append('缺 description')
        score -= 15
    if not assess:
        issues.append('缺 assessment_prompt')
        score -= 15
    if not kp:
        issues.append('缺 key_points')
        score -= 10
    elif len(kp) < 3:
        issues.append(f'key_points 只 {len(kp)} 条 (< 3)')
        score -= 5

    # 3. 教学三件套 (有更好, 不强制)
    # V3.6.9: teaching_voice block 在 UI 上复用 description 字段 (没单独 LLM 生成教学话术)
    # 审查时: 有 description 就算有"教学话术"显示
    tv = (node.get('teaching_voice') or node.get('description') or '').strip()
    if not tv:
        quality.append('缺 teaching_voice/description (老师可用性)')
        score -= 5
    for f in ['real_examples', 'common_mistakes', 'teaching_activity']:
        if not (node.get(f) or '').strip():
            quality.append(f'缺 {f}')

    # 4. 元数据
    for f in METADATA:
        if not node.get(f):
            issues.append(f'缺 {f}')
            score -= 2

    # 5. 课标引用
    for f in CURRICULUM:
        v = node.get(f)
        if f == 'src_page':
            if not v:
                issues.append(f'缺 {f}')
                score -= 3
        else:
            if not (v or '').strip():
                issues.append(f'缺 {f}')
                score -= 3

    # 6. 长度
    if desc and not (DESC_MIN <= len(desc) <= DESC_MAX):
        quality.append(f'description 长度 {len(desc)} (期望 {DESC_MIN}-{DESC_MAX})')
    if assess and not (ASSESS_MIN <= len(assess) <= ASSESS_MAX):
        quality.append(f'assessment 长度 {len(assess)} (期望 {ASSESS_MIN}-{ASSESS_MAX})')
    if tv and len(tv) < TV_MIN:
        quality.append(f'teaching_voice 长度 {len(tv)} (>= {TV_MIN})')

    # 7. {{name}} 占位符 (V3.7.1: academic_req 是课标原文语气, 不需要 {{name}})
    for f, val in [('description', desc), ('assessment_prompt', assess), ('teaching_voice', tv)]:
        cnt = val.count(NAME_PLACEHOLDER)
        if val and cnt != NAME_EXPECT:
            quality.append(f'{f} 含 {{name}} {cnt} 次 (期望 {NAME_EXPECT})')

    # 8. 禁词
    for word in FORBIDDEN:
        for f, val in [('description', desc), ('assessment_prompt', assess), ('teaching_voice', tv), ('content_req', node.get('content_req', ''))]:
            if word in val:
                quality.append(f'{f} 含禁词 "{word}"')

    # 9. type 检查
    if node.get('type') and node['type'] not in ('FACTUAL', 'PROCEDURAL', 'CONCEPTUAL'):
        quality.append(f"type 异常: {node['type']}")

    return {
        'id': node.get('id', 'NO_ID'),
        'title': node.get('title', 'NO_TITLE'),
        'subject': node.get('subject', 'unknown'),
        'grade': f"{node.get('grade_start', '?')}-{node.get('grade_end', '?')}",
        'type': node.get('type', ''),
        'score': max(score, 0),
        'desc_len': len(desc),
        'assess_len': len(assess),
        'kp_count': len(kp),
        'tv_len': len(tv),
        'centrality': round(node.get('centrality', 0) * 100, 1),
        'has_teaching_voice': bool(tv),
        'has_real_examples': bool((node.get('real_examples') or '').strip()),
        'has_common_mistakes': bool((node.get('common_mistakes') or '').strip()),
        'has_teaching_activity': bool((node.get('teaching_activity') or '').strip()),
        'has_src_page': bool(node.get('src_page')),
        'issues': issues,
        'quality': quality,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subject', help='只审查指定学科 (如 math/chinese)')
    parser.add_argument('--json', help='输出 JSON 报告到指定文件')
    parser.add_argument('--top', type=int, default=30, help='输出缺字段最多的前 N 个概念')
    args = parser.parse_args()

    if not DATA.exists():
        print(f'❌ 数据文件不存在: {DATA}')
        return

    with open(DATA) as f:
        data = json.load(f)

    nodes = data['nodes']
    if args.subject:
        nodes = [n for n in nodes if n.get('subject') == args.subject]
        print(f'🔍 只审查学科: {args.subject} ({len(nodes)} 概念)')
    else:
        print(f'🔍 审查全部 {len(nodes)} 概念')

    # 跑审查
    reports = [audit_node(n) for n in nodes]
    reports.sort(key=lambda r: r['score'])  # 分数最低的排前面 (最缺)

    # 总体统计
    total = len(reports)
    perfect = sum(1 for r in reports if r['score'] == 100 and not r['quality'])
    good = sum(1 for r in reports if 80 <= r['score'] < 100 and len(r['quality']) <= 2)
    need_fix = sum(1 for r in reports if r['score'] < 80 or len(r['quality']) > 2)

    # 各字段覆盖率
    coverage = {}
    for field in CONTENT_TRIPLE + TEACHING_TRIPLE + CURRICULUM:
        if field in CONTENT_TRIPLE or field in CURRICULUM:
            cnt = sum(1 for r in reports if not any(field in i for i in r['issues']))
        else:  # TEACHING_TRIPLE
            key = f'has_{field}'
            cnt = sum(1 for r in reports if r.get(key, False))
        coverage[field] = round(cnt / total * 100, 1) if total else 0

    # 按学科统计
    by_subject = defaultdict(lambda: {'total': 0, 'avg_score': 0, 'perfect': 0, 'need_fix': 0})
    for r in reports:
        s = r['subject']
        by_subject[s]['total'] += 1
        by_subject[s]['avg_score'] += r['score']
        if r['score'] == 100 and not r['quality']:
            by_subject[s]['perfect'] += 1
        if r['score'] < 80 or len(r['quality']) > 2:
            by_subject[s]['need_fix'] += 1
    for s, d in by_subject.items():
        d['avg_score'] = round(d['avg_score'] / d['total'], 1) if d['total'] else 0
        d['perfect_pct'] = round(d['perfect'] / d['total'] * 100, 1) if d['total'] else 0

    # === 输出报告 ===
    print()
    print('=' * 60)
    print(f'📊 V3.6.10c 概念质量审查报告 (数据版本: {data.get("version", "?")})')
    print('=' * 60)
    print()
    print(f'总概念数: {total}')
    print(f'完美概念 (100 分 + 0 质量问题): {perfect} ({perfect/total*100:.1f}%)')
    print(f'良好 (80-99 分 + ≤2 质量):     {good} ({good/total*100:.1f}%)')
    print(f'需修复 (< 80 分 或 > 2 质量):  {need_fix} ({need_fix/total*100:.1f}%)')
    print()
    print('字段覆盖率 (有/全部):')
    for f, pct in coverage.items():
        bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
        label = f.ljust(20)
        print(f'  {label} {bar} {pct}%')
    print()
    print('各学科完整度:')
    sorted_subj = sorted(by_subject.items(), key=lambda x: x[1]['avg_score'])
    for s, d in sorted_subj:
        bar = '█' * int(d['perfect_pct'] / 5) + '░' * (20 - int(d['perfect_pct'] / 5))
        print(f'  {s:18s} 概念 {d["total"]:3d}  完美 {d["perfect"]:3d} ({d["perfect_pct"]:5.1f}%)  平均分 {d["avg_score"]:5.1f}  {bar}')
    print()
    print(f'📉 缺字段最多的 Top {args.top} 概念 (按 score 升序):')
    print('-' * 60)
    print(f'{"ID":<20s} {"标题":<14s} {"年级":<5s} {"分":<3s} {"缺字段":<40s}')
    print('-' * 60)
    for r in reports[:args.top]:
        miss = ', '.join(r['issues'][:3])
        if len(r['issues']) > 3:
            miss += f' (+{len(r["issues"])-3})'
        if r['quality']:
            miss += f' [质:{len(r["quality"])}]'
        title = r['title'][:12]
        print(f'{r["id"]:<20s} {title:<14s} {r["grade"]:<5s} {r["score"]:<3d} {miss:<40s}')
    print()

    # JSON 报告
    if args.json:
        out = {
            'version': data.get('version', '?'),
            'total': total,
            'perfect': perfect,
            'good': good,
            'need_fix': need_fix,
            'coverage': coverage,
            'by_subject': dict(by_subject),
            'reports': reports,
        }
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f'📁 JSON 报告已写到: {args.json}')


if __name__ == '__main__':
    main()
