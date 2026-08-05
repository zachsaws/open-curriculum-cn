#!/usr/bin/env python3
"""生成 graph_lite.json (3D 球用, ~300KB) + graph_lite.json.gz
- 3D 球需要: id/subject/title/grade_start/grade_end/centrality/difficulty/bloom/type/estimated_minutes/subdomain/domain
- detail panel 需要 fetch 单节点 from full
"""
import json
import gzip
import shutil
from pathlib import Path

ROOT = Path('/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn')
FULL = ROOT / 'web/data/graph.json'
LITE = ROOT / 'web/data/graph_lite.json'
LITE_GZ = ROOT / 'web/data/graph_lite.json.gz'

# 3D 球 + detail panel 字段 (~4.5MB / 1.3MB gz, 比 full 7.8MB 快 6 倍)
# 含 3D 渲染 + detail 全部字段, 不分两步
LITE_FIELDS = [
    # 3D 球核心
    'id', 'subject', 'title', 'grade_start', 'grade_end', 'centrality',
    'difficulty', 'bloom', 'type', 'estimated_minutes', 'subdomain', 'domain',
    # detail panel 必要
    'content_req', 'academic_req', 'assessment_prompt',
    'key_points', 'examples', 'src_page',
    'teaching_voice', 'description', 'summary',
    # V3.3.4 教师用书级 (老师备课核心)
    'real_examples', 'common_mistakes', 'teaching_activity',
]

# 边保留 (3D 球画线)
EDGE_FIELDS = ['id', 'from', 'to', 'rel', 'weight']


def main():
    full = json.load(open(FULL))
    print(f'原文件: {FULL.stat().st_size / 1024 / 1024:.2f} MB, {len(full["nodes"])} 节点, {len(full["edges"])} 边')

    lite = {
        'version': full.get('version', ''),
        'note': 'V4.1.3: graph_lite, 3D 球 + detail panel 核心字段',
        'nodes': [
            {k: n.get(k) for k in LITE_FIELDS if k in n}
            for n in full['nodes']
        ],
        'edges': [
            {k: e.get(k) for k in EDGE_FIELDS if k in e}
            for e in full['edges']
        ],
    }
    LITE.write_text(json.dumps(lite, ensure_ascii=False, separators=(',', ':')))
    size = LITE.stat().st_size
    print(f'Lite JSON: {size / 1024:.1f} KB ({size / FULL.stat().st_size * 100:.1f}% of full)')

    # gz
    with open(LITE, 'rb') as f_in, gzip.open(LITE_GZ, 'wb', compresslevel=9) as f_out:
        shutil.copyfileobj(f_in, f_out)
    print(f'Lite gz: {LITE_GZ.stat().st_size / 1024:.1f} KB')


if __name__ == '__main__':
    main()
