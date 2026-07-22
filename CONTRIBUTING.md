# 贡献指南 · Open Curriculum CN

> 任何人都可以贡献 — 一线老师、教研员、家长、学生、开发者。

## 贡献类型

我们欢迎 5 类贡献：

### 1. 新增概念 PR
适合人群：老师 / 教研员
- 任务：补全 V0.7 字段或新增未覆盖的概念
- 文件：`data/graph/{subject}_v0.7.json`
- 格式：见 [docs/schema.md](docs/schema.md)
- 自评：跑 `python src/pipeline/enrich_subject.py --subject {subject} --round 1`

### 2. 课标原文校对
适合人群：老师 / 教研员 / 学科专家
- 任务：检查 `content_req` 字段是否真在课标里，字对不对
- 流程：打开 `data/graph/{subject}_v0.7.json`，抽样 20 个概念，查 `src_page` 页码

### 3. 关系图谱补充
适合人群：任何上过相关学科的人
- 任务：补 `M_G3_NS_01 → M_G4_NS_01` 这类先决关系
- 文件：`data/graph/all_v0.7.json` 的 `edges` 数组
- 格式：`{"from": "M_G3_NS_01", "to": "M_G4_NS_01", "type": 1}` (1=硬, 0=软)

### 4. 教师审核
适合人群：教 1-9 年级某学科的一线老师
- 任务：抽样 50 个概念审核
- 流程：填 [docs/teacher-review.md](docs/teacher-review.md) 问卷
- 审核样题：
  - 概念标题是否准确
  - content_req 字段是否真在课标
  - 难度评级 1-5 是否合理
  - estimated_minutes 是否合理
  - bloom 动词是否准确
  - 关系图 (先决/后继) 是否正确

### 5. 代码贡献
适合人群：开发者
- 任务：前端 / 后端 / 数据 pipeline
- 流程：fork → branch → PR
- 详见下节

## 开发者流程

### 环境要求

```bash
Python 3.12+
Node 18+ (前端)
tesseract 5.x + tesseract-lang (含 chi_sim)
```

### Fork & Branch

```bash
git clone https://github.com/your-name/open-curriculum-cn
cd open-curriculum-cn
git checkout -b feat/your-feature
```

### 开发

```bash
# 后端
source .venv/bin/activate
pip install -e .

# 前端
cd web
python -m http.server 8000  # 本地访问 http://127.0.0.1:8000
```

### 自评

每次 commit 前必跑：

```bash
# 1. enrich 重跑（确保没有破坏）
python src/pipeline/enrich_subject.py --subject {subject} --round 1

# 2. 合并
python src/pipeline/merge_v0.7_all.py

# 3. 截图验证
python src/validate/screenshot_v07.py
# 看 data/screenshots/v07_*.png 是否正常

# 4. 单元测试（如适用）
python -m pytest api/tests/
```

### PR 检查清单

- [ ] 自评全 PASS (`{subject}_review_r1.json` 里 verdict=PASS)
- [ ] 概念 ID 唯一（无重复）
- [ ] 关系 from/to 引用存在的概念（无悬空）
- [ ] 没有自环边 (from == to)
- [ ] 学段一致（概念 grade_start 在 stage 范围内）
- [ ] 改动一个 commit 一个功能（不要 mix）

### Commit 规范

```
v0.X: 简短描述 (≤ 50 字)

- 改动点 1
- 改动点 2
- 自评结果
```

例：
```
v0.7.5: 14 学科 enrich PASS

- math: 214 概念, OCR 匹配 100%
- chinese: 75 概念, OCR 匹配 100%
- 14/14 PASS
```

## 数据 schema

详见 [docs/schema.md](docs/schema.md)。核心字段：

```json
{
  "id": "M_G4_QR_05",                  // 唯一 ID
  "subject": "math",                    // 学科
  "stage": 4,                            // 1-4
  "grade_start": 7,                      // 起始年级
  "grade_end": 9,                        // 结束年级
  "title": "一元二次方程",               // 中文标题
  "domain": "数量关系",                  // 大领域
  "subdomain": "方程",                   // 子领域
  "difficulty": 3,                       // 1-5
  "summary": "会用直接开平方法/配方法/公式法/因式分解法解一元二次方程",
  "content_req": "...",                  // 课标内容要求原文
  "academic_req": "...",                 // 课标学业要求原文
  "examples": ["例 1"],                  // 课标例题引用
  "key_points": ["会解...", "..."],      // 知识要点
  "bloom": ["会"],                        // 布鲁姆分类动词
  "estimated_minutes": 40,               // 估计学习时间
  "src_page": 53,                         // 课标 PDF 页码
  "src_stage": "第四学段",
  "src_domain_ocr": "方程",
  "review_round": 1,
  "review_status": "passed"
}
```

## 优先级

- P0: 数学 / 物理 / 化学 / 生物 (2022 改版最大)
- P1: 语文 / 英语 (量大)
- P2: 历史 / 地理 / 道法 / 科学
- P3: 信息科技 / 艺术 / 体育 / 劳动

## 沟通

- GitHub Issues: 提问 / 报告 bug
- GitHub Discussions: 想法 / 路线图讨论
- 邮件: 审核样题请发邮件给 maintainer

## 贡献者致谢

所有贡献者都会在 README 致谢 + 5+ PR 的成为 maintainer。
