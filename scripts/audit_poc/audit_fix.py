"""Step 3: 改写 high 风险题 prompt"""
import json
from prompts import format_exercise

V1_FIX_PROMPT = """你是 K12 出题专家。给你一道**有问题的题**, 请按审查反馈**改写**。

## 改写原则 (重要!)
- **保留原教学目标** (concept_id 不能变, 题目核心考点不能变)
- 修复**答案正确性** (硬要求, 不能错)
- 修复**题目清晰度** (学生 1 遍能看懂)
- 修复**选项设计** (4 个都是真选项, 不凑数)
- 重新标**难度** (基于 Bloom: 1记忆 2理解 3应用 4分析 5评价)
- 如**概念错配** (题目和 concept 不符), 把 concept_id 改成正确的 (从下面 candidates 选)

## 原题 (含审查反馈):

```
[原题目] {question}
[概念 ID] {concept_id} ({concept_title})
[题型] {qtype}
[原难度] {difficulty}
[Bloom] {bloom}
[原选项] {options}
[原答案] {answer}
[原解析] {explanation}

[审查反馈]
- 答案正确: {answer_correct}
- 题目清晰: {question_clear}
- 选项质量: {options_quality}
- 难度匹配: {difficulty_match} (建议 {difficulty_suggested})
- 概念对应: {concept_match}
- 修复建议: {fix_suggestion}
```

## 输出 (紧凑 JSON, 不加 ```, 不加解释):

{{"question":"改写后的题目","options":["A. ...","B. ...","C. ...","D. ..."],"answer":"A","explanation":"改写后的解析","difficulty":2,"bloom":"理解","concept_id":"{concept_id}","changed":["修了答案","选项重设","难度调为2"],"note":"一句话说明改了什么"}}
"""
