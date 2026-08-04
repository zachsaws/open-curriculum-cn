"""V4.0.6 B: 全量 difficulty 校准 prompt"""

V1_DIFF_PROMPT = """你是 K12 题目难度评估专家。给一道题, 按 Bloom 分类重新评估 difficulty 1-5。

## Bloom 难度对照:
- 1 记忆: 记住事实/概念/公式
- 2 理解: 解释/区分/推断
- 3 应用: 用学过的解题
- 4 分析: 拆解/对比/找关系
- 5 评价: 评判/论证/选最优

## 题目:
```
[题目] {question}
[题型] {qtype}
[原难度] {difficulty}
[答案] {answer}
[Bloom] {bloom}
[选项] {options}
```

## 输出 (紧凑 JSON, 不加 ```, 不加解释):

{{"difficulty": 1-5, "reason": "一句话"}}

只返 difficulty 字段, 紧凑 JSON。"""
