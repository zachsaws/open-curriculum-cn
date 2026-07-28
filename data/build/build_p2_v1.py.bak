#!/usr/bin/env python3
"""
V3.7 P2 — 题目库生成 (K12 核心竞争力)
每个概念配 3-5 道题 (选择 / 填空 / 简答), 关联 lineage.

跑法: 14 学科串行, 1 个 bg task 1 个学科, 增量模式.
"""
import json
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SRC = ROOT / 'data' / 'graph' / 'all_v3.7_p1.json'
DST = ROOT / 'data' / 'exercises' / 'exercises_v1.json'
SETTINGS = Path.home() / '.claude' / 'settings.json'

LLM_URL = 'https://api.minimaxi.com/anthropic/v1/messages'
LLM_MODEL = 'MiniMax-M3'
LLM_MAX_TOKENS = 1500  # 题目长

EXERCISES_PER_CONCEPT = 3  # 每概念 3 道题 (1 选择 + 1 填空 + 1 简答)


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
    """题目库 prompt: 3 道题 (选择 + 填空 + 简答)."""
    title = node.get('title', '')
    grade = f"{node.get('grade_start', '?')}-{node.get('grade_end', '?')} 年级"
    subject = node.get('subject', '')
    difficulty = node.get('difficulty', 3)
    content_req = (node.get('content_req') or '')[:300]
    description = (node.get('description') or '')[:300]
    key_points = node.get('key_points', [])
    teaching_voice = (node.get('teaching_voice') or '')[:200]

    prompt = f"""你是 K12 出题老师, 看完下面的概念, 出 3 道题 (1 选择 + 1 填空 + 1 简答).

# 概念信息
- 标题: {title}
- 年级: {grade}
- 学科: {subject}
- 难度: {difficulty}/5
- 课标内容要求: {content_req}
- 概念描述: {description}
- 知识要点: {json.dumps(key_points, ensure_ascii=False)[:200]}
- 教学话术: {teaching_voice}

# 任务: 出 3 道题 (按本概念难度自适应)

## 第 1 题: 选择题 (4 选 1)
- 题干 20-80 字, 1 个明确问题
- 4 个选项 A/B/C/D, 1 个正确, 3 个干扰 (干扰项要紧扣本概念, 错得真实, 不能太离谱)
- answer 是字母 (A/B/C/D)
- explanation 20-50 字说明为什么对、其他为什么错

## 第 2 题: 填空题 (1-3 个空)
- 题干 20-80 字
- 用 "____" 表示空 (1-3 个空, 多个空用 "____、____" 分隔)
- answer 是关键词数组 ["关键词1", "关键词2", ...]
- explanation 20-50 字说明

## 第 3 题: 简答题 (1 道)
- 题干 20-60 字, 1 个开放问题 (描述/解释/应用/对比)
- answer 是参考答案 30-80 字 (学生可能答得不完整, 老师参考)
- explanation 30-60 字, 包含评分要点 (1. ... 2. ... 3. ...)

# 要求
- 题目要紧扣本概念**自身**, 不要出"前置概念"题 (那是别的概念的题)
- 难度 1-2/5: 选择题干扰项明显, 填空 1 个空, 简答简单描述
- 难度 3/5: 选择题干扰项迷惑, 填空 2 个空, 简答解释说明
- 难度 4-5/5: 选择题干扰项要"看着对", 填空 3 个空, 简答应用 + 推理
- 学生口吻 (像真在考试), 不要"小朋友们"这种幼稚话
- 答案必须**确定** (不要模糊, 简答允许 1-2 种答法但必须有主要答案)

# 输出 (严格 JSON, 不要其他)

```json
{{
  "exercises": [
    {{
      "type": "multiple_choice",
      "difficulty": {difficulty},
      "question": "...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "answer": "B",
      "explanation": "..."
    }},
    {{
      "type": "fill_blank",
      "difficulty": {difficulty},
      "question": "...____、____...",
      "answer": ["关键词1", "关键词2"],
      "explanation": "..."
    }},
    {{
      "type": "short_answer",
      "difficulty": {difficulty},
      "question": "...",
      "answer": "参考答案...",
      "explanation": "1. ... 2. ... 3. ..."
    }}
  ]
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
    """机械后处理: id 分配 + 字段校验."""
    out = []
    ex_id_base = f"EX_{node['id']}"
    exercises = llm_result.get('exercises', [])
    if not isinstance(exercises, list) or len(exercises) == 0:
        log.append(f'{node["id"]}: 题目为空')
        return out

    for i, ex in enumerate(exercises):
        if not isinstance(ex, dict):
            continue
        ex_id = f"{ex_id_base}_{i+1:03d}"
        et = ex.get('type', 'unknown')
        if et not in ('multiple_choice', 'fill_blank', 'short_answer'):
            log.append(f'{node["id"]}: 题型未知 {et}')
            continue
        item = {
            'id': ex_id,
            'concept_id': node['id'],
            'type': et,
            'difficulty': ex.get('difficulty', node.get('difficulty', 3)),
            'question': ex.get('question', '').strip(),
            'answer': ex.get('answer', ''),
            'explanation': ex.get('explanation', '').strip(),
            'tags': [],
        }
        if et == 'multiple_choice':
            opts = ex.get('options', [])
            if not isinstance(opts, list) or len(opts) != 4:
                log.append(f'{node["id"]} 选择题 options 不是 4 个')
                continue
            item['options'] = [str(o).strip() for o in opts]
            ans = ex.get('answer', '')
            if ans not in ('A', 'B', 'C', 'D'):
                log.append(f'{node["id"]} 选择题 answer 不是 ABCD: {ans}')
                continue
        elif et == 'fill_blank':
            ans = ex.get('answer', [])
            if isinstance(ans, str):
                ans = [ans]
            item['answer'] = [str(a).strip() for a in ans]
        # 校验
        if not item['question'] or not item['explanation']:
            log.append(f'{node["id"]} {ex_id}: 缺 question 或 explanation')
            continue
        out.append(item)
    return out


def need_update(node, existing_ids):
    """判断是否需要补完: 看本概念是否已有 ≥ EXERCISES_PER_CONCEPT 道题."""
    count = sum(1 for ex_id in existing_ids if ex_id.startswith(f"EX_{node['id']}_"))
    return count < EXERCISES_PER_CONCEPT, f'只 {count} 道 (< {EXERCISES_PER_CONCEPT})'


def process_node(node, api_key, existing_ids, log, max_attempts=3):
    need, reason = need_update(node, existing_ids)
    if not need:
        return []
    log.append(f'>>> {node["id"]} ({node.get("title", "")[:20]}): {reason}')

    prompt = build_prompt(node)
    for attempt in range(1, max_attempts + 1):
        try:
            text = call_llm(prompt, api_key)
        except Exception as e:
            log.append(f'LLM 失败 (第{attempt}次) {node["id"]}: {e}')
            time.sleep(2)
            continue

        parsed = parse_llm_output(text)
        if not parsed:
            log.append(f'LLM 输出无法 parse (第{attempt}次) {node["id"]}')
            continue

        exs = parsed.get('exercises', [])
        if len(exs) < EXERCISES_PER_CONCEPT:
            log.append(f'LLM 输出截断 (第{attempt}次) {node["id"]}: {len(exs)} 道')
            continue

        out = post_process(node, parsed, log)
        if len(out) >= EXERCISES_PER_CONCEPT - 1:  # 至少 2 道 OK
            return out

    log.append(f'❌ 全部尝试失败 {node["id"]}, 跳过')
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subject', help='只跑指定学科')
    parser.add_argument('--ids', nargs='+', help='只跑指定 ID')
    parser.add_argument('--limit', type=int, help='最多跑 N 个概念')
    parser.add_argument('--out', default=str(DST), help='输出 JSON')
    parser.add_argument('--reset', action='store_true', help='重置')
    args = parser.parse_args()

    out_path = Path(args.out)
    if args.reset and out_path.exists():
        out_path.unlink()
        print(f'🗑  重置: {out_path}')

    # 加载已有
    if out_path.exists():
        out_data = json.load(open(out_path))
        existing_ids = {ex['id'] for ex in out_data.get('exercises', [])}
        print(f'📂 增量: {out_path} 已有 {len(existing_ids)} 题')
    else:
        out_data = {'version': 'v4.0.0-p2-partial', 'exercises': []}
        existing_ids = set()
        print(f'📂 新建: {out_path}')

    api_key = get_api_key()
    if not api_key:
        print('❌ 找不到 ANTHROPIC_AUTH_TOKEN')
        return

    with open(SRC) as f:
        d = json.load(f)
    nodes = d['nodes']
    if args.subject:
        nodes = [n for n in nodes if n.get('subject') == args.subject]
    if args.ids:
        nodes = [n for n in nodes if n.get('id') in args.ids]
    todo = [n for n in nodes if need_update(n, existing_ids)[0]]
    print(f'📋 总需补: {len(todo)}/{len(nodes)}')
    if args.limit:
        todo = todo[:args.limit]
        print(f'⚠️ 限制前 {args.limit} 个 (测试)')

    log = []
    start = time.time()
    for i, node in enumerate(todo):
        rate = (i + 1) / max(time.time() - start, 0.1)
        eta = (len(todo) - i - 1) / max(rate, 0.001) / 60
        print(f'[{i+1}/{len(todo)}] {rate:.2f}/s, ETA {eta:.0f}min', flush=True)
        out = process_node(node, api_key, existing_ids, log)
        for ex in out:
            out_data['exercises'].append(ex)
            existing_ids.add(ex['id'])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)

    log_path = out_path.parent / (out_path.stem + '.log')
    with open(log_path, 'w') as f:
        f.write('\n'.join(log))

    print()
    print(f'✅ 新增 {len(todo)} 概念题目, 写到 {out_path}')
    print(f'📊 总题目数: {len(out_data["exercises"])}')


if __name__ == '__main__':
    main()
