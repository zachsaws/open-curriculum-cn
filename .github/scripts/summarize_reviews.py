"""
汇总 14 学科自评结果
"""
import json
import sys
from pathlib import Path

GRAPH_DIR = Path(__file__).parent.parent.parent / "data" / "graph"

print(f"{'学科':<14} {'概念':>4} {'完整率':>7} {'匹配率':>7} {'bloom':>6} {'错配':>5} {'VERDICT':>9}")
print("-" * 65)
for path in sorted(GRAPH_DIR.glob("*_review_r*.json")):
    if "r2" in path.name or "r3" in path.name:
        continue  # 跳过中间轮
    with open(path) as f:
        r = json.load(f)
    print(f"{r['subject']:<14} {r['total_concepts']:>4} {r['content_req_full_pct']:>6.1f}% {r['content_req_matched_pct']:>6.1f}% {r['bloom_coverage_pct']:>5.1f}% {r['cross_stage_mismatch']:>5} {r['verdict']:>9}")
