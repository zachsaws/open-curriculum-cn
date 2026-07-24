"""
Smoke test: 1 概念 from each of 5 学科, validate script.
"""
import json
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path('/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn')
os.chdir(ROOT)

sys.path.insert(0, str(ROOT / 'data/graph/_build_v35'))
from subjects_config import SUBJECTS

# 取每个学科的第 1 个概念
import build as build_mod

for subject in SUBJECTS.keys():
    cfg = SUBJECTS[subject]
    print(f'\n=== Smoke test: {subject} ===')
    data = json.load(open(cfg['input_path']))
    first = data[0]
    print(f'Test concept: {first["id"]} ({first["title"]})')
    text = build_mod.call_llm([first])
    print(f'LLM response length: {len(text)}')
    parsed = build_mod.parse_json(text)
    print(f'Parsed: {len(parsed)} items')
    if parsed:
        item = parsed[0]
        item = build_mod.repair_one(item)
        issues = build_mod.validate(item)
        print(f'After repair: {[(k, len(v)) for k, v in item.items() if k in ["real_examples", "common_mistakes", "teaching_activity"]]}')
        print(f'Issues: {issues if issues else "NONE"}')
        if not issues:
            for f in ['real_examples', 'common_mistakes', 'teaching_activity']:
                print(f'  {f}: {item[f][:80]}...')
    else:
        print(f'PARSE FAILED, raw text:')
        print(text[:500])
