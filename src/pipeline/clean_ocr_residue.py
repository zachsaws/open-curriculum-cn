"""
V3.3.2 OCR 跑题清理.

清理 3 类问题:
1. 跑题 key_points: 检测公文腔/OCR 跑题模式 (道德与法治 115 节点全被"请解析...元素"污染)
2. 段落截断: key_points 不以标点结尾的 1714 节点补全
3. 跑题 academic_req: 235 节点 LLM 化替换

策略: 启发式 + 用 LLM 化 description 兜底
"""
import json
import re
import os
import sys

ROOT = '/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn'
os.chdir(ROOT)

# 跑题模式 (正则)
RESIDUE_PATTERNS = [
    r'请解析',
    r'在\s*\S+\s*课[堂学]?[上中]',  # 在 X 课上
    r'理解\s*\S+\s*这一概念',
    r'独立完成相关题目',
    r'用自己的话解释',
    r'举出一个生活中的例子',
    r'通过本[\u4e00-\u9fa5]*',
    r'具体含义',
    r'请回答',
    r'是否掌握',
    r'是否理解',
    r'思考[:：]\s*$',
    r'包含.{0,30}元素',  # 道德与法治特有: "请解析这些命名中蕴含了...元素"
]
RESIDUE_RE = re.compile('|'.join(RESIDUE_PATTERNS))

# 句末标点
END_PUNCT = set('。！？!?.；;」』"')

def is_residue(s):
    if not s:
        return False
    return bool(RESIDUE_RE.search(s))

def ends_punct(s):
    if not s:
        return True
    s = s.rstrip()
    return s and s[-1] in END_PUNCT

def extract_bullets_from_desc(desc, n=3):
    """从 description 拆 3 个 bullet 关键词."""
    if not desc:
        return []
    # 优先用句号分割
    parts = re.split(r'[。!?！？]', desc)
    parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 4]
    # 排除纯标点 / 长度 < 5
    bullets = []
    for p in parts[:n]:
        # 截短到 25 字
        if len(p) > 25:
            p = p[:25] + '...'
        bullets.append(p)
    while len(bullets) < n:
        bullets.append(f'关键概念 {len(bullets)+1}')
    return bullets[:n]


def clean_node(node, stats):
    """清理单节点 key_points / academic_req, 返回修改后节点."""
    nid = node.get('id', '?')
    desc = node.get('description', '') or ''

    # 1. 清理 key_points
    kp = node.get('key_points', [])
    if isinstance(kp, str):
        kp = [kp]
    if not isinstance(kp, list):
        kp = []

    new_kp = []
    for k in kp:
        if is_residue(k):
            stats['kp_residue_drop'] += 1
            continue
        if ends_punct(k) and 5 <= len(k) <= 60:
            new_kp.append(k)
        else:
            # 截断 / 太长 / 太短 / 无标点
            if not ends_punct(k) and len(k) > 5:
                k_clean = k.rstrip() + '。'
                new_kp.append(k_clean)
                stats['kp_punct_added'] += 1
            elif len(k) <= 5:
                stats['kp_too_short_drop'] += 1
            else:
                new_kp.append(k)

    # 道德与法治 115 节点: 整段 kp 跑题 → 用 description 拆 3 个 bullet
    if not new_kp and node.get('subject') == 'morality_law':
        new_kp = extract_bullets_from_desc(desc, 3)
        stats['morality_law_rebuilt'] += 1

    # 兜底: 仍空 → 用 description 拆
    if not new_kp:
        new_kp = extract_bullets_from_desc(desc, 3)
        stats['kp_empty_fallback'] += 1

    # 强制 3-5 个
    if len(new_kp) < 3:
        new_kp += extract_bullets_from_desc(desc, 3)[len(new_kp):]
    new_kp = new_kp[:5]

    node['key_points'] = new_kp

    # 2. 清理 academic_req
    ar = node.get('academic_req') or ''
    if ar and is_residue(ar):
        # 用 description 替代
        node['academic_req'] = desc
        stats['ar_residue_replaced'] += 1
    elif ar and not ends_punct(ar):
        node['academic_req'] = ar.rstrip() + '。'
        stats['ar_punct_added'] += 1

    return node


def main():
    in_path = 'data/graph/all_v3.3.json'
    out_path = 'data/graph/all_v3.3_clean.json'
    print(f"读 {in_path}...")
    with open(in_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    nodes = data.get('nodes', [])
    print(f"Total: {len(nodes)} nodes")

    stats = {
        'kp_residue_drop': 0,
        'kp_punct_added': 0,
        'kp_too_short_drop': 0,
        'kp_empty_fallback': 0,
        'ar_residue_replaced': 0,
        'ar_punct_added': 0,
        'morality_law_rebuilt': 0,
    }

    cleaned = []
    for n in nodes:
        cleaned.append(clean_node(n, stats))

    data['nodes'] = cleaned

    print(f"\n=== 清理统计 ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # 验证跑题率
    residue_after = 0
    for n in cleaned:
        kp_text = ' '.join(n.get('key_points', []))
        ar = n.get('academic_req') or ''
        if is_residue(kp_text):
            residue_after += 1
        if ar and is_residue(ar):
            residue_after += 1
    print(f"\n清理后跑题节点: {residue_after} (期望 < 5%)")
    print(f"跑题率: {residue_after / len(cleaned) * 100:.1f}%")

    # 写
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    print(f"\n✓ 写 {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")

    # 同步 web
    web_path = 'web/data/graph.json'
    with open(web_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    sz = os.path.getsize(web_path)
    import gzip
    with open(web_path, 'rb') as f:
        gz = gzip.compress(f.read(), compresslevel=9)
    with open(web_path + '.gz', 'wb') as f:
        f.write(gz)
    print(f"✓ 写 {web_path} ({sz/1024:.1f} KB) + .gz ({len(gz)/1024:.1f} KB)")

    return stats, residue_after


if __name__ == '__main__':
    main()
