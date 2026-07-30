#!/usr/bin/env python3
"""
V4.1.2 phase 3.2: Playwright 慢通道补缺口
- 用真实 Chrome 拿 B 站 search.bilibili.com
- 处理反爬
- 每次 1 个概念, 1 个 query, 慢但稳
"""
import json
import csv
import re
import time
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent.parent
CSV_PATH = ROOT / 'docs' / 'v412_video_picks.csv'
OUT_PATH = ROOT / 'web' / 'data' / 'videos.json'

# 黑名单
BLACKLIST = ['游戏', '动画', '鬼畜', '舞蹈', 'vlog', '搞笑', '娱乐', '配音', '短剧', '明星', '美食', '旅行',
             'MMD', '综艺', '颜值', '恋爱', '吃货', '手办', '爆笑', '段子', '脱口秀', '探店', '影评', '二创',
             '伪音', '幻音', 'cosplay', '手游', '吃鸡', '王者', '原神', '宅舞', 'JK', '韩剧', '电影解说',
             '开箱', '测评', '整蛊', '解说', 'NBA', '八卦', '塌房', '出轨', '离婚', '一口气看完', '全集',
             '合集', '一口气', '肝完', '鬼畜', '整活', '小剧场', '情景剧']

# 白名单
WHITELIST = ['教学', '讲解', '教程', '网课', '课堂', '课程', '老师', '公开课', '示范', '讲', '复习',
             '专题', '训练', '学习', '练习', '思维', '导学', '同步', '人教', '北师', '中考', '高考',
             '期末', '期中', '真题', '模拟', '一轮', '二轮', '冲刺', '考', '试题', '考点', '解析',
             '详解', '精讲', '预习', '概念', '公式', '定理', '原理', '方法', '技巧', '口诀', '总结',
             '必考', '高频', '重点', '难点', '易错', '提升', '基础', '入门', '上册', '下册', '全一册']

# 高质量 UP
GOOD_UPS = ['一数', '叫我CC呀', '碳老师', '杨教头', '一点老师', '国家中小学', '智慧教育', '人民教育',
            '学而思', '高途', '作业帮', '猿辅导', '新东方', '有道', '教研室']


def parse_duration(s):
    if not s:
        return None
    parts = s.split(':')
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return None
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return None


def extract_keywords(title):
    skip = {'年级', '学科', '主题', '常见', '个人', '简单', '认识', '了解', '学会', '掌握', '理解',
            '基本', '一般', '通常', '主要', '重要', '什么', '怎么', '如何', '为什么', '一个', '一种'}
    clean = re.sub(r'[0-9一二三四五六七八九十]+', '', title)
    clean = re.sub(r'[^\w\u4e00-\u9fff]', '', clean)
    if not clean or clean in skip:
        return []
    kws = [clean]
    for n in (2, 3):
        for i in range(len(clean) - n + 1):
            sub = clean[i:i + n]
            if sub not in skip and sub not in kws:
                kws.append(sub)
    return [k for k in kws if len(k) >= 2]


def score_video(v, concept):
    title = v['title']
    author = v['author']
    tag = v.get('tag', '')
    desc = v.get('description', '')
    typename = v.get('typename', '')
    play = v['play']
    dur = v.get('duration_sec') or 0

    keywords = extract_keywords(concept['title'])
    matched = [k for k in keywords if k in title or k in tag or k in desc]
    matched_count = len(matched)

    score = 0
    is_relevant = False
    if matched_count > 0:
        score += matched_count * 40
        is_relevant = True
    else:
        score -= 100
        if len(keywords) == 0:
            score += 30

    wl_hits = sum(1 for kw in WHITELIST if kw in title or kw in tag or kw in typename)
    score += min(40, wl_hits * 8)

    bl_hits = sum(1 for kw in BLACKLIST if kw in title or kw in author)
    if bl_hits > 0:
        score -= 80 * bl_hits
        is_relevant = False

    if play > 1000:
        import math
        score += min(40, int(math.log10(play) * 5))

    if 180 <= dur <= 1500:
        score += 25
    elif 60 <= dur < 180:
        score += 12
    elif 1500 < dur <= 3000:
        score += 8
    elif dur > 3000:
        score -= 30

    for up in GOOD_UPS:
        if up in author:
            score += 25
            break

    if 5 <= len(title) <= 35:
        score += 8

    return score, matched, is_relevant


def parse_bili_search_html(html):
    """从 B 站搜索页 HTML 提取 video 块"""
    results = []
    # 找 bvid 位置
    for m in re.finditer(r'bvid:"(BV[0-9A-Za-z]+)"', html):
        bvid = m.group(1)
        # 向前找最近的 {
        pos = m.start()
        brace_start = html.rfind('{', max(0, pos - 500), pos)
        if brace_start < 0:
            continue
        # 找匹配 }
        depth = 0
        brace_end = -1
        for i in range(brace_start, min(len(html), brace_start + 5000)):
            if html[i] == '{':
                depth += 1
            elif html[i] == '}':
                depth -= 1
                if depth == 0:
                    brace_end = i + 1
                    break
        if brace_end < 0:
            continue
        block = html[brace_start:brace_end]

        def extract(pattern, default=''):
            mm = re.search(pattern, block)
            return mm.group(1) if mm else default

        title = extract(r'title:"((?:[^"\\]|\\.)*)"')
        author = extract(r'author:"((?:[^"\\]|\\.)*)"')
        dur = extract(r'duration:"([^"]+)"')
        play_s = extract(r'play:(\d+)')
        desc = extract(r'description:"((?:[^"\\]|\\.)*)"')

        title = title.replace('\\u003Cem class=\\"keyword\\"\\u003E', '').replace('\\u003C/em\\u003E', '')
        title = re.sub(r'<[^>]+>', '', title)
        desc = desc.replace('\\u003Cem class=\\"keyword\\"\\u003E', '').replace('\\u003C/em\\u003E', '')
        desc = desc.replace('\\n', ' ').replace('\n', ' ')
        desc = re.sub(r'<[^>]+>', '', desc)

        if not bvid or not title:
            continue
        if bvid in [r['bvid'] for r in results]:
            continue

        results.append({
            'bvid': bvid,
            'url': f'https://www.bilibili.com/video/{bvid}/',
            'title': title.strip()[:120],
            'author': author.strip()[:30],
            'duration_str': dur,
            'duration_sec': parse_duration(dur),
            'play': int(play_s) if play_s else 0,
            'description': desc.strip()[:300],
        })
    return results


def pick_with_playwright(page, concept, queries):
    """用 Playwright 跑多个 query, 选 best"""
    best = None
    best_status = None
    for q in queries:
        url = f'https://search.bilibili.com/all?keyword={q}'
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=20000)
            time.sleep(2.5)  # 等 JS 渲染
            # 触发 anti-bot
            captcha = page.query_selector('.geetest_panel, .bili-captcha, [class*="captcha"]')
            if captcha and captcha.is_visible():
                print(f'    [CAPTCHA!] 跳过 query: {q}')
                continue
            html = page.content()
            results = parse_bili_search_html(html)
            if not results:
                continue
            # 评分
            scored = []
            for v in results:
                s, matched, relevant = score_video(v, concept)
                scored.append((s, matched, relevant, v))
            relevant_scored = [x for x in scored if x[2]]
            if relevant_scored:
                relevant_scored.sort(key=lambda x: x[0], reverse=True)
                pick = relevant_scored[0][3]
                if not best or best_status == 'fallback' or pick['play'] > best.get('play', 0):
                    best = pick
                    best_status = 'ok'
            elif not best:
                scored.sort(key=lambda x: x[0], reverse=True)
                best = scored[0][3]
                best_status = 'fallback'
        except Exception as e:
            print(f'    [err: {str(e)[:50]}]')
            continue
    return best, best_status


def make_queries(concept):
    title = concept['title']
    subject = concept['subject']
    grade = concept['grade']
    GRADE_CN = {1: '小学一年级', 2: '小学二年级', 3: '小学三年级', 4: '小学四年级', 5: '小学五年级', 6: '小学六年级',
                7: '初一', 8: '初二', 9: '初三'}
    grade_cn = GRADE_CN.get(grade, '')
    queries = [
        f'{title} 教学',
        f'{title} 讲解',
        f'{title} 课',
    ]
    if subject == 'science':
        queries += [f'{title} 科学', f'{title} 小学', f'{title} 实验']
    elif subject == 'labor':
        queries += [f'{title} 劳动', f'{title} 生活', f'{title} 教程']
    elif subject == 'pe_health':
        queries += [f'{title} 体育', f'{title} 运动', f'{title} 训练']
    elif subject == 'art':
        queries += [f'{title} 美术', f'{title} 绘画', f'{title} 教程']
    elif subject == 'info_tech':
        queries += [f'{title} 信息', f'{title} 编程', f'{title} 算法']
    elif subject == 'geography':
        queries += [f'{title} 地理', f'{title} 介绍']
    elif subject == 'chinese':
        queries += [f'{title} 语文', f'{title} 阅读', f'{title} 课文']
    return list(dict.fromkeys(queries))


def read_picks():
    picks = []
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            g_raw = row.get('grade', '') or ''
            if '-' in g_raw:
                parts = g_raw.split('-')
                try:
                    grade = (int(parts[0]) + int(parts[1])) // 2
                except ValueError:
                    grade = None
            else:
                try:
                    grade = int(g_raw)
                except ValueError:
                    grade = None
            picks.append({
                'concept_id': row['id'],
                'subject': row['subject'],
                'grade': grade,
                'title': row['title'],
                'difficulty': int(row['difficulty']) if row.get('difficulty') else 3,
            })
    return picks


SUBJECT_CN = {'math': '数学', 'chinese': '语文', 'english': '英语', 'physics': '物理', 'chemistry': '化学',
              'biology': '生物', 'history': '历史', 'geography': '地理', 'morality_law': '道德与法治',
              'science': '科学', 'info_tech': '信息科技', 'pe_health': '体育', 'art': '艺术', 'labor': '劳动'}
GRADE_CN_FULL = {1: '小学一年级', 2: '小学二年级', 3: '小学三年级', 4: '小学四年级', 5: '小学五年级', 6: '小学六年级',
                 7: '初一', 8: '初二', 9: '初三'}


def main():
    picks = read_picks()
    existing = json.loads(OUT_PATH.read_text())['videos']
    have = {v['concept_id'] for v in existing}
    todo = [p for p in picks if p['concept_id'] not in have]
    print(f'已有 {len(existing)} 视频, 待挑 {len(todo)}')

    if not todo:
        print('全部已选')
        return

    results = list(existing)
    failed = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            viewport={'width': 1280, 'height': 800},
        )
        page = ctx.new_page()

        for i, concept in enumerate(todo):
            print(f'[{i+1}/{len(todo)}] {concept["concept_id"]} {concept["title"][:25]}', end=' ... ', flush=True)
            queries = make_queries(concept)
            best, status = pick_with_playwright(page, concept, queries)
            if best:
                is_fb = status == 'fallback'
                tag = '🆘' if is_fb else '✓'
                print(f'{tag} {best["title"][:30]} | {best["author"][:10]} {best["duration_sec"]}s')
                results.append({
                    'concept_id': concept['concept_id'],
                    'title': best['title'],
                    'url': best['url'],
                    'platform': 'bilibili',
                    'duration_sec': best['duration_sec'],
                    'language': 'zh-CN',
                    'publisher': best['author'],
                    'is_free': True,
                    'rating': None,
                    'notes': f'{SUBJECT_CN.get(concept["subject"], concept["subject"])} {GRADE_CN_FULL.get(concept["grade"], concept["grade"])} · 难 {concept["difficulty"]} · 播放 {best["play"]}{" [fallback]" if is_fb else ""}',
                })
            else:
                print('✗ no result')
                failed.append(concept)
            # 每 5 个写盘
            if (i + 1) % 5 == 0:
                out = {'version': 'v4.1.2', 'note': f'Playwright 补 {len(results) - len(existing)} 个', 'videos': results}
                OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2))
            time.sleep(2)  # 慢点

        browser.close()

    out = {'version': 'v4.1.2', 'note': f'Playwright 补完, 失败 {len(failed)}', 'videos': results}
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f'\n=== 完成 ===')
    print(f'共 {len(results)} 视频, 新增 {len(results) - len(existing)}, 失败 {len(failed)}')


if __name__ == '__main__':
    main()
