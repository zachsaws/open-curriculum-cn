"""
V3.2.2: 给每个概念生成 pinyin (英文 fallback)
- EN 模式时, 概念卡片用 pinyin 显示 (因为还没真翻译)
- 写回 all_v3.2.json 的 title_pinyin 字段
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
IN = ROOT / "data" / "graph" / "all_v3.2.json"

try:
    from pypinyin import lazy_pinyin
except ImportError:
    print("缺 pypinyin, 装: uv pip install pypinyin")
    raise

def main():
    print(f"读 {IN}")
    with open(IN) as f:
        d = json.load(f)
    nodes = d["nodes"]
    filled = 0
    for n in nodes:
        title = n.get("title", "")
        if not title:
            continue
        if n.get("title_pinyin"):
            continue
        try:
            # 用空格连接拼音 (而不是无分隔符)
            py = " ".join(lazy_pinyin(title))
            n["title_pinyin"] = py
            filled += 1
        except Exception:
            n["title_pinyin"] = title
            filled += 1
    print(f"填充 pinyin: {filled}/{len(nodes)}")
    # 抽样
    import random
    sample = random.sample(nodes, 5)
    for n in sample:
        print(f"  {n['title']} → {n['title_pinyin']}")
    with open(IN, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=None, separators=(',', ':'))
    print(f"写回 {IN}")

if __name__ == "__main__":
    main()
