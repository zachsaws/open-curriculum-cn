"""4 个 prompt 版本用于对比"""
import json

# 题目标准化输入格式
def format_exercise(e, concept_title=''):
    """返 题目结构化文本"""
    q = e.get('question', '').strip() if isinstance(e.get('question'), str) else str(e.get('question', ''))
    a_raw = e.get('answer', '')
    if isinstance(a_raw, list):
        a = ', '.join(str(x) for x in a_raw)
    else:
        a = str(a_raw).strip()
    expl = e.get('explanation', '').strip() if isinstance(e.get('explanation'), str) else str(e.get('explanation', ''))
    diff = e.get('difficulty', '?')
    bloom = e.get('bloom', '')
    t = e.get('type', '')
    opts = e.get('options', []) or []
    cid = e.get('concept_id', '')

    text = f"""[题目] {q}
[概念 ID] {cid} {f'({concept_title})' if concept_title else ''}
[题型] {t}
[难度] {diff} (1=最易, 5=最难)
[Bloom] {bloom}
[选项] {chr(10).join(opts) if opts else 'N/A'}
[答案] {a}
[解析] {expl}"""
    return text


# ============== V1: 严格 5 维评分 ==============
V1_PROMPT = """你是一位资深 K12 教研员 + 出题审核员。审一道题，按 5 个维度严格评估:

```
[题目信息]
{ex_text}
```

请输出严格 JSON (不加解释, 不加 markdown 代码块):
{{
  "answer_correct": true/false,           // 答案是否正确
  "answer_correct_reason": "...",         // 1 句话解释
  
  "question_clear": true/false,           // 题目表述是否清晰
  "question_clear_reason": "...",         // 1 句话解释
  
  "options_quality": "good"/"ok"/"bad",   // 选项设计质量
  "options_quality_reason": "...",        // 1 句话解释
  
  "difficulty_match": true/false,         // 难度 1-5 是否匹配实际
  "difficulty_suggested": 1-5,            // 建议难度
  "difficulty_reason": "...",             // 1 句话解释
  
  "concept_match": true/false,            // 题目和概念是否对应
  "concept_match_reason": "...",          // 1 句话解释
  
  "overall_risk": "high"/"medium"/"low",  // 整体风险
  "fix_suggestion": "..."                 // 修复建议 (1 句)
}}

判定标准 (严):
- answer_correct: 选择题看答案对, 简答题看解析推答案是否合理
- question_clear: 学生看一眼能直接做, 不绕弯
- options_quality: 选择题 4 个选项是否都是真选项 (不是明显凑数)
- difficulty_match: 难度是否符合 [1=记忆 2=理解 3=应用 4=分析 5=评价] Bloom
- concept_match: 题目考的内容是否对应 concept_id 标注的概念"""


# ============== V2: 宽松 3 档评分 ==============
V2_PROMPT = """你审一道 K12 题目, 判断是否有问题。

```
[题目信息]
{ex_text}
```

如果有下面任何问题, 标 "high":
- 答案明显错
- 题目有歧义 / 看不懂
- 选项凑数 (比如 4 选 1, 2 个明显错得离谱)
- 难度标得和实际差很多 (比如标 1 实际很难, 标 5 实际很简单)
- 题目和 concept_id 概念不对应

如果基本能用, 但有小毛病, 标 "medium":
- 解析不够清楚
- 选项设计一般
- 难度小漂

完全没问题, 标 "low"。

输出 JSON:
{{"risk": "high"/"medium"/"low", "issues": ["issue1", "issue2"], "summary": "一句话说明"}}"""


# ============== V3: 极简 1 行 ==============
V3_PROMPT = """审这道 K12 题, 1-5 评分 (5 最好):

```
{ex_text}
```

考虑:
- 答案对吗
- 题看得懂吗
- 难度标注 1-5 准吗
- 跟概念对得上吗

只输出一行 JSON:
{{"score": 1-5, "reason": "1 句话原因"}}"""


# ============== V4: 详细长答 (给改写建议) ==============
V4_PROMPT = """你是一位特级教师 + 课程主编, 严格审一道 K12 题目。

```
[题目信息]
{ex_text}
```

请按以下 5 段回答, 每段 1-3 句:

1. **答案审核**: 答案对吗? 简答题答案是否合理完整?
2. **题目表述**: 学生能否 1 遍看懂? 有无歧义/绕弯?
3. **选项设计** (选择/填空): 是否都是真选项? 是否有凑数?
4. **难度评估**: 当前 difficulty 1-5 是否准? 应改为?
5. **概念对应**: 题目考的内容和 concept_id 概念对得上吗?

然后给:
- overall_risk: "high"/"medium"/"low"
- 改写版本 (如果 high 风险): 重写题目 + 答案

最后输出 JSON:
{{
  "answer_correct": "...",
  "question_clear": "...",
  "options_quality": "...",
  "difficulty_review": "...",
  "concept_match": "...",
  "overall_risk": "high"/"medium"/"low",
  "rewrite": "..." // 改写版本, 不需要改写时 null
}}"""


PROMPTS = {
    'v1_strict_5d': V1_PROMPT,
    'v2_loose_3tier': V2_PROMPT,
    'v3_minimal_1line': V3_PROMPT,
    'v4_detailed_rewrite': V4_PROMPT,
}
