#!/usr/bin/env python3
"""
V3.7 P0 — 补 academic_req + key_points 完整度
- 1 次 LLM call 同时生成 2 字段 (省 token)
- 串行 1 概念 1 LLM call (避免 token plan 撞墙)
- 调 Mavis session 端点, 不通过 sub-agent (之前 V3.3.1 教训)

用法:
  python3 data/build/build_p0.py --subject math --limit 5   # 测试 5 概念
  python3 data/build/build_p0.py --subject math             # 跑 math 全部
  python3 data/build/build_p0.py --ids M_G1_NS_01           # 跑指定 1 概念
"""
import json
import os
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SRC = ROOT / 'data' / 'graph' / 'all_v3.3.json'
DST = ROOT / 'data' / 'graph' / 'all_v3.7.json'
SETTINGS = Path.home() / '.claude' / 'settings.json'

# LLM 配置
LLM_URL = 'https://api.minimaxi.com/anthropic/v1/messages'
LLM_MODEL = 'MiniMax-M3'
LLM_MAX_TOKENS = 800

# 长度阈值
ACADEMIC_REQ_MIN, ACADEMIC_REQ_MAX = 30, 150
KEY_POINTS_TARGET = 3
KEY_POINTS_MIN_LEN, KEY_POINTS_MAX_LEN = 5, 60

# 禁词 (V3.3.5 LLM 增强规范)
FORBIDDEN = ['理解', '培养', '掌握', '运用', '含义', '定义']


def get_api_key():
    with open(SETTINGS) as f:
        s = json.load(f)
    return s.get('env', {}).get('ANTHROPIC_AUTH_TOKEN', '')


def call_llm(prompt, api_key, max_retries=3):
    """调 Mavis session 端点, 1 次 LLM call. 返回 text 字段, 失败 raise."""
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
        time.sleep(2 + attempt * 2)  # backoff
    raise RuntimeError(f'LLM 失败 3 次: {last_err}')


def build_prompt(node):
    """构造 prompt, 让 LLM 补 academic_req + key_points."""
    title = node.get('title', '')
    grade = f"{node.get('grade_start', '?')}-{node.get('grade_end', '?')} 年级"
    subject = node.get('subject', '')
    type_ = node.get('type', 'CONCEPTUAL')
    difficulty = node.get('difficulty', 3)
    content_req = (node.get('content_req') or '')[:300]
    description = (node.get('description') or '')[:300]
    assessment = (node.get('assessment_prompt') or '')[:200]
    key_points = node.get('key_points', [])

    prompt = f"""你是 K12 课程内容编辑, 看完下面的概念信息, 帮我补 2 个字段.

# 概念信息
- 标题: {title}
- 年级: {grade}
- 学科: {subject}
- 类型: {type_}
- 难度: {difficulty}/5
- 课标内容要求: {content_req}
- 概念描述: {description}
- 评估场景: {assessment}
- 现有 key_points ({len(key_points)} 条): {json.dumps(key_points, ensure_ascii=False)[:200]}

# 你的任务

## 1. academic_req (学业要求, 30-150 字, 1 句话)

模仿 2022 课标原文"学业要求"段的语气, 写 1 句"学生在本概念学完后要会什么"的描述.
- 动词开头: "会..." / "能..." / "在...情境中能..."
- 写学生**能做什么** (用 4 类动词: 识别 / 描述 / 解释 / 应用)
- 不要重复 content_req
- 不要用"理解/培养/掌握/运用/含义/定义"等空话
- 1 句, 不要分点

## 2. key_points (知识要点, 3 条)

列出本概念**自身**最核心的 3 个要点 (如果现有 key_points 已有 X 条, 补到 3 条).
- 每条 5-60 字
- 是**本概念**的事实/结论, **不要抄 content_req 的句子** (content_req 是整个学段的目标, 不一定都是本概念本身)
- **不要重复**: 你生成的 3 条必须**完全不同**, 不能 3 条说同一个事
- **不要跟"通用身体姿势"混**: 体育/健康等课有很多通用前置 (如"正确坐立行"), 这些是**前置概念**的要点, 不是本概念的. 只写本概念**新增**的认知.
- 动词开头 ("能 X" / "是 X" / "包括 X")
- 3 条按"从具体到抽象"或"从易到难"排序
- 例如: "能识别 0-9 每个数字" / "知道 10 个一是 1 个十" / "能用位置写 100 以内的数"

# 输出 (严格 JSON, 不要其他文字)

```json
{{
  "academic_req": "...",
  "key_points": ["要点 1", "要点 2", "要点 3"]
}}
```"""
    return prompt


def parse_llm_output(text):
    """从 LLM 输出提取 JSON. 处理 ```json ... ``` 包裹 + 杂文本."""
    # 尝试直接 parse
    text = text.strip()
    # 找 ```json ... ``` 块
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
    # 找 {...} 块
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
    return None


def post_process(node, llm_result, log):
    """机械后处理: 校验长度 / {{name}} / 禁词, 不通过 log 警告但不阻断."""
    out = {}

    # academic_req
    ar = (llm_result.get('academic_req') or '').strip()
    REPLACE = {'理解': '看明白', '培养': '养成', '掌握': '会用', '运用': '用起来', '含义': '意思', '定义': '是啥'}
    if not ar:
        log.append(f'{node["id"]}: academic_req 为空')
    elif not (ACADEMIC_REQ_MIN <= len(ar) <= ACADEMIC_REQ_MAX):
        log.append(f'{node["id"]}: academic_req 长度 {len(ar)} 超出 {ACADEMIC_REQ_MIN}-{ACADEMIC_REQ_MAX}')
    else:
        for w, r in REPLACE.items():
            if w in ar:
                ar = ar.replace(w, r)
                log.append(f'{node["id"]}: academic_req 替换禁词 "{w}"')
    out['academic_req'] = ar

    # key_points
    kps = llm_result.get('key_points', [])
    if not isinstance(kps, list):
        kps = []
    # 禁词替换映射
    REPLACE = {'理解': '看明白', '培养': '养成', '掌握': '会用', '运用': '用起来', '含义': '意思', '定义': '是啥'}
    # 过滤空 + 长度校验 + 禁词替换
    clean_kps = []
    for kp in kps:
        kp = (kp or '').strip()
        if not kp:
            continue
        if not (KEY_POINTS_MIN_LEN <= len(kp) <= KEY_POINTS_MAX_LEN):
            log.append(f'{node["id"]}: key_point 长度 {len(kp)} 超出 {KEY_POINTS_MIN_LEN}-{KEY_POINTS_MAX_LEN}: {kp[:30]}')
            continue
        for w, r in REPLACE.items():
            if w in kp:
                kp = kp.replace(w, r)
                log.append(f'{node["id"]}: key_point 替换禁词 "{w}"')
        clean_kps.append(kp)

    # 补到 KEY_POINTS_TARGET 条
    existing = node.get('key_points', [])
    seen = set(existing)
    for kp in clean_kps:
        # V3.7.1 后处理去重: 不许重复 (跨已有 + 新增)
        if kp in seen:
            continue
        existing.append(kp)
        seen.add(kp)
    if len(existing) < KEY_POINTS_TARGET:
        log.append(f'{node["id"]}: 补完 key_points 只 {len(existing)} 条 (< {KEY_POINTS_TARGET})')
    out['key_points'] = existing[:KEY_POINTS_TARGET + 2]  # 允许多 1-2 条

    return out


def need_update(node):
    """判断是否需要 LLM 补完."""
    if not node.get('academic_req'):
        return True, '缺 academic_req'
    if len(node.get('key_points', [])) < KEY_POINTS_TARGET:
        return True, f'key_points {len(node.get("key_points", []))} < {KEY_POINTS_TARGET}'
    return False, 'OK'


def process_node(node, api_key, log, max_attempts=3):
    """处理 1 概念: 调 LLM + 后处理 + 返回新字段. 截断自动重试."""
    need, reason = need_update(node)
    if not need:
        return None  # 不需要补
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

        # 截断检测: academic_req < 30 字 / key_points < 2 条 视为截断
        ar = parsed.get('academic_req', '')
        kps = parsed.get('key_points', [])
        if len(ar) < 30 or len(kps) < 2:
            log.append(f'LLM 输出截断 (第{attempt}次) {node["id"]}: ar={len(ar)}字 kp={len(kps)}条')
            continue

        # 通过, 跑后处理
        out = post_process(node, parsed, log)
        if attempt > 1:
            log.append(f'  重试成功 (第{attempt}次) {node["id"]}')
        return out

    # 所有尝试失败
    log.append(f'❌ 全部尝试失败 {node["id"]}, 跳过')
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subject', help='只跑指定学科 (如 math)')
    parser.add_argument('--ids', nargs='+', help='只跑指定 1 个或多个 ID')
    parser.add_argument('--limit', type=int, help='最多跑 N 个概念 (测试用)')
    parser.add_argument('--out', default=str(DST), help='输出 JSON 文件')
    parser.add_argument('--reset', action='store_true', help='从 V3.3.5 重新开始 (不基于 V3.7 残留)')
    args = parser.parse_args()

    if args.reset and Path(args.out).exists():
        Path(args.out).unlink()
        print(f'🗑  重置: 删除 {args.out}')

    # V3.7.1: 优先从 DST (V3.7) 读, 增量补缺; 不存在则从 SRC (V3.3.5) 读
    src_to_use = Path(args.out) if Path(args.out).exists() else SRC
    if src_to_use == Path(args.out):
        print(f'📂 增量: 从 {args.out} 读, 跳过已补完的概念')
    else:
        print(f'📂 基础: 从 {SRC} 读 (V3.7 不存在)')

    with open(src_to_use) as f:
        data = json.load(f)
    api_key = get_api_key()
    if not api_key:
        print('❌ 找不到 ANTHROPIC_AUTH_TOKEN (在 ~/.claude/settings.json)')
        return

    nodes = data['nodes']
    if args.subject:
        nodes = [n for n in nodes if n.get('subject') == args.subject]
        print(f'🔍 只跑学科: {args.subject} ({len(nodes)} 概念)')
    if args.ids:
        nodes = [n for n in nodes if n.get('id') in args.ids]
        print(f'🔍 只跑指定 ID: {args.ids}')

    # 找需要补的
    todo = [n for n in nodes if need_update(n)[0]]
    print(f'📋 总需补: {len(todo)}/{len(nodes)}')
    if args.limit:
        todo = todo[:args.limit]
        print(f'⚠️ 限制前 {args.limit} 个 (测试)')

    if not todo:
        print('✅ 全部已 OK, 无需补')
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

    # 写新文件
    out_path = Path(args.out)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 写 log
    log_path = out_path.parent / (out_path.stem + '.log')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log))

    print()
    print(f'✅ 更新 {updated}/{len(todo)} 概念, 写到 {out_path}')
    print(f'📝 Log: {log_path}')
    print(f'⏱  总耗时: {(time.time()-start)/60:.1f}min')

    # 统计
    total = len(data['nodes'])
    has_ac = sum(1 for n in data['nodes'] if n.get('academic_req'))
    has_kp3 = sum(1 for n in data['nodes'] if len(n.get('key_points', [])) >= 3)
    print(f'📊 academic_req: {has_ac}/{total} ({has_ac/total*100:.1f}%)')
    print(f'📊 key_points ≥3: {has_kp3}/{total} ({has_kp3/total*100:.1f}%)')


if __name__ == '__main__':
    main()
