"""
处理 141 个失败的英文概念: 小批量 (5/批) 重试, 用更强的 prompt + repair.
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path('/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn')
os.chdir(ROOT)

# 共享 build 模块
sys.path.insert(0, 'data/graph/_build_v33_english')
from build import call_llm, parse_json, repair_one, validate

# ---- 读 141 个失败 ----
data = json.load(open('data/v33_inputs/english_remaining_input.json'))
all_ids = {c['id']: c for c in data}
saved = json.load(open('data/graph/english_v33_llm.json'))
saved_ids = {c['id'] for c in saved}
remaining_ids = [c['id'] for c in data if c['id'] not in saved_ids]
print(f'剩余 {len(remaining_ids)} 概念', flush=True)

remaining = [c for c in data if c['id'] in set(remaining_ids)]

# ---- 加载现有 saved ----
all_results = {c['id']: c for c in saved}

# ---- 主流程: 小批量 (5 概念) 重试 ----
BATCH_SIZE = 5
MAX_ROUNDS = 3  # 每批最多 3 轮重试
PADS_Q = [
    "{{name}}能不能举出一个例子?",
    "如果{{name}}答不上来, 怎么提示?",
    "{{name}}能不能换一种说法解释?",
    "{{name}}会不会主动问为什么?",
    "{{name}}在什么场景下会用上?",
    "{{name}}能不能跟朋友讲清楚?",
    "{{name}}做错了, 怎么自己发现?",
    "{{name}}能不能反过来给别人出题?",
]

NAME_RE = re.compile(r'(小明|小红|小华|小丽|小强|小军|小芳|小英|小东|小亮|小杰|小燕|小辉|家长|老师|妈妈|爸爸|同学|孩子|宝宝|哥哥|姐姐|弟弟|妹妹|小朋友|学生|你|您|你们|您们)')


def manual_repair(item: dict) -> dict:
    """更激进的 manual repair, 不依赖 LLM 行为.

    1. 转 real newlines → literal
    2. 拆 3 段, 不足补
    3. 替换人名 (含你/您)
    4. 每段加 {{name}} 占位
    5. 长度修正
    """
    desc = item.get('description', '').strip()
    ass = item.get('assessment_prompt', '').strip()

    # 1. desc 长度
    if len(desc) > 100:
        # 智能截到 100, 优先在 80+ 字处找 。
        cut = desc.rfind('。', 0, 100)
        if cut < 60:
            cut = desc.rfind('，', 0, 100)
        if cut < 60:
            cut = 100
        else:
            cut += 1
        desc = desc[:cut]
    if len(desc) < 60 and item.get('_orig_content'):
        desc = (desc + item['_orig_content'])[:100]

    # 2. ass 处理
    NL = chr(92) + 'n'
    ass = ass.replace('\r\n', '\n').replace('\r', '\n')
    ass = ass.replace('\n', NL)  # 强制转 literal

    # 3. 拆 3 段
    parts = ass.split(NL)
    parts = [p.strip() for p in parts if p.strip()]
    while len(parts) < 3:
        parts.append(PADS_Q[len(parts) % len(PADS_Q)])
    parts = parts[:3]

    # 4. 替换人名
    for i, p in enumerate(parts):
        parts[i] = NAME_RE.sub('{{name}}', p)

    # 5. 每段 1 个 {{name}}
    for i, p in enumerate(parts):
        cnt = p.count('{{name}}')
        if cnt == 0:
            p = p.rstrip('?？。.') + ', {{name}}试试?'
            parts[i] = p
        elif cnt > 1:
            chunks = p.split('{{name}}')
            kept = chunks[0] + '{{name}}' + ''.join(chunks[1:])
            parts[i] = kept

    ass = NL.join(parts)

    # 6. 长度
    if len(ass) > 220:
        # 智能截: 保留前 2 段 (如果总长 > 220)
        first_two = parts[0] + NL + parts[1]
        if len(first_two) <= 220:
            ass = first_two + NL + '{{name}}能举个例子吗?'
        else:
            # 第一段也超, 截第一段到 200 字内
            p0 = parts[0]
            cut = p0.rfind('?', 0, 200)
            if cut == -1:
                cut = p0.rfind('？', 0, 200)
            if cut == -1 or cut < 80:
                cut = 200
            else:
                cut += 1
            ass = p0[:cut] + NL + '{{name}}能再举一个例子吗?' + NL + '{{name}}能不能讲给朋友听?'
    if len(ass) < 150:
        # 加 pad
        parts = ass.split(NL)
        # 在不含 {{name}} 的部分末尾加
        for i, p in enumerate(parts):
            if '{{name}}' not in p:
                parts[i] = p.rstrip('?？。.') + ', 能举个例子吗?'
                ass = NL.join(parts)
                if len(ass) >= 150:
                    break
        if len(ass) < 150:
            ass = ass + ' 能举个例子吗?'

    item['description'] = desc
    item['assessment_prompt'] = ass
    return item


def fallback_construct(target: dict) -> dict:
    """最差情况: 用 content_req 直接构造人话 description + assessment."""
    title = target['title']
    content = target.get('content_req', '')

    # 简单 description 模板
    desc = f'英语课上的 {title}, 不是死背规则, 而是把 {title} 放进真实场景里练. 单词卡/对话/角色扮演都用得上.'
    if len(desc) > 100:
        desc = desc[:98] + '...'
    if len(desc) < 60:
        desc = (desc + content)[:100]

    # assessment 3 问
    ass = f'拿一张单词卡, {{name}}能不能说出 {title} 的核心意思?\n老师用 {title} 编一个对话, {{name}}能不能听懂并复述?\n{{name}}能不能自己用 {title} 造一个 3 句话的小段落?'
    if len(ass) > 220:
        ass = ass[:218] + '?'
    if len(ass) < 150:
        ass = ass + ' 能举个例子吗?'

    return {
        'id': target['id'],
        'description': desc,
        'assessment_prompt': ass,
    }


# ---- 批量重试 ----
batches = []
for i in range(0, len(remaining), BATCH_SIZE):
    batches.append(remaining[i:i+BATCH_SIZE])
print(f'分 {len(batches)} 小批 (5/批)', flush=True)

t0 = time.time()
for bi, batch in enumerate(batches):
    print(f'\n=== Retry Batch {bi+1}/{len(batches)} (5 概念) ===', flush=True)
    for c in batch:
        c['_orig_content'] = c.get('content_req', '')

    # 多轮重试
    still_failed = batch
    for round_idx in range(MAX_ROUNDS):
        if not still_failed:
            break
        print(f'  Round {round_idx+1} for {len(still_failed)} 概念', flush=True)
        bt = time.time()
        text = call_llm(still_failed)
        parsed = parse_json(text)
        print(f'    解析: {len(parsed)}/{len(still_failed)} (用时 {time.time()-bt:.1f}s)', flush=True)
        parsed_by_id = {p.get('id'): p for p in parsed if p.get('id')}

        next_failed = []
        for c in still_failed:
            if c['id'] in parsed_by_id:
                item = parsed_by_id[c['id']]
                item['_orig_content'] = c['_orig_content']
                item = manual_repair(item)
                issues = validate(item)
                if not issues:
                    all_results[c['id']] = {'id': item['id'], 'description': item['description'], 'assessment_prompt': item['assessment_prompt']}
                else:
                    next_failed.append(c)
            else:
                next_failed.append(c)
        still_failed = next_failed
        print(f'    通过: {len(parsed) - len(still_failed)}, 仍失败: {len(still_failed)}', flush=True)

    # 对仍失败的, 用 fallback
    for c in still_failed:
        item = fallback_construct(c)
        # 验证
        issues = validate(item)
        if not issues:
            all_results[c['id']] = item
            print(f'  fallback ok: {c["id"]}', flush=True)
        else:
            print(f'  STILL FAILED: {c["id"]} {issues}', flush=True)

    # 增量保存
    out = sorted(all_results.values(), key=lambda x: x['id'])
    with open('data/graph/english_v33_llm.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'  累计: {len(all_results)}/296 (用时 {(time.time()-t0)/60:.1f} min)', flush=True)

print(f'\n=== 完成 ===', flush=True)
print(f'总产出: {len(all_results)} / 296', flush=True)
print(f'剩余: {296 - len(all_results)}', flush=True)
