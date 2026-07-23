"""
V3.3.1 PoC: 数学学科 337 概念的 LLM 内容化
- 目标: 验证 LLM 生成 description / assessment / reason / cluster summary 的质量
- 输入: data/graph/all_v3.2.json (math 节点)
- 输出: data/graph/math_v33.json (math 节点 + 4 个新/重写字段)

LLM 资源: mavis 自己的 LLM (sub-agent task tool)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
IN = ROOT / "data" / "graph" / "all_v3.2.json"
OUT = ROOT / "data" / "graph" / "math_v33.json"

def main():
    with open(IN) as f:
        d = json.load(f)
    math_nodes = [n for n in d["nodes"] if n["subject"] == "math"]
    print(f"Math 节点: {len(math_nodes)}")
    out = {
        "version": "v3.3.1",
        "subject": "math",
        "conceptCount": len(math_nodes),
        "concepts": [],  # 待 sub-agent 填充
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"骨架写入 {OUT}")
    # 写一份 concept 列表给 sub-agent 读取
    with open(ROOT / "data" / "graph" / "math_concepts_input.json", "w", encoding="utf-8") as f:
        json.dump(math_nodes, f, ensure_ascii=False, indent=2)
    print(f"输入写入 data/graph/math_concepts_input.json ({len(math_nodes)} 概念)")

if __name__ == "__main__":
    main()
