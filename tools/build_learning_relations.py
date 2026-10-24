#!/usr/bin/env python3
"""Derive relation explanations without changing curriculum source data."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'web/data'


def build():
    full = json.loads((DATA / 'graph.json').read_text())
    lite_bytes = (DATA / 'graph_lite.json').read_bytes()
    lite = json.loads(lite_bytes)
    assert {e['id'] for e in full['edges']} == {e['id'] for e in lite['edges']}
    payload = {
        'version': 1,
        'graph_sha256': hashlib.sha256(lite_bytes).hexdigest(),
        'edges': [{k: e[k] for k in ('id', 'reason', 'rationale', 'source') if k in e}
                  for e in full['edges']],
    }
    return (json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n').encode()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target = DATA / 'learning_relations.json'
    expected = build()
    if args.check:
        if not target.exists() or target.read_bytes() != expected:
            raise SystemExit('learning_relations.json is stale; run tools/build_learning_relations.py')
        print('learning relation payload matches source data')
    else:
        target.write_bytes(expected)
        print(f'built {target.name}: {len(expected):,} bytes')
