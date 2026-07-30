#!/usr/bin/env python3
"""
V4.1.2 phase 3.3: cron self 续跑脚本
- 每次跑前先 test 1 个 query 测速
- 限速时返 0, 立即退
- 跑通时跑完整 batch
- 目标: 累计到 500+ 视频
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from auto_pick_videos import (
    fetch_bilibili_wbi, process_concept, read_picks,
    save, SUBJECT_CN, GRADE_CN
)
from pathlib import Path

OUT_PATH = ROOT / 'web' / 'data' / 'videos.json'
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 500
MAX_PER_RUN = 30  # 每次最多 30 个, 避免单次跑太久

print(f'=== cron_pick_resume, target {TARGET} ===')

# 读现有
existing = json.loads(OUT_PATH.read_text())['videos']
have = {v['concept_id'] for v in existing}
print(f'当前: {len(existing)} 视频')

if len(existing) >= TARGET:
    print(f'已达标 ({len(existing)} >= {TARGET}), 退')
    sys.exit(0)

# 测速
print('测速...')
test_results, test_err = fetch_bilibili_wbi('勾股定理 教学')
if not test_results:
    print(f'限速中 (err: {test_err}), 退')
    sys.exit(0)
print(f'测速 OK, 返 {len(test_results)} 结果')

# 跑批
picks = read_picks()
todo = [p for p in picks if p['concept_id'] not in have]
print(f'待挑: {len(todo)} 概念')

results = list(existing)
new_count = 0
fail_count = 0
fallback_count = 0

for i, concept in enumerate(todo):
    if new_count >= MAX_PER_RUN:
        print(f'本轮 {MAX_PER_RUN} 个跑完, 退')
        break
    print(f'[{new_count+1}] {concept["concept_id"]} {concept["title"][:25]}', end=' ... ', flush=True)
    v = process_concept(concept)
    if v:
        is_fb = '[fallback]' in v.get('notes', '')
        tag = '🆘' if is_fb else '✓'
        print(f'{tag} {v["title"][:30]} | {v["publisher"][:10]} {v["duration_sec"]}s')
        if is_fb:
            fallback_count += 1
        results.append(v)
        new_count += 1
    else:
        print('✗ no result')
        fail_count += 1
    time.sleep(0.8)  # 比原版更慢, 避免快速触限速

# 写盘
save(results, len(existing), new_count, fail_count, fallback_count)
print(f'\n=== 本轮完成 ===')
print(f'总: {len(results)} 视频, 新增 {new_count}, 失败 {fail_count}, fallback {fallback_count}')
if len(results) >= TARGET:
    print(f'🎯 达标! ({len(results)} >= {TARGET})')
