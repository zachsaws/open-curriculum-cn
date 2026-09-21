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

# 首屏只保留构建球面、学科筛选与搜索所需字段。
# 详情在用户点开概念后才从 graph.json 按需合并，避免把整套课标文本塞进首屏。
LITE_FIELDS = [
    # 3D 球核心
    'id', 'subject', 'title', 'grade_start', 'grade_end', 'centrality',
    'difficulty', 'bloom', 'type', 'estimated_minutes', 'subdomain', 'domain',
]

# 边保留 (3D 球画线)
EDGE_FIELDS = ['id', 'from', 'to', 'rel', 'weight']


def main():
    full = json.load(open(FULL))
    print(f'原文件: {FULL.stat().st_size / 1024 / 1024:.2f} MB, {len(full["nodes"])} 节点, {len(full["edges"])} 边')

    lite = {
        'version': full.get('version', ''),
        'note': 'V4.1.5: 首屏球面与搜索字段；详情在点开概念后按需加载',
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
