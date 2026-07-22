"""
JSON schema 验证 — 检查 data/graph/all_v3.0.json (V3.0 数据全集)
"""
import json
import sys
from pathlib import Path
from collections import Counter

GRAPH_DIR = Path(__file__).parent.parent.parent / "data" / "graph"
ALL_PATH = GRAPH_DIR / "all_v3.0.json"

try:
    import jsonschema
except ImportError:
    print("❌ 缺 jsonschema, 装: pip install jsonschema")
    sys.exit(1)

with open(Path(__file__).parent.parent / "schema.json") as f:
    schema = json.load(f)

validator = jsonschema.Draft7Validator(schema)
errors_total = 0
ok_total = 0

# 主数据：all_v3.0.json (V3.0 全集)
with open(ALL_PATH) as f:
    all_data = json.load(f)
nodes = all_data["nodes"]
print(f"\n--- {ALL_PATH.name}: {len(nodes)} 概念 ---")
for n in nodes:
    errs = list(validator.iter_errors(n))
    if errs:
        errors_total += len(errs)
        print(f"  ❌ {n.get('id', '?')}: {errs[0].message}")
    else:
        ok_total += 1

# 也按学科分布展示
subj_counter = Counter(n.get("subject", "?") for n in nodes)
print("\n--- 学科分布 ---")
for s, c in sorted(subj_counter.items(), key=lambda x: -x[1]):
    print(f"  {s:14s}: {c}")
ids = {n["id"] for n in all_data["nodes"]}
edge_err = 0
for e in all_data["edges"]:
    if e.get("from") not in ids:
        print(f"  ❌ edge.from 不存在: {e.get('from')}")
        edge_err += 1
    if e.get("to") not in ids:
        print(f"  ❌ edge.to 不存在: {e.get('to')}")
        edge_err += 1
    if e.get("from") == e.get("to"):
        print(f"  ❌ 自环: {e.get('from')}")
        edge_err += 1

print(f"\n=== 验证结果 ===")
print(f"✅ 有效概念: {ok_total}")
print(f"❌ 无效概念: {errors_total}")
print(f"❌ 关系错误: {edge_err}")
if errors_total == 0 and edge_err == 0:
    print("🎉 全部通过")
    sys.exit(0)
else:
    sys.exit(1)
