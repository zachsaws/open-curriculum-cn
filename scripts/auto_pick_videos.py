#!/usr/bin/env python3
"""
V4.1.2 视频自动挑选脚本 (wbi 签名版)
- 用 bilibili-api-python 库 (内置 wbi 签名, 绕过 412)
- fallback: Playwright 慢通道
- 学科化 query
- 评分: 关键词命中 + 白名单 + 黑名单 + 播放数 + 时长
"""
import json
import csv
import re
import time
import math
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CSV_PATH = ROOT / 'docs' / 'v412_video_picks.csv'
OUT_PATH = ROOT / 'web' / 'data' / 'videos.json'

SUBJECT_CN = {'math': '数学', 'chinese': '语文', 'english': '英语', 'physics': '物理', 'chemistry': '化学',
              'biology': '生物', 'history': '历史', 'geography': '地理', 'morality_law': '道德与法治',
              'science': '科学', 'info_tech': '信息科技', 'pe_health': '体育', 'art': '艺术', 'labor': '劳动', 'integrated': '综合'}
GRADE_CN = {1: '小学一年级', 2: '小学二年级', 3: '小学三年级', 4: '小学四年级',
            5: '小学五年级', 6: '小学六年级', 7: '初一', 8: '初二', 9: '初三'}

BLACKLIST = ['游戏', '动画', '鬼畜', '舞蹈', 'vlog', '搞笑', '娱乐', '配音', '短剧', '明星', '美食', '旅行',
             '手书', 'MAD', 'AMV', 'MMD', '综艺', '颜值', '恋爱', '吃货', '手办', '爆笑', '段子', '脱口秀',
             '探店', '影评', '二创', '伪音', '幻音', 'cosplay', '手游', '吃鸡', '王者', '原神', '宅舞',
             'JK', '洛丽塔', '韩剧', '电影解说', '解说电影', '开箱', '测评', '整蛊', 'NBA', '体育赛事',
             '娱乐圈', '八卦', '塌房', '出轨', '离婚', '一口气看完', '全集', '合集', '一口气', '肝完',
             '鬼畜', '整活', '小剧场', '情景剧', '无生试讲', '穿搭', '时尚', 'LOLITA', '男伪', '伪男',
             '穿搭底层', '穿衣量感', '护肤', '美妆', '化妆', '美容', 'adobe', 'Adobe', 'PS教程', 'PR教程',
             '吉他', '钢琴', '尤克里里', '贝斯', '架子鼓', '韩星', '韩团', '猫咪', '养猫', '狗狗',
             '动漫解说', 'MAD', '鬼畜', '日剧', '美剧', '英剧', '颜值', '高甜', '撩人', '御姐',
             '萝莉', '禁欲', '风尘', '荷尔蒙', '欲望', '少妇', '艳遇', '出轨', '偷情', '离婚',
             '天呐', '竟是这样', '竟然是', '震惊', '小伙', '妹子', '美女', '帅哥', '小姐姐',
             '日落日出', '街景', '风景', '航拍', '无人机', '极限运动', '跑酷', '滑板', '冲浪',
             'VLOG', '旅行', '记vlog', '日常vlog', 'vlog日常', '开箱', '拆箱', '开箱视频',
             '试讲', '教师资格证', '教师招聘', '考编', '教招', '教资', '模拟授课', '面试试讲',
             '脱单', '撩妹', '撩汉', '把妹', '单身', '恋爱脑', '撒狗粮', '虐狗', '红娘', '月老',
             '终末地', '明日方舟', '原神', '星穹铁道', '鸣潮', '三角洲', 'CSGO', '瓦罗兰特', '无畏契约',
             '直播间', '主播', '带货', '打赏', 'PK', '比心', '送礼', '直播秀', '直播切片', '直播回放',
             '成人', 'vlog', 'VLOG', '街拍', '走秀', '走光', '模特', '内衣', '情趣', '色情', '低俗',
             '擦边', '性暗示', '诱惑', '撒娇', '萌妹', '正太', '御姐', '小奶狗', '小狼狗', '大叔', '少妇',
             '金条', '金钞', '金币', '金元宝', 'K金', '足金', '千足金', '万足金', '彩金', '铂金', '钯金',
             '老凤祥', '周大福', '周生生', '六福珠宝', '谢瑞麟', '周大生', '老庙黄金', '潮宏基', '明牌珠宝',
             '雅思', '托福', 'GRE', 'GMAT', '考研', '考公', '考博', '留学', '移民', '海归', '海淘', '代购',
             '理财', '基金', '股票', '期货', '外汇', '钻石', '玉石', '翡翠', '珍珠', '水晶', '玛瑙', '宝石',
             '祛斑', '祛痘', '防晒', '美白', '瘦身', '减肥', '健身教练', '私教', '美甲', '美瞳', '医美']

WHITELIST = ['教学', '讲解', '教程', '网课', '课堂', '课程', '老师', '公开课', '示范', '讲', '复习', '专题',
             '训练', '学习', '练习', '思维', '导学', '同步', '人教', '北师', '苏教', '部编', '中考', '高考',
             '期末', '期中', '真题', '模拟', '一轮', '二轮', '冲刺', '考', '试题', '考点', '解析', '详解',
             '精讲', '预习', '概念', '公式', '定理', '原理', '方法', '技巧', '口诀', '总结', '必考', '高频',
             '重点', '难点', '易错', '提升', '基础', '入门', '上册', '下册', '全一册']

GOOD_UPS = ['一数', '叫我CC呀', '碳老师', '杨教头', '数学', '物理', '化学', '生物', '科学', '一点老师',
            '国家中小学', '智慧教育', '人民教育', '学而思', '高途', '作业帮', '猿辅导', '新东方', '有道',
            '教研室', '雪球', '马老师', '戴老师', '刘老师', '张老师', '王老师', '李老师', '诸葛', '小文老师',
            '乐乐课堂', '天天练', '阿乐', '亮亮', '高中生物', '高中数学CL', '高考', '中考', '田静', '徐磊']

# 全局缓存
_BILI_SEARCH = None


def get_bili():
    global _BILI_SEARCH
    if _BILI_SEARCH is None:
        from bilibili_api import search, sync as bili_sync
        _BILI_SEARCH = (search, bili_sync)
    return _BILI_SEARCH


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


def fetch_bilibili_wbi(keyword, max_results=20):
    """用 bilibili-api-python 库 (wbi 签名), 返 [{bvid, title, author, duration, play, ...}]"""
    search, bili_sync = get_bili()
    from bilibili_api.search import SearchObjectType
    try:
        r = bili_sync(search.search_by_type(keyword, search_type=SearchObjectType.VIDEO))
    except Exception as e:
        return None, f'fetch failed: {e}'

    videos = []
    for v in r.get('result', []):
        # wbi 库 search_by_type 直接返 video 数组 (type='video', 没 result_type)
        if v.get('type') and v.get('type') != 'video':
            continue
        if v.get('result_type') and v.get('result_type') != 'video':
            continue
        title_raw = v.get('title', '')
        title = re.sub(r'<[^>]+>', '', title_raw).strip()[:120]
        bvid = v.get('bvid', '')
        author = v.get('author', '').strip()[:30]
        dur_str = v.get('duration', '')
        dur_sec = parse_duration(dur_str)
        play = int(v.get('play', 0) or 0)
        tag = v.get('tag', '') or ''
        desc = (v.get('description', '') or '')[:200]
        typename = v.get('typename', '')
        if not bvid or not title:
            continue
        videos.append({
            'bvid': bvid,
            'url': f'https://www.bilibili.com/video/{bvid}/',
            'title': title,
            'author': author,
            'duration_str': dur_str,
            'duration_sec': dur_sec,
            'play': play,
            'tag': tag,
            'description': desc,
            'typename': typename,
        })
        if len(videos) >= max_results:
            break
    return videos, None


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
    typename = v.get('typename', '')
    desc = v.get('description', '')
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


def make_queries(concept):
    title = concept['title']
    subject = concept['subject']
    grade = concept['grade']
    grade_cn = GRADE_CN.get(grade, f'{grade}年级')

    queries = [
        f'{title} 教学',
        f'{title} 讲解',
        f'{title} {grade_cn}',
    ]
    if subject == 'history':
        queries += [f'{title} 历史 故事', f'{title} 朝代 讲解', f'{title} 由来']
    elif subject == 'chinese':
        queries += [f'{grade_cn} 语文 {title}', f'{title} 课文 朗读', f'{title} 古诗 赏析', f'{title} 阅读 写作']
    elif subject == 'english':
        queries += [f'{title} 英文 单词', f'{title} 英语 语法']
    elif subject == 'physics':
        queries += [f'{title} 物理 公式', f'{title} 物理 概念']
    elif subject == 'chemistry':
        queries += [f'{title} 化学 反应', f'{title} 化学 实验']
    elif subject == 'biology':
        queries += [f'{title} 生物 知识', f'{title} 生物 科普']
    elif subject == 'geography':
        queries += [f'{title} 地理 知识']
    elif subject == 'morality_law':
        queries += [f'{title} 道德 法治']
    elif subject == 'info_tech':
        queries += [f'{title} 信息 技术']
    elif subject == 'art':
        queries += [f'{title} 美术 教学', f'{title} 音乐 教学']
    elif subject == 'pe_health':
        queries += [f'{title} 体育 运动']
    elif subject == 'labor':
        queries += [f'{title} 劳动 课']
    elif subject == 'science':
        queries += [f'{title} 科学 课', f'{title} 小学 科学', f'{title} 实验']

    queries += [f'{title} 公开课', f'{title} 入门']

    seen = set()
    uniq = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq


def pick_best_video(results, concept):
    if not results:
        return None, 'no_results'
    scored = []
    for v in results:
        s, matched, relevant = score_video(v, concept)
        scored.append((s, matched, relevant, v))
    relevant_scored = [x for x in scored if x[2]]
    if relevant_scored:
        relevant_scored.sort(key=lambda x: x[0], reverse=True)
        return relevant_scored[0][3], 'ok'
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][3], 'fallback'


def process_concept(concept, debug=False):
    queries = make_queries(concept)
    best = None
    best_status = None
    for q in queries:
        results, err = fetch_bilibili_wbi(q)
        if not results:
            if debug:
                print(f'\n    [debug: {q[:25]} -> err: {err}]', end=' ', flush=True)
            continue
        pick, status = pick_best_video(results, concept)
        if not pick:
            continue
        if status == 'ok':
            if best is None or (best_status == 'fallback') or (pick['play'] > best.get('play', 0)):
                best = pick
                best_status = status
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
        v = process_concept(concept, debug=(i < 3))
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
        if (len(results) - len(existing)) % 10 == 0 and results:
            save(results, len(existing), len(results) - len(existing), len(failed), fallback_count)
        time.sleep(1.5)  # wbi 限速, 慢一点

    save(results, len(existing), len(results) - len(existing), len(failed), fallback_count)
    print(f'\n=== 完成 ===')
    print(f'共 {len(results)} 视频, 新增 {len(results) - len(existing)}')
    print(f'fallback {fallback_count}, 失败 {len(failed)}')
    if failed:
        print(f'失败列表 (前 30):')
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
