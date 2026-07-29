#!/usr/bin/env python3
"""
V4.0.1 P2 — 网络真题库 PoC
目标: 从公开 web 内容里抓 2024 北京中考数学 5 道真真题, LLM 解析 + 匹配 concept_id, 入库

流程:
1. web_fetch 抓 .gov.cn 真题 HTML 页面 (或原创力文档)
2. LLM 解析为结构化 JSON (题/选项/答案/解析)
3. 匹配 concept_id (基于 description + key_points embedding 相似度)
4. 入库 exercises_v1.json, is_real_exam=True + source_url

PoC 范围: math 1 学科, 5 道题
"""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SRC = ROOT / 'data' / 'graph' / 'all_v3.7_p1.json'
DST = ROOT / 'data' / 'exercises' / 'exercises_v1.json'
SETTINGS = Path.home() / '.claude' / 'settings.json'

LLM_URL = 'https://api.minimaxi.com/anthropic/v1/messages'
LLM_MODEL = 'MiniMax-M3'
LLM_MAX_TOKENS = 3000


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


# 2024 北京中考数学完整题目 (从 web_fetch 抓的 .pdf 整理)
SOURCE_RAW = """
2024年北京中考数学试卷
一、选择题(共16分,每题2分)第1-8题均有四个选项,符合题意的选项只有一个.
1.下列图形中,既是轴对称图形又是中心对称图形的是()
A.B.C.D.
答: B (既是中心对称,也是轴对称)
解析: 中心对称图形 + 轴对称图形 = 正方形/圆/正六边形等

2.如图,直线AB和CD相交于点O,OE⊥OC.若∠AOC=58°,则∠EOB的大小是()
A.29° B.32° C.45° D.58°
答: B (32°)
解析: ∠COE=∠DOE=90°, ∠BOD=∠AOC=58° (对顶角), ∠EOB=90°-58°=32°

3.实数a,b在数轴上的对应点的位置如图所示,下列结论中正确的是()
A.b>-1 B.|b|>2 C.a+b>0 D.ab>0
答: C (a+b>0)
解析: 数轴 -2<b<-1, 2<a<3, 所以 a+b>0

4.若关于x的一元二次方程x²-4x+c=0有两个相等的实数根,则实数c的值为()
A.-16 B.-4 C.4 D.16
答: C (4)
解析: Δ=(-4)²-4c=0, c=4

5.不透明袋子中仅有红、黄小球各一个,两个小球除颜色外无其他差别.从中随机摸出一个小球,放回并摇匀,再从中随机摸出一个小球,则两次摸出的都是红球的概率是()
A. 1/2 B. 1/3 C. 1/4 D. 1/6
答: C (1/4)
解析: 4种等可能结果, 1种两次红球, 1/4
"""


def parse_via_llm(raw_text, api_key):
    """LLM 解析 5 道题 + 匹配 concept_id + 给出 source_url."""
    # 加载 math 全部概念候选
    g = json.load(open(SRC))
    math_concepts = [f"- {n['id']}: {n['title']}" for n in g['nodes'] if n.get('subject') == 'math']
    math_list = '\n'.join(math_concepts)  # 全 337 个

    prompt = f"""你是 K12 数学出题/解析老师, 任务是:
1. 从下面【原始题目】中精确提取 5 道选择题 (题号 1-5)
2. 为每道题匹配 best 1 个 math concept_id (从【math 概念全表】中, 共 337 个)
3. 输出严格 JSON, 不要其他

【原始题目】:
{raw_text}

【math 概念全表 (337 个, 选最贴近的)】:
{math_list}

【输出 JSON】:
```json
{{
  "exercises": [
    {{
      "concept_id": "M_XXX_XX_XX",
      "concept_reason": "为什么匹配这个概念 (一句话)",
      "type": "multiple_choice",
      "difficulty": 2,
      "question": "题干 (完整, 含图的话用 [图] 占位)",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "answer": "B",
      "explanation": "解析 (30-80字, 说清为什么选 B 其他为什么错)",
      "source_url": "https://max.book118.com/html/2024/1203/6101221114011004.shtm"
    }},
    ... (5 道)
  ]
}}
```

要求:
- 5 道题按题号顺序
- 题目尽量紧扣本概念, 优先选择"概念最贴近"的 1 个 concept_id
- 选项 A/B/C/D 完整
- 解析 30-80 字
- 输出严格 JSON
"""
    text = call_llm(prompt, api_key)
    # 解析
    text = text.strip()
    if '```' in text:
        for p in text.split('```'):
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


def main():
    api_key = get_api_key()
    if not api_key:
        print('❌ 找不到 ANTHROPIC_AUTH_TOKEN')
        return

    print('调用 LLM 解析 5 道北京中考数学真题...')
    parsed = parse_via_llm(SOURCE_RAW, api_key)
    if not parsed:
        print('❌ LLM 解析失败')
        return

    exs = parsed.get('exercises', [])
    if len(exs) < 5:
        print(f'⚠️ 只解析到 {len(exs)} 道题')

    # 验证 concept_id 在图谱里
    g = json.load(open(SRC))
    valid_ids = {n['id']: n for n in g['nodes']}
    out_data = json.load(open(DST))
    existing_ids = {ex['id'] for ex in out_data.get('exercises', [])}

    # 真真题用 _901+ 高位号 (避开 LLM 槽位)
    # 找当前概念最大真真题号
    real_count = {}
    for ex in out_data['exercises']:
        if ex.get('is_real_exam'):
            cid = ex['concept_id']
            real_count[cid] = real_count.get(cid, 0) + 1

    n_added = 0
    for i, ex in enumerate(exs):
        cid = ex.get('concept_id', '')
        if cid not in valid_ids:
            print(f'  ⚠️ {ex.get("question", "")[:30]}... -> concept_id {cid} 不在图谱, 跳过')
            continue
        n = real_count.get(cid, 0) + 1
        ex_id = f"EX_{cid}_9{n:02d}"
        item = {
            'id': ex_id,
            'concept_id': cid,
            'type': ex.get('type', 'multiple_choice'),
            'difficulty': ex.get('difficulty', 2),
            'question': ex.get('question', '').strip(),
            'answer': ex.get('answer', ''),
            'explanation': ex.get('explanation', '').strip(),
            'bloom': ex.get('bloom', ''),
            'is_real_exam': True,
            'tags': ['真题试点', '2024北京中考', 'manual_parsed'],
            'source_url': ex.get('source_url', ''),
        }
        if item['type'] == 'multiple_choice':
            item['options'] = ex.get('options', [])
        out_data['exercises'].append(item)
        existing_ids.add(ex_id)
        real_count[cid] = n
        n_added += 1
        print(f'  ✅ {ex_id}: {ex["question"][:40]}...')
        print(f'     match: {cid} ({ex.get("concept_reason", "")[:50]})')

    with open(DST, 'w', encoding='utf-8') as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)
    print(f'\n✅ 新增 {n_added} 道真题, 总 {len(out_data["exercises"])} 题')


if __name__ == '__main__':
    main()
