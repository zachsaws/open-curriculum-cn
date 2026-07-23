# V3.3.3 chemistry 62 概念 LLM 化

## Steps
- [x] 读 chemistry_prompt.txt + chemistry_remaining_input.json (62 概念)
- [x] 借鉴 art build.py 写 chemistry build.py
- [ ] 跑 build.py (5 概念/批, 13 批预计)
- [ ] 检查 repair 是否需要 fix.py 二次补
- [ ] post-validation 全文件扫, 缺值/字符错位/模板回潮
- [ ] 合并到 all_v3.3.json, 跑出 all_v3.3.3_final.json
- [ ] 部署公网, 拿 URL
- [ ] commit + 报告

## 学到
- 化学要"具体反应/具体物质" — "把铁钉放醋里 1 天, X 看到什么? 为什么?", 避免"理解化学变化"
- 化学关键词: 反应式/化学式/元素符号/实验器材/具体物质/具体数字/单位(g/mol/mL/pH/°C)
- 缺值检测: 2+ 空格 + 化学关键词
- 字符错位: 原看明白/原掌握 等
- 模板回潮: {{name}}能举个例子吗 → 重写到具体反应场景
