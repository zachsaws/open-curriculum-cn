#!/usr/bin/env python3
"""
V4.1.2 视频自动挑选脚本 (稳定版)
输入: docs/v412_video_picks.csv (200 概念)
输出: web/data/videos.json (200 视频)

策略:
1. 用 B 站 API 端点 api.bilibili.com/x/web-interface/search/all/v2 (无需过 anti-bot)
2. 学科化 query (历史/语文/音体美/抽象数学分别不同 query)
3. 评分: 关键词命中 + tag 命中 + 播放数 log + 时长适中 + 排除全集
4. 兜底: 任何情况都接受 #1 结果 (标 fallback)
"""
import json
import csv
import re
import time
import sys
import math
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent.parent
CSV_PATH = ROOT / 'docs' / 'v412_video_picks.csv'
OUT_PATH = ROOT / 'web' / 'data' / 'videos.json'

# 学科中文
SUBJECT_CN = {
    'math': '数学', 'chinese': '语文', 'english': '英语',
    'physics': '物理', 'chemistry': '化学', 'biology': '生物',
    'history': '历史', 'geography': '地理', 'morality_law': '道德与法治',
    'science': '科学', 'info_tech': '信息科技', 'pe_health': '体育',
    'art': '艺术', 'labor': '劳动', 'integrated': '综合',
}

# 学段标签
GRADE_CN = {
    1: '小学一年级', 2: '小学二年级', 3: '小学三年级', 4: '小学四年级',
    5: '小学五年级', 6: '小学六年级', 7: '初一', 8: '初二', 9: '初三',
}

# 黑名单关键词 (非教学内容)
BLACKLIST = [
    '游戏', '动画', '鬼畜', '舞蹈', 'vlog', '搞笑', '娱乐',
    '配音', '短剧', '明星', '美食', '旅行', '手书', 'MAD', 'AMV', 'MMD',
    '综艺', '颜值', '恋爱', '吃货', '手办', '爆笑', '段子', '脱口秀',
    '探店', '主播', '影评', '剧评', '二创', '伪音', '幻音', '重返未来',
    '颜值', 'cosplay', '手游', '吃鸡', '王者', '原神', '新一', '后宫',
    '宅舞', 'JK', '洛丽塔', '韩剧', '日剧', '美剧', '电影解说', '解说电影',
    '直播', '开箱', '测评', '整蛊', '解说', '体育赛事', 'NBA', '足球比赛',
    '娱乐圈', '八卦', '塌房', '吸毒', '出轨', '离婚',
    # 假/半教学 (无意义)
    '一口气看完', '全集', '合集', '一口气', '肝完', '魔鬼', '鬼畜',
    '整活', '小剧场', '情景剧', '心理测试', '人格分析',
]

# 白名单关键词 (教学内容)
WHITELIST = [
    '教学', '讲解', '教程', '网课', '课堂', '课程', '老师', '公开课',
    '示范', '讲', '复习', '专题', '训练', '学习', '练习', '思维',
    '导学', '同步', '人教', '北师', '苏教', '沪教', '部编',
    '中考', '高考', '期末', '期中', '真题', '模拟', '一轮', '二轮',
    '冲刺', '考', '试题', '考点', '解析', '详解', '精讲', '预习',
    '概念', '公式', '定理', '原理', '方法', '技巧', '口诀', '总结',
    '必考', '高频', '重点', '难点', '易错', '提升', '基础', '入门',
    '同步', '上册', '下册', '全一册',
]

# 高质量 UP 主 (教学口碑好)
GOOD_UPS = [
    '一数', '叫我CC呀', '碳老师', '杨教头', '数学', '物理', '化学', '生物',
    '科学', '一点老师', '国家中小学', '智慧教育', '人民教育', '教育',
    '学而思', '高途', '作业帮', '猿辅导', '新东方', '有道', '诸葛',
    '戴老师', '刘老师', '张老师', '王老师', '李老师', '宋老师', '陈老师',
    '雪球', '马老师', '老王', '小杨', '讲', '教研室', '教研',
]


def parse_duration(s):
    """'1:23' / '1:23:45' / '32:34' → 秒"""
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


def fetch_bilibili_api(keyword, max_results=20):
    """用 B 站 API 端点, 返 video 块 [{bvid, title, author, duration, play, description, tag, arcurl}]"""
    url = f'https://api.bilibili.com/x/web-interface/search/all/v2?keyword={urllib.parse.quote(keyword)}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    })
    try:
        resp = urllib.request.urlopen(req, timeout=12)
        data = json.loads(resp.read().decode('utf-8', errors='ignore'))
    except Exception as e:
        return [], f'fetch failed: {e}'

    if data.get('code') != 0:
        return [], f'api code: {data.get("code")} {data.get("message")}'

    videos = []
    for r in data.get('data', {}).get('result', []):
        if r.get('result_type') != 'video':
            continue
        for v in r.get('data', []):
            title = re.sub(r'<[^>]+>', '', v.get('title', ''))
            desc = re.sub(r'<[^>]+>', '', v.get('description', '') or '')
            tag = v.get('tag', '') or ''
            play = int(v.get('play', 0) or 0)
            dur = parse_duration(v.get('duration', ''))
            bvid = v.get('bvid', '')
            if not bvid or not title:
                continue
            videos.append({
                'bvid': bvid,
                'url': f'https://www.bilibili.com/video/{bvid}/',
                'title': title.strip()[:120],
                'author': v.get('author', '').strip()[:30],
                'duration_str': v.get('duration', ''),
                'duration_sec': dur,
                'play': play,
                'description': desc.strip()[:300],
                'tag': tag,
                'typename': v.get('typename', ''),
            })
            if len(videos) >= max_results:
                break
        if len(videos) >= max_results:
            break
    return videos, None


def extract_keywords(title):
    """从概念名提取核心关键词 — 整个 title + 2字/3字滑动窗"""
    skip = {
        '年级', '学科', '主题', '常见', '个人', '简单', '认识', '了解',
        '学会', '掌握', '理解', '基本', '一般', '通常', '主要', '重要',
        '什么', '怎么', '如何', '为什么', '一个', '一种',
    }
    # 去掉数字 + 标点
    clean = re.sub(r'[0-9一二三四五六七八九十]+', '', title)
    clean = re.sub(r'[^\w\u4e00-\u9fff]', '', clean)
    if not clean or clean in skip:
        return []
    # 整个 title 作为 1 个 keyword
    kws = [clean]
    # 加 2-3 字滑动窗口
    for n in (2, 3):
        for i in range(len(clean) - n + 1):
            sub = clean[i:i + n]
            if sub not in skip and sub not in kws:
                kws.append(sub)
    # 过滤: 至少 2 字符
    return [k for k in kws if len(k) >= 2]


def make_queries(concept):
    """根据学科生成多个搜索 query, 按命中率优先级"""
    title = concept['title']
    subject = concept['subject']
    grade = concept['grade']
    grade_cn = GRADE_CN.get(grade, f'{grade}年级')

    queries = []

    # 基础: 概念 + 教学
    queries.append(f'{title} 教学')
    queries.append(f'{title} 讲解')
    queries.append(f'{title} {GRADE_CN.get(grade, "")}')

    # 学科化 fallback
    if subject == 'history':
        # 朝代 + 讲解, 抽象事件 + 由来
        queries.append(f'{title} 历史 故事')
        queries.append(f'{title} 朝代 讲解')
        queries.append(f'{title} 由来')
    elif subject == 'chinese':
        # 语文抽象: 加学段 + 学科
        queries.append(f'{grade_cn} 语文 {title}')
        queries.append(f'{title} 课文 朗读')
        queries.append(f'{title} 古诗 赏析')
        queries.append(f'{title} 阅读 写作')
    elif subject == 'english':
        queries.append(f'{title} 英文 单词')
        queries.append(f'{title} 英语 语法')
    elif subject == 'physics':
        queries.append(f'{title} 物理 公式')
        queries.append(f'{title} 物理 概念')
    elif subject == 'chemistry':
        queries.append(f'{title} 化学 反应')
        queries.append(f'{title} 化学 实验')
    elif subject == 'biology':
        queries.append(f'{title} 生物 知识')
        queries.append(f'{title} 生物 科普')
    elif subject == 'geography':
        queries.append(f'{title} 地理 知识')
    elif subject == 'morality_law':
        queries.append(f'{title} 道德 法治')
    elif subject == 'info_tech':
        queries.append(f'{title} 信息 技术')
    elif subject == 'art':
        queries.append(f'{title} 美术 教学')
        queries.append(f'{title} 音乐 教学')
    elif subject == 'pe_health':
        queries.append(f'{title} 体育 运动')
    elif subject == 'labor':
        queries.append(f'{title} 劳动 课')
    elif subject == 'science':
        queries.append(f'{title} 科学 课')

    # 通用兜底
    queries.append(f'{title} 公开课')
    queries.append(f'{title} 入门')

    # 去重保留顺序
    seen = set()
    uniq = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq


def score_video(v, concept):
    """评分: 返回 (score, matched_keywords, is_relevant)"""
    title = v['title']
    author = v['author']
    tag = v.get('tag', '')
    typename = v.get('typename', '')
    desc = v.get('description', '')
    play = v['play']
    dur = v.get('duration_sec') or 0

    # 关键词
    keywords = extract_keywords(concept['title'])
    matched = [k for k in keywords if k in title or k in tag or k in desc]
    matched_count = len(matched)

    score = 0
    is_relevant = False

    # 1) 关键词命中: 必须 (核心 - 否则标记不相关)
    if matched_count > 0:
        score += matched_count * 40
        is_relevant = True
    else:
        # 关键词没命中: 大幅减分
        score -= 100
        # 但完全没关键词的概念 (如 "诗歌" 整体搜) 仍允许
        if len(keywords) == 0:
            score += 30  # 概念名全是单字, 用播放数/白名单补

    # 2) 白名单 (title/tag/typename 里)
    wl_hits = 0
    for kw in WHITELIST:
        if kw in title or kw in tag or kw in typename:
            wl_hits += 1
    score += min(40, wl_hits * 8)

    # 3) 黑名单
    bl_hits = 0
    for kw in BLACKLIST:
        if kw in title or kw in author:
            bl_hits += 1
            score -= 80
    if bl_hits > 0:
        is_relevant = False  # 黑名单命中: 强制不相关

    # 4) 播放数 (log)
    if play > 1000:
        score += min(40, int(math.log10(play) * 5))

    # 5) 时长: 3-25 分钟最佳
    if 180 <= dur <= 1500:
        score += 25
    elif 60 <= dur < 180:
        score += 12
    elif dur > 1500 and dur <= 3000:
        score += 8  # 30-50 分钟也接受 (课堂实录)
    elif dur > 3000:
        score -= 30  # 1 小时+ 太长

    # 6) 高质量 UP 主
    for up in GOOD_UPS:
        if up in author:
            score += 25
            break

    # 7) 标题短一些 (清爽)
    if 5 <= len(title) <= 35:
        score += 8

    return score, matched, is_relevant


def pick_best_video(results, concept):
    """从候选里选最合适的:
    - 相关视频按评分排序
    - 兜底: 没相关视频就用 #1 (标 fallback)
    """
    if not results:
        return None, 'no_results'

    # 评分
    scored = []
    for v in results:
        s, matched, relevant = score_video(v, concept)
        scored.append((s, matched, relevant, v))

    # 第一遍: 只看 relevant=True
    relevant_scored = [x for x in scored if x[2]]
    if relevant_scored:
        relevant_scored.sort(key=lambda x: x[0], reverse=True)
        return relevant_scored[0][3], 'ok'

    # 兜底: 没相关, 用评分最高的, 标 fallback
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][3], 'fallback'


def process_concept(concept):
    """为单个概念找视频"""
    queries = make_queries(concept)
    best = None
    best_status = None
    for q in queries:
        results, err = fetch_bilibili_api(q)
        if not results:
            continue
        pick, status = pick_best_video(results, concept)
        if not pick:
            continue
        # 选 best 时优先 ok 状态的
        if status == 'ok':
            if best is None or (best_status == 'fallback') or (pick['play'] > best.get('play', 0)):
                best = pick
                best_status = status
                # 找到一个 ok 的, 后面 ok 状态按 play 数比, fallback 直接跳过
        elif status == 'fallback' and best is None:
            best = pick
            best_status = status
    if not best:
        return None
    return {
        'concept_id': concept['concept_id'],
        'title': best['title'],
        'url': best['url'],
        'platform': 'bilibili',
        'duration_sec': best['duration_sec'],
        'language': 'zh-CN',
        'publisher': best['author'],
        'is_free': True,
        'rating': None,
        'notes': f"{SUBJECT_CN.get(concept['subject'], concept['subject'])} {GRADE_CN.get(concept['grade'], concept['grade'])} · 难 {concept['difficulty']} · 播放 {best['play']}{' [fallback]' if best_status == 'fallback' else ''}",
    }


def read_picks():
    picks = []
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            g_raw = row.get('grade', '') or ''
            grade = None
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


def main():
    picks = read_picks()
    print(f'读 {len(picks)} 概念')

    existing = []
    if OUT_PATH.exists():
        try:
            existing = json.loads(OUT_PATH.read_text()).get('videos', [])
            print(f'现有 {len(existing)} 视频')
        except Exception:
            existing = []
    existing_concepts = {v['concept_id'] for v in existing}
    todo = [p for p in picks if p['concept_id'] not in existing_concepts]
    print(f'待挑 {len(todo)} 概念')

    if not todo:
        print('全部已选, 退出')
        return

    results = list(existing)
    failed = []
    fallback_count = 0

    for i, concept in enumerate(todo):
        print(f'[{i+1}/{len(todo)}] {concept["concept_id"]} {concept["title"][:25]}', end=' ... ', flush=True)
        v = process_concept(concept)
        if v:
            is_fb = '[fallback]' in v.get('notes', '')
            tag = '🆘' if is_fb else '✓'
            print(f'{tag} {v["title"][:30]} | {v["publisher"][:10]} {v["duration_sec"]}s')
            if is_fb:
                fallback_count += 1
            results.append(v)
        else:
            print('✗ no result')
            failed.append(concept)
        # 每 20 个写盘
        if (len(results) - len(existing)) % 20 == 0 and results:
            save(results, len(existing), len(results) - len(existing), len(failed), fallback_count)
        time.sleep(0.4)

    save(results, len(existing), len(results) - len(existing), len(failed), fallback_count)
    print(f'\n=== 完成 ===')
    print(f'共 {len(results)} 视频 (现有 {len(existing)} + 新增 {len(results) - len(existing)})')
    print(f'fallback {fallback_count} 个, 失败 {len(failed)} 个')
    if failed:
        print(f'失败列表 ({len(failed)}):')
        for c in failed[:30]:
            print(f'  - {c["concept_id"]} {c["title"]}')


def save(results, existing_count, new_count, failed_count, fallback_count):
    out = {
        'version': 'v4.1.2',
        'note': f'自动挑选: 现有 {existing_count} + 新增 {new_count} (含 {fallback_count} fallback), 失败 {failed_count}',
        'videos': results,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f'  💾 写盘: {len(results)} 视频')


if __name__ == '__main__':
    main()
