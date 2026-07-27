#!/usr/bin/env python3
"""
V3.7 P1 — 生成 teaching_voice 独立字段 (老师口吻 3 句话讲明白)
之前 V3.6.9 在 UI 上复用 description 字段当作"教学话术" (挂羊头卖狗肉),
P1 让 teaching_voice 变成独立字段, 老师用得着, 不再空喊"这步怎么教".

目标: 1906 概念, 每个生成 30-60 字的教学话术 (含 1 个生活例子, 3 句话讲明白).

跑法: 14 学科串行, 1 个 bg task 1 个学科, 增量模式 (跳过已有).
"""
import json
import os
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SRC = ROOT / 'data' / 'graph' / 'all_v3.7.json'
DST = ROOT / 'data' / 'graph' / 'all_v3.7_p1.json'
SETTINGS = Path.home() / '.claude' / 'settings.json'

LLM_URL = 'https://api.minimaxi.com/anthropic/v1/messages'
LLM_MODEL = 'MiniMax-M3'
LLM_MAX_TOKENS = 400

# 长度阈值
TV_MIN, TV_MAX = 25, 80
FORBIDDEN = ['理解', '培养', '掌握', '运用', '含义', '定义']


def get_api_key():
    with open(SETTINGS) as f:
        s = json.load(f)
    return s.get('env', {}).get('ANTHROPIC_AUTH_TOKEN', '')


def call_llm(prompt, api_key, max_retries=3):
    req = urllib.request.Request(
        LLM_URL,
        data=json.dumps({
            'model': LLM_MODEL,
            'max_tokens': LLM_MAX_TOKENS,
            'messages': [{'role': 'user', 'content': prompt}],
        }).encode('utf-8'),
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        method='POST'
    )
    last_err = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
                return data['content'][0]['text']
        except urllib.error.HTTPError as e:
            last_err = f'HTTP {e.code}: {e.read()[:200].decode("utf-8","replace")}'
        except Exception as e:
            last_err = f'{type(e).__name__}: {e}'
        time.sleep(2 + attempt * 2)
    raise RuntimeError(f'LLM 失败 3 次: {last_err}')


def build_prompt(node):
    """教学话术 prompt: 老师口吻, 3 句话, 含 1 个生活例子."""
    title = node.get('title', '')
    grade = f"{node.get('grade_start', '?')}-{node.get('grade_end', '?')} 年级"
    subject = node.get('subject', '')
    description = (node.get('description') or '')[:300]
    key_points = node.get('key_points', [])

    prompt = f"""你是 K12 老师, 看完下面的概念, 写 1 段**教学话术**给其他老师参考.

# 概念信息
- 标题: {title}
- 年级: {grade}
- 学科: {subject}
- 概念描述: {description}
- 知识要点: {json.dumps(key_points, ensure_ascii=False)[:300]}

# 任务: 教学话术 (30-80 字, 3 句话讲明白)

写 1 段话, 老师**拿到就能照着讲**. 要求:
1. **3 句话**结构: 第 1 句开门见山告诉学生"这是什么"; 第 2 句用 1 个**生活例子**讲明白; 第 3 句告诉学生"现在能做什么"
2. **老师口吻** ("我们来看"/"想象一下"/"比如"/"记住"), 不要"理解/培养/掌握/运用/含义/定义"等空话
3. **30-80 字**, 不要超过 80 字 (短才好用)
4. 1 个**生活例子** (超市/家里/路上/游戏 场景), 不抽象
5. **不写**"理解/培养/掌握/运用/含义/定义"等空词
6. **不写**"今天我们学习..."这种开头废话
7. **不写**"通过本节课..."这种结尾废话

# 例子
概念: 「垃圾分类」小学 1-2 年级
教学话术: "我们来看,垃圾分 4 类——可回收、厨余、有害、其他。想象家里妈妈让你把菜叶和塑料袋扔进'厨余'桶,你就要说'塑料袋是其他垃圾,菜叶才扔厨余'。记住,电池一定要去有害垃圾桶,扔错会污染一平方米土壤 50 年。"

# 输出 (严格 JSON, 不要其他)

```json
{{
  "teaching_voice": "..."
}}
```"""
    return prompt


def parse_llm_output(text):
    text = text.strip()
    if '```' in text:
        parts = text.split('```')
        for p in parts:
            p = p.strip()
            if p.startswith('json'):
                p = p[4:].strip()
            if p.startswith('{') and p.endswith('}'):
                try:
                    return json.loads(p)
                except json.JSONDecodeError:
                    continue
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
    return None


def post_process(node, llm_result, log):
    REPLACE = {'理解': '看明白', '培养': '养成', '掌握': '会用', '运用': '用起来', '含义': '意思', '定义': '是啥'}
    out = {}

    tv = (llm_result.get('teaching_voice') or '').strip()
    if not tv:
        log.append(f'{node["id"]}: teaching_voice 为空')
    elif not (TV_MIN <= len(tv) <= TV_MAX):
        log.append(f'{node["id"]}: teaching_voice 长度 {len(tv)} 超出 {TV_MIN}-{TV_MAX}')
    for w, r in REPLACE.items():
        if w in tv:
            tv = tv.replace(w, r)
            log.append(f'{node["id"]}: teaching_voice 替换禁词 "{w}"')
    out['teaching_voice'] = tv
    return out


def need_update(node):
    if not node.get('teaching_voice'):
        return True, '缺 teaching_voice'
    if not (TV_MIN <= len(node.get('teaching_voice', '')) <= TV_MAX):
        return True, f'teaching_voice 长度 {len(node.get("teaching_voice", ""))} 超出 {TV_MIN}-{TV_MAX}'
    return False, 'OK'


def process_node(node, api_key, log, max_attempts=3):
    need, reason = need_update(node)
    if not need:
        return None
    log.append(f'>>> {node["id"]} ({node.get("title", "")[:20]}): {reason}')

    prompt = build_prompt(node)
    last_text = None
    for attempt in range(1, max_attempts + 1):
        try:
            text = call_llm(prompt, api_key)
            last_text = text
        except Exception as e:
            log.append(f'LLM 失败 (第{attempt}次) {node["id"]}: {e}')
            time.sleep(2)
            continue

        parsed = parse_llm_output(text)
        if not parsed:
            log.append(f'LLM 输出无法 parse (第{attempt}次) {node["id"]}: {text[:100]}')
            continue

        tv = parsed.get('teaching_voice', '')
        if not tv or len(tv) < TV_MIN:
            log.append(f'LLM 输出截断 (第{attempt}次) {node["id"]}: tv={len(tv)}字')
            continue

        out = post_process(node, parsed, log)
        if attempt > 1:
            log.append(f'  重试成功 (第{attempt}次) {node["id"]}')
        return out

    log.append(f'❌ 全部尝试失败 {node["id"]}, 跳过')
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subject', help='只跑指定学科')
    parser.add_argument('--ids', nargs='+', help='只跑指定 ID')
    parser.add_argument('--limit', type=int, help='最多跑 N 个 (测试用)')
    parser.add_argument('--out', default=str(DST), help='输出 JSON 文件')
    parser.add_argument('--reset', action='store_true', help='从 V3.7 重新开始')
    args = parser.parse_args()

    if args.reset and Path(args.out).exists():
        Path(args.out).unlink()
        print(f'🗑  重置: 删除 {args.out}')

    src_to_use = Path(args.out) if Path(args.out).exists() else SRC
    if src_to_use == Path(args.out):
        print(f'📂 增量: 从 {args.out} 读, 跳过已补完')
    else:
        print(f'📂 基础: 从 {SRC} 读')

    with open(src_to_use) as f:
        data = json.load(f)
    api_key = get_api_key()
    if not api_key:
        print('❌ 找不到 ANTHROPIC_AUTH_TOKEN')
        return

    nodes = data['nodes']
    if args.subject:
        nodes = [n for n in nodes if n.get('subject') == args.subject]
        print(f'🔍 只跑学科: {args.subject} ({len(nodes)} 概念)')
    if args.ids:
        nodes = [n for n in nodes if n.get('id') in args.ids]
        print(f'🔍 只跑指定 ID: {args.ids}')

    todo = [n for n in nodes if need_update(n)[0]]
    print(f'📋 总需补: {len(todo)}/{len(nodes)}')
    if args.limit:
        todo = todo[:args.limit]
        print(f'⚠️ 限制前 {args.limit} 个 (测试)')

    if not todo:
        print('✅ 全部已 OK')
        return

    log = []
    updated = 0
    start = time.time()

    for i, node in enumerate(todo):
        elapsed = time.time() - start
        rate = (i + 1) / max(elapsed, 0.1)
        eta = (len(todo) - i - 1) / max(rate, 0.001) / 60
        print(f'[{i+1}/{len(todo)}] {rate:.1f}/s, ETA {eta:.0f}min', flush=True)

        out = process_node(node, api_key, log)
        if out:
            node.update(out)
            updated += 1

    out_path = Path(args.out)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log_path = out_path.parent / (out_path.stem + '.log')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log))

    print()
    print(f'✅ 更新 {updated}/{len(todo)} 概念, 写到 {out_path}')
    print(f'📝 Log: {log_path}')
    print(f'⏱  总耗时: {(time.time()-start)/60:.1f}min')

    total = len(data['nodes'])
    has_tv = sum(1 for n in data['nodes'] if n.get('teaching_voice'))
    print(f'📊 teaching_voice: {has_tv}/{total} ({has_tv/total*100:.1f}%)')


if __name__ == '__main__':
    main()
