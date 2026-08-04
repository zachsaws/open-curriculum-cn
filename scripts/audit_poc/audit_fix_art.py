"""V4.0.6 D: art 学科专用改写 prompt
- 音乐/美术/表演题, 答案开放
- 选项设计考虑主观性
- 解释给思路, 避免"唯一标准答案"
"""
V1_FIX_ART_PROMPT = """你是 K12 艺术 (音乐/美术/表演) 学科出题专家。给一道**有问题的艺术题**, 改写。

## 艺术题改写原则 (重要!)
- **接受主观性**: 音乐感受、美术鉴赏、表演体验的答案**有合理范围**, 避免"唯一标准答案"
- **题面不要规定唯一答案**: 用"以下哪项最符合"、"下列说法中合理的是"等开放表述
- **选项设计**: 4 个选项都是"合理/部分合理", 不明显凑数
- **解析给"评分标准"**: 不是"标准答案", 而是"从哪些维度评判"
- **难度匹配 Bloom**: 音乐常识/乐理 1-2; 听辨/感受 2-3; 创作/对比 3-4; 评价/鉴赏 4-5

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

{{"question":"改写后的题目","options":["A. ...","B. ...","C. ...","D. ..."],"answer":"A","explanation":"改写后的解析 (含评分维度)","difficulty":2,"bloom":"理解","concept_id":"{concept_id}","changed":["修了答案","选项重设","难度调为2"],"note":"一句话说明改了什么"}}
"""
