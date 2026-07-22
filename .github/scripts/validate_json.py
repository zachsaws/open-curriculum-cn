"""
JSON schema 验证 — 检查 data/graph/ 所有 *_v0.7.json 概念
"""
import json
import sys
from pathlib import Path

GRAPH_DIR = Path(__file__).parent.parent.parent / "data" / "graph"

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

for path in sorted(GRAPH_DIR.glob("*_v0.7.json")):
    if path.name == "all_v0.7.json":
        continue
    with open(path) as f:
        data = json.load(f)
    nodes = data["nodes"] if "nodes" in data else data
    print(f"\n--- {path.name}: {len(nodes)} 概念 ---")
    for n in nodes:
        errs = list(validator.iter_errors(n))
        if errs:
            errors_total += len(errs)
            print(f"  ❌ {n.get('id', '?')}: {errs[0].message}")
        else:
            ok_total += 1

# 检查 all_v0.7.json 的 edges
with open(GRAPH_DIR / "all_v0.7.json") as f:
    all_data = json.load(f)
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
