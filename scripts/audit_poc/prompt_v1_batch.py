"""V1 batch 4 题版 prompt (避免 max_tokens 截断)"""

V1_BATCH_PROMPT = """你是 K12 出题审核员。一次审 4 道题, 每题独立 5 维评估。

## 4 题列表:

```
{batch_text}
```

## 5 维 (每题独立判断):
1. answer_correct: 答案对吗
2. question_clear: 题目表述清晰吗
3. options_quality: "good"/"ok"/"bad"
4. difficulty_match: 当前 difficulty 1-5 与 Bloom (1记忆 2理解 3应用 4分析 5评价) 匹配吗
5. concept_match: 题目和 concept_id 概念对应吗

## 输出

只输出 JSON 数组 4 个对象, 紧凑 JSON (不要空格换行), 不加 ```, 不加解释:

[{{"idx":1,"answer_correct":true,"question_clear":true,"options_quality":"good","difficulty_match":true,"difficulty_suggested":2,"concept_match":true,"overall_risk":"low","fix_suggestion":null}},{{"idx":2,...}},{{"idx":3,...}},{{"idx":4,...}}]

要求:
- 4 个对象必须完整
- fix_suggestion **最多 15 字中文**, 不需修就 null
- 紧凑 JSON, 不要断行, 不要解释, 不要任何前言"""
