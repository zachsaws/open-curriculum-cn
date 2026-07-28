#!/usr/bin/env python3
"""
V4.0.1 P2 v2 — 题目库生成 (K12 核心竞争力升级版)
每概念配 5 道题 (5 道互补设计):
  T1 选择题 (基础概念辨析) — A/B/C/D 考察 4 个不同维度
  T2 填空题 (关键步骤/关键词记忆)
  T3 简答题 (解释/描述)
  T4 应用题 (真实情境/真题风格) — 贴近中考/小升初真题
  T5 综合题 (跨本概念 + 前置/后置概念, 真题压轴) — 综合推理/分析

跑法: 14 学科串行, 1 个 bg task 1 个学科, 增量模式.
增量逻辑: 跳过已有 ≥ 5 道的概念, 缺几道补几道.
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
LLM_MAX_TOKENS = 2500  # 5 道题更长

EXERCISES_PER_CONCEPT = 5  # 升级: 3 → 5


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
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read())
                return data['content'][0]['text']
        except urllib.error.HTTPError as e:
            last_err = f'HTTP {e.code}: {e.read()[:200].decode("utf-8","replace")}'
        except Exception as e:
            last_err = f'{type(e).__name__}: {e}'
        time.sleep(2 + attempt * 2)
    raise RuntimeError(f'LLM 失败 3 次: {last_err}')


def build_prompt(node, missing_types):
    """题目库 prompt: 按 missing_types 补 5 道题中的部分.

    missing_types: 该概念需要补哪些题型, e.g. ['apply', 'synthesize']
    """
    title = node.get('title', '')
    grade = f"{node.get('grade_start', '?')}-{node.get('grade_end', '?')} 年级"
    subject = node.get('subject', '')
    difficulty = node.get('difficulty', 3)
    content_req = (node.get('content_req') or '')[:300]
    description = (node.get('description') or '')[:300]
    key_points = node.get('key_points', [])
    teaching_voice = (node.get('teaching_voice') or '')[:200]
    real_examples = node.get('real_examples', [])[:2]
    common_mistakes = node.get('common_mistakes', [])[:2]

    # 描述每道题要补什么
    slot_specs = {
        'choice': {
            't_num': 1, 'type': 'multiple_choice', 'bloom': '理解',
            'desc': '基础概念辨析 - 4 个选项考察 4 个不同维度',
            'guide': """- 题干 20-80 字, 1 个明确问题
- 4 个选项 A/B/C/D 必须考察【不同维度】(不要都是同概念 4 种变体), 例如:
  · A 考定义, B 考典型例子, C 考常见误区, D 考应用场景
  · A 考原因, B 考结果, C 考对比, D 考例外
  · 4 个维度来自【本概念的不同侧面】(定义/性质/原因/影响/例子/对比/误区/应用)
- 干扰项要"看着对"但有细微错误 (不要一眼假)
- answer 是字母 (A/B/B/C/D)
- explanation 20-50 字说明为什么对、其他为什么错""",
        },
        'fill': {
            't_num': 2, 'type': 'fill_blank', 'bloom': '记忆',
            'desc': '填空题 - 关键步骤/关键词记忆',
            'guide': """- 题干 20-80 字, 1-3 个空
- 用 "____" 表示空 (1-3 个空, 多个空用 "____、____" 分隔)
- 考【关键步骤】或【关键词】, 不是简单记忆字面
- answer 是关键词数组 ["关键词1", "关键词2", ...]
- explanation 20-50 字说明""",
        },
        'explain': {
            't_num': 3, 'type': 'short_answer', 'bloom': '分析',
            'desc': '简答题 - 解释/描述',
            'guide': """- 题干 20-60 字, 1 个开放问题 (解释/描述/对比)
- answer 是参考答案 30-80 字 (学生可能答得不完整, 老师参考)
- explanation 30-60 字, 包含评分要点 (1. ... 2. ... 3. ...)""",
        },
        'apply': {
            't_num': 4, 'type': 'short_answer', 'bloom': '应用',
            'desc': '应用题 - 真实情境/真题风格',
            'guide': """- 【真题风格】参考中考/小升初/会考常见考法
- 真实生活情境 (生活/科技/历史/跨学科), 不是抽象题
- 题干 30-100 字, 1-2 个具体问题
- 答案要求【分步骤】:
  · 审题: 1-2 句说明已知/求解
  · 分析: 1-2 句点出本概念关键点
  · 解答: 30-80 字完整过程或结论
- answer 是 50-150 字的完整解答
- explanation 是评分要点 1./2./3. (解题关键步骤分)""",
        },
        'synthesize': {
            't_num': 5, 'type': 'short_answer', 'bloom': '评价/综合',
            'desc': '综合题 - 跨本概念 + 前置/后置概念, 真题压轴',
            'guide': """- 【真题压轴】高考/中考压轴题风格
- 必须【跨本概念 + 1-2 个相关概念】(可参考前置/后置概念), 综合推理
- 题干 50-120 字, 1 个综合问题 (对比/辨析/推理/评价/设计)
- 例如:
  · "对比 A 与 B 概念的本质差异, 并各举 1 例"
  · "用本概念 + 前置概念, 解释 [现象]"
  · "评价 [方法] 在 [场景] 的适用性"
- answer 是 80-200 字的综合论述 (分 2-3 段, 体现综合分析)
- explanation 是评分要点 1./2./3./4. (每段/每维度的得分点)""",
        },
    }

    slots = '\n\n'.join(
        f"## 第 {slot_specs[t]['t_num']} 题 ({slot_specs[t]['type']}, Bloom: {slot_specs[t]['bloom']}) - {slot_specs[t]['desc']}\n{slot_specs[t]['guide']}"
        for t in missing_types
    )

    prompt = f"""你是 K12 出题老师, 看完下面的概念, 补 {len(missing_types)} 道题, 题型见下方.

# 概念信息
- 标题: {title}
- 年级: {grade}
- 学科: {subject}
- 难度: {difficulty}/5
- 课标内容要求: {content_req}
- 概念描述: {description}
- 知识要点: {json.dumps(key_points, ensure_ascii=False)[:200]}
- 教学话术: {teaching_voice}
- 真实例子: {json.dumps(real_examples, ensure_ascii=False)[:150]}
- 常见误区: {json.dumps(common_mistakes, ensure_ascii=False)[:150]}

# 任务: 补 {len(missing_types)} 道题

{slots}

# 要求
- 题目要紧扣本概念【自身】, 不要出"前置概念"题 (那是别的概念的题)
- 学生口吻 (像真在考试), 不要"小朋友们"这种幼稚话
- 答案必须【确定】 (不要模糊, 简答允许 1-2 种答法但必须有主要答案)
- 难度 1-2/5: 题目直接, 选项/空少
- 难度 3/5: 有干扰/陷阱
- 难度 4-5/5: 综合/推理
- T1 4 个选项【必须考察 4 个不同维度】(最关键)
- T4/T5 要有【真题风】, 不是抽象题

# 输出 (严格 JSON, 不要其他)

```json
{{
  "exercises": [
"""
    # 模板
    template_per_type = {
        'multiple_choice': '''    {{
      "type": "multiple_choice",
      "difficulty": {difficulty},
      "question": "...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "answer": "B",
      "explanation": "...",
      "bloom": "理解"
    }}''',
        'fill_blank': '''    {{
      "type": "fill_blank",
      "difficulty": {difficulty},
      "question": "...____、____...",
      "answer": ["关键词1", "关键词2"],
      "explanation": "...",
      "bloom": "记忆"
    }}''',
        'short_answer': '''    {{
      "type": "short_answer",
      "difficulty": {difficulty},
      "question": "...",
      "answer": "参考答案...",
      "explanation": "1. ... 2. ... 3. ...",
      "bloom": "应用/分析/评价"
    }}''',
    }
    slot_templates = []
    for t in missing_types:
        slot_info = slot_specs[t]
        if slot_info['type'] == 'multiple_choice':
            slot_templates.append(template_per_type['multiple_choice'].format(difficulty=difficulty))
        elif slot_info['type'] == 'fill_blank':
            slot_templates.append(template_per_type['fill_blank'].format(difficulty=difficulty))
        else:
            slot_templates.append(template_per_type['short_answer'].format(difficulty=difficulty))

    prompt += ',\n'.join(slot_templates) + '''
  ]
}
```'''
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


def need_update(node, existing_ids):
    """判断需要补哪些题型. 升级到 5 道题.

    Returns: (need: bool, missing_types: list[str])
    missing_types: 需要补的题型槽位 ['choice', 'fill', 'explain', 'apply', 'synthesize']
    """
    prefix = f"EX_{node['id']}_"
    existing = sorted(ex_id for ex_id in existing_ids if ex_id.startswith(prefix))
    n_have = len(existing)
    if n_have >= EXERCISES_PER_CONCEPT:
        return False, []

    # 5 道题槽位（顺序固定）:
    # _001 = T1 choice (基础)
    # _002 = T2 fill (填空)
    # _003 = T3 explain (简答)
    # _004 = T4 apply (应用/真题)
    # _005 = T5 synthesize (综合/压轴)
    slot_order = ['choice', 'fill', 'explain', 'apply', 'synthesize']
    missing = slot_order[n_have:]
    return True, missing


def post_process(node, llm_result, missing_types, log, existing_ids_for_node):
    """机械后处理: id 分配 + 字段校验."""
    out = []
    # 计算 id 起始号 = 已有题数 + 1
    start_num = len(existing_ids_for_node) + 1
    exercises = llm_result.get('exercises', [])
    if not isinstance(exercises, list) or len(exercises) == 0:
        log.append(f'{node["id"]}: 题目为空')
        return out

    n_added = 0
    for i, ex in enumerate(exercises):
        if not isinstance(ex, dict):
            continue
        ex_id = f"EX_{node['id']}_{start_num + n_added:03d}"
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
            'bloom': ex.get('bloom', '').strip(),
            'is_real_exam': False,  # 手动入库时设 True
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
        # 字数校验
        if et == 'short_answer' and len(item['answer']) < 20:
            log.append(f'{node["id"]} {ex_id}: 简答答案太短 ({len(item["answer"])} 字)')
            continue
        if et == 'multiple_choice':
            # 选项必须考察不同维度 — 用长度/关键词粗略检查
            # 这个很难自动检查, 只校验选项长度都 > 1 字
            if any(len(o) < 2 for o in item['options']):
                log.append(f'{node["id"]} {ex_id}: 选项过短')
                continue
        out.append(item)
        n_added += 1
        if n_added >= len(missing_types):
            break
    return out


def process_node(node, api_key, existing_ids, log, max_attempts=3):
    need, missing_types = need_update(node, existing_ids)
    if not need:
        return []
    log.append(f'>>> {node["id"]} ({node.get("title", "")[:20]}): 补 {len(missing_types)} 道 ({missing_types})')

    prompt = build_prompt(node, missing_types)
    prefix = f"EX_{node['id']}_"
    existing_ids_for_node = [ex_id for ex_id in existing_ids if ex_id.startswith(prefix)]

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
        if len(exs) < len(missing_types):
            log.append(f'LLM 输出截断 (第{attempt}次) {node["id"]}: {len(exs)}/{len(missing_types)}')
            continue

        out = post_process(node, parsed, missing_types, log, existing_ids_for_node)
        if len(out) >= len(missing_types) - 1:  # 至少 1 道 OK
            return out

    log.append(f'❌ 全部尝试失败 {node["id"]}, 跳过')
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subject', help='只跑指定学科')
    parser.add_argument('--ids', nargs='+', help='只跑指定 ID')
    parser.add_argument('--limit', type=int, help='最多跑 N 个概念')
    parser.add_argument('--out', default=str(DST), help='输出 JSON')
    parser.add_argument('--reset', action='store_true', help='⚠️ 重置 (删已有)')
    parser.add_argument('--dry-run', action='store_true', help='只列出需要补的概念, 不调 LLM')
    args = parser.parse_args()

    out_path = Path(args.out)
    if args.reset and out_path.exists():
        out_path.unlink()
        print(f'🗑  重置: {out_path}')

    # 加载已有
    if out_path.exists():
        out_data = json.load(open(out_path))
        existing_ids = {ex['id'] for ex in out_data.get('exercises', [])}
        # Fixup: 给老题 (V1 时代的) 按 id 后缀回填 bloom 和 is_real_exam
        bloom_by_suffix = {'001': '理解', '002': '记忆', '003': '分析', '004': '应用', '005': '评价/综合'}
        n_fixed = 0
        for ex in out_data.get('exercises', []):
            if 'bloom' not in ex or not ex.get('bloom'):
                suffix = ex['id'].split('_')[-1]
                ex['bloom'] = bloom_by_suffix.get(suffix, '')
                n_fixed += 1
            if 'is_real_exam' not in ex:
                ex['is_real_exam'] = False
        if n_fixed:
            print(f'🔧 Fixup: {n_fixed} 老题回填 bloom + is_real_exam')
        print(f'📂 增量: {out_path} 已有 {len(existing_ids)} 题')
    else:
        out_data = {'version': 'v4.0.1-p2-partial', 'exercises': []}
        existing_ids = set()
        print(f'📂 新建: {out_path}')

    api_key = get_api_key()
    if not api_key and not args.dry_run:
        print('❌ 找不到 ANTHROPIC_AUTH_TOKEN')
        return

    with open(SRC) as f:
        d = json.load(f)
    nodes = d['nodes']
    if args.subject:
        nodes = [n for n in nodes if n.get('subject') == args.subject]
    if args.ids:
        nodes = [n for n in nodes if n.get('id') in args.ids]

    # 找需要补的概念
    todo = []
    for n in nodes:
        need, missing = need_update(n, existing_ids)
        if need:
            todo.append((n, missing))

    print(f'📋 总需补: {len(todo)}/{len(nodes)} 概念')
    total_new = sum(len(m) for _, m in todo)
    print(f'📋 总需补题: {total_new} 道')

    # 学科分布
    from collections import Counter
    subj_count = Counter()
    subj_q = Counter()
    for n, missing in todo:
        subj_count[n.get('subject', '?')] += 1
        subj_q[n.get('subject', '?')] += len(missing)
    print('  学科分布:')
    for s in sorted(subj_count.keys(), key=lambda x: -subj_count[x]):
        print(f'    {s}: {subj_count[s]} 概念 / {subj_q[s]} 题')

    if args.dry_run:
        print('\n[DRY-RUN] 退出')
        return

    if args.limit:
        todo = todo[:args.limit]
        print(f'⚠️ 限制前 {args.limit} 个 (测试)')

    log = []
    start = time.time()
    FLUSH_EVERY = 20  # 每 20 个概念写盘一次, 避免 race condition 丢数据
    for i, (node, missing_types) in enumerate(todo):
        rate = (i + 1) / max(time.time() - start, 0.1)
        eta = (len(todo) - i - 1) / max(rate, 0.001) / 60
        print(f'[{i+1}/{len(todo)}] {node["id"]} 补{len(missing_types)}道 {rate:.2f}/s, ETA {eta:.0f}min', flush=True)
        out = process_node(node, api_key, existing_ids, log)
        for ex in out:
            out_data['exercises'].append(ex)
            existing_ids.add(ex['id'])

        # 定期写盘 (避免 race condition 丢数据)
        if (i + 1) % FLUSH_EVERY == 0 or (i + 1) == len(todo):
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(out_data, f, ensure_ascii=False, indent=2)
            print(f'  💾 [FLUSH] {i+1}/{len(todo)} 写盘, 当前 {len(out_data["exercises"])} 题', flush=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)

    log_path = out_path.parent / (out_path.stem + '.log')
    with open(log_path, 'w') as f:
        f.write('\n'.join(log))

    print()
    print(f'✅ 新增题目, 写到 {out_path}')
    print(f'📊 总题目数: {len(out_data["exercises"])}')


if __name__ == '__main__':
    main()
