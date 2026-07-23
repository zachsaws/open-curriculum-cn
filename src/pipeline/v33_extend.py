"""
V3.3.1 扩展: 14 学科并行 sub-agent, 每个处理一个学科的所有概念.

用法:
    python src/pipeline/v33_extend.py

会:
1. 为 14 学科各生成 1 个 sub-agent prompt
2. 调用 mavis task 工具 (run_in_background) 并行启动
3. 打印 task_id 列表
4. 后续用 task_query / task_output 查进度
"""
import json
import os
import sys
import subprocess

ROOT = '/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn'
os.chdir(ROOT)

# 学科配置
SUBJECTS = [
    ('math', '数学', 337),
    ('chinese', '语文', 209),
    ('english', '英语', 296),
    ('history', '历史', 136),
    ('physics', '物理', 121),
    ('science', '科学', 121),
    ('morality_law', '道德与法治', 115),
    ('info_tech', '信息科技', 97),
    ('geography', '地理', 91),
    ('pe_health', '体育与健康', 87),
    ('labor', '劳动', 85),
    ('art', '艺术', 78),
    ('biology', '生物', 71),
    ('chemistry', '化学', 62),
]

PROMPT_TEMPLATE = """你是 V3.3.1 内容 LLM 化工程师, 任务: 为 {subj_cn} (subject={subj}, 共 {n} 概念) 所有概念生成**人话级**的 description 和 assessment_prompt.

## 输入
- 学科所有概念 (含 id/title/summary/content_req/academic_req/key_points/bloom/type/age_range):
  {input_path}

## 输出
- 写到: {output_path}
- 格式: JSON list, 每条必须含原 id + `description` + `assessment_prompt` 三个字段 (其它字段从原 input 复制, 不要丢)

## 严格要求 (V3.3.1 PoC 学到的教训)

### 1. description 风格
- 长度 60-100 字 (含标点), 1 段, 中间可用「」, 不允许换行
- **必须用具体场景代替抽象定义** — 写"在披萨上切一半 = 1/2" 而非"理解分数的概念"
- **不要用绝对化承诺** — 避免"一定/必然/肯定"等词
- **要反直觉, 要画面感** — 优于课标原文 (例: "3 不只是 3 而是 3 个百" 优于 "理解位值的意义")

### 2. assessment_prompt 风格 (更重要, 这是 LLM 化的核心)
- 长度 150-220 字
- **必须正好 3 个评估问题**, 每问 1 行, 行间用 `\\n` (一个反斜杠加 n) 分隔
- 每问必须含 `{{{{name}}}}` 占位符 (1 个, 不能多, 不能少)
- **场景必须具体**: 含具体数字/具体物品/具体动作/具体对话 — 拒绝"理解 X 这一概念, 能否独立完成相关题目?" 这种空问
- **要区分度**: 3 问难度递进 — 第 1 问直接识别, 第 2 问操作/反例, 第 3 问解释/迁移
- **中文要自然**: 用"能不能 / 会不会 / 会不会出现" 优于 "能否"

### 3. 禁词 (BANNED, 命中必须改)
- `理解 / 培养 / 掌握 / 运用 / 知识点 / 课标 / 教学目标 / 含义 / 定义 / 本概念 / 该概念 / 本节 / 本文 / 通过本 / 课标要求 / 具体含义`
- 禁词 0 容忍, 自查 1 遍

### 4. 模板词 (BANNED, 这些是 V3.2 公文腔痕迹)
- 句式: "在 X 课上, {{name}} 能否..."
- 句式: "用自己的话解释 X 的含义"
- 句式: "独立完成相关题目"
- 句式: "举出一个生活中的例子"

## PoC 标杆 (5/5 抽样, 这就是质量底线, 不要低于此)

```
id: M_G1_NS_02 (位值, G1)
description: 同一个数字「2」,放在个位是 2、放在十位是 20、放在百位是 200——位置变了,值就变了。孩子写「345」时知道 3 不只是 3 而是 3 个百,这就是位值感。
assessment: 看到数字 506,{{name}}能不能马上说「5 在百位上所以是 500,0 在十位上是 0 个十」?\\n把 4 写在十位、把 4 写在个位组成两个数(如 44 和 404),{{name}}能不能解释为什么这两个 4 差这么多?\\n在计数器上拨珠子,{{name}}能不能拨出一个 4 位数后,再拨一个 4 位数,自己说出「我移了一个珠子,从 1000 变成 100」?
```

## 工作流

1. 读 input JSON
2. 对每个概念, 写 `description` + `assessment_prompt`
3. 写入 output JSON
4. **必须做 post-validation** (这一步容易漏, 别学 PoC 撒谎):
   - description 长度 60-100
   - assessment_prompt 长度 150-220
   - assessment_prompt 含 `{{{{name}}}}` 正好 3 次
   - assessment_prompt 含 `\\n` 至少 2 次
   - 禁词列表命中数 = 0
   - **不达标的概念必须重写, 不允许带病通过**
5. 报告:
   - 成功数 / 总数
   - 平均 description 字数 / 平均 assessment 字数
   - 禁词命中数 (应 = 0)
   - 重写次数
   - **不要估计数字, 必须用脚本实数**

## 学科特殊提示

- {subj_cn}: {subj_specific}

## 重要: 不要触碰的

- 输入文件: 只读, 不要修改
- V3.0/V3.1/V3.2 数据文件: 不要修改
- API: 不要改 api/server.py, 不要改 web/

## 完成后

返回 1 段简短报告 (4-5 行), 包含数字 (description/assessment 长度, {{name}} 数, 禁词数, 失败重写数).
"""


SUBJ_HINT = {
    'math': '数学最强调"具体场景 + 数字" — 用苹果/披萨/计数器/算盘/教室, 避免纯文字描述',
    'chinese': '语文要扣"原文/字词/句子/段落"层级 — 用课文片段或具体字例 (例: "把"字), 避免空泛"理解课文"',
    'english': '英语场景用"对话/单词卡/角色扮演" — 例: 问"apple 怎么用? 写出 3 个句子", 避免"掌握词汇"',
    'history': '历史要"具体年代 + 具体事件 + 具体人物" — 例: "1937 年 7 月 7 日, X 在卢沟桥看到什么?", 避免"了解历史"',
    'physics': '物理要"实验/具体现象" — 例: "用尺子量课本长度, X 能不能读出 25.4 cm?", 避免"理解物理量"',
    'chemistry': '化学要"具体反应/具体物质" — 例: "把铁钉放醋里 1 天, X 看到什么? 为什么?", 避免"理解化学变化"',
    'biology': '生物要"具体生物/具体现象" — 例: "看到蚂蚁搬家, X 能不能说出 3 个原因?", 避免"理解生态系统"',
    'science': '科学要"具体实验" — 例: "把冰块放杯子里, X 能不能描述 5 分钟内发生什么?", 避免"理解科学概念"',
    'geography': '地理要"具体地点 + 具体特征" — 例: "看中国地图, X 能不能指出 3 条长江流经的省份?", 避免"了解地理"',
    'morality_law': '道德与法治要"具体情境 + 行为选择" — 例: "同学抄你作业, X 怎么办? 说出 2 种方式", 避免"培养品德"',
    'info_tech': '信息科技要"具体操作" — 例: "在 Word 里点 3 次, X 能不能把字体改成红色?", 避免"掌握操作"',
    'pe_health': '体育要"具体动作 + 具体标准" — 例: "立定跳远 1.5 米及格, X 跳了几次达标?", 避免"提高体能"',
    'art': '艺术要"具体作品/具体技法" — 例: "用红黄蓝三色, X 能不能调出绿色? 试 2 次", 避免"培养审美"',
    'labor': '劳动要"具体劳动任务" — 例: "扫地 5 分钟, X 能不能扫干净 5 平米地面?", 避免"培养劳动习惯"',
}


def main():
    print("V3.3.1 扩展: 14 学科并行 sub-agent 启动")
    print("=" * 70)

    task_ids = []

    for subj, subj_cn, n in SUBJECTS:
        input_path = f'data/v33_inputs/{subj}_input.json'
        output_path = f'data/graph/{subj}_v33_llm.json'
        subj_specific = SUBJ_HINT.get(subj, '用具体场景, 避免抽象描述')

        if not os.path.exists(input_path):
            print(f"❌ 缺 input: {input_path}")
            continue

        prompt = PROMPT_TEMPLATE.format(
            subj=subj, subj_cn=subj_cn, n=n,
            input_path=input_path, output_path=output_path,
            subj_specific=subj_specific,
        )

        # 写到 prompt 文件 (sub-agent 可以读)
        prompt_file = f'data/v33_inputs/{subj}_prompt.txt'
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"  ✓ {subj:14s} ({subj_cn:6s}) {n:4d} 概念 → prompt {prompt_file}")

    print()
    print("Prompt 文件已生成。下一步: 启动 14 sub-agent 并行.")
    print("运行: 后续用 mavis task 工具逐个启动, prompt 从 _prompt.txt 读")
    print()
    print("=" * 70)
    print("学科列表 (按从大到小, 建议优先启动 math 337):")
    for i, (s, cn, n) in enumerate(SUBJECTS, 1):
        print(f"  {i:2d}. {s:14s} {cn:6s} {n:4d}")


if __name__ == '__main__':
    main()
