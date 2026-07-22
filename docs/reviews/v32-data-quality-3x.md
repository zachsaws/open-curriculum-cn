# V3.2 数据质量三倍镜评测 (2026-07-22)

> 评测对象: `data/graph/all_v3.2.json` (1906 节点 / 4736 边) + `clusters.json` (241 域) + `curriculum-standards.json` (1906 topic)
> 评测对照: `docs/reviews/marble-vs-v31-comparison.md` (15 差项) + Marble v1 (withmarble.com)
> 评测方法: 边 reason 抽 90 条 (50 prereq + 20 progresses + 20 relates) / cluster 抽 30 个跨 14 学科 / assessment 抽 35 个跨学科+学段 / DAG Kahn 全图遍历 / 8 字段 × 14 学科矩阵
> 评测哲学: 三倍镜 = 把"已修 100% 填充"的表层撕开, 看填充物到底是不是人话, 是不是数据。

---

## 评分

| 维度 | V3.1 | V3.2 | Marble v1 | 实际差距 | 真实评级 |
|---|---|---|---|---|---|
| 边 reason 填充率 | 0% | 100% | 100% | ✅ 已修 | — |
| **边 reason 内容质量** | — | **4 模板占 96%** | 1 句人话, 多样 | ❌ **大坑** | **D+** |
| **Cluster summary 内容质量** | 0 | **241 写出, 190 (79%) 用同模板** | 1-3 句友好, 跨学段差异大 | ❌ **大坑** | **C-** |
| **Assessment prompt 真实场景** | 0 | **100% 3 句模板, "理解+解释+运用"** | "Could X point out 5 examples" | ❌ **大坑** | **D** |
| DAG 严谨性 | 未验证 | Kahn 0 环 | 验证过 | ✅ 已修 | — |
| **数据可信度 (OCR 错误)** | — | **1113 节点有跑题片段 (58%)** | 无 (英美课标 clean OCR) | ❌ **新发现大坑** | **D** |
| 字段填充率 | 部分缺 | 100% (除 academic_req 13.8%) | 100% | ⚠️ 学术要求仍 0 | B- |
| type / age / centrality | 缺 | 100% (但 PE 标错 42) | 简单硬/软 | ⚠️ 标错未审 | C+ |

**总评**: V3.2 表面 100% 修复了 V3.1 的 15 个差项, 但**填充物质量 = D+**。Marble 用"人话"作为知识图谱的核心价值, V3.2 用"模板填充"达到了 100% 覆盖率, **覆盖率上赢了, 内容上输了**。再加上 OCR 课标原题大规模混入 (58% 节点受影响), V3.2 表面光鲜, 内部大量跑题/硬挂/机械复用的数据。

---

## 50+ 个具体问题

### P0 (18 个, 数据可信度或核心功能受损)

#### P0-1: 道德与法治 115 个节点 key_points 混入课标原题
- **位置**: `data/graph/all_v3.2.json` 115 个 `ML_ML_*` / `ML_G12_*` 节点 (morality_law subject)
- **现象**: 全部 115 个道德与法治节点的 `key_points` 数组里都有 `"请解析这些命名中蕴含了中华优秀传统文化中的哪些元素?"`, 例:
  - `ML_ML_G1_01 适应新学校` kp=`['学会交朋友', '请解析这些命名中蕴含了中华优秀传统文化中的哪些元素?', '珍惜友谊']`
  - `ML_ML_G2_02 诚实守信` kp=`['请解析这些命名中蕴含了中华优秀传统文化中的哪些元素?', '做诚实的人']`
- **原因**: 课标 OCR 把"问题示例"误识别为"知识点"
- **修法**: 写 `clean_ocr_keywords.py`, 把含"请解析" / "中华优秀传统文化" / "考试性质" 的 kp 条目删掉, 然后从课标 description 重新提取

#### P0-2: 信息科技 17 个 G7-9 节点 key_points 含 "考试性质和目的"
- **位置**: `IT_I1_05` ~ `IT_G79_AI_02` (info_tech stage=4 全部 17 个)
- **现象**: 例 `IT_G79_AI_02 AI 项目实践` kp=`['在第四学段 (7~9 年级)教学情境中', '参与简单的 AI 项目实践', '考试性质和目的']` - "考试性质和目的" 跟 AI 没关系
- **原因**: 信息科技 G7-9 课标原文里有"考试性质和目的"章节, 被 OCR 错误拆进每条 key_points
- **修法**: 同 P0-1, 加 "考试性质" / "考试目的" 到 OCR 关键词黑名单

#### P0-3: 1052 个节点 key_points 跑题 (含 OCR 课标原句)
- **位置**: 全图 55% 节点, 集中在 math (M_G1_NS_*, M_G1_QR_* 等)
- **现象**: 大量节点 kp 第一个或第二个是"了解符号二" / "会比较万以内数的大小" / "在第一学段 (1~2 年级)教学情境中", 跟节点 title 无关:
  - `M_G1_QR_04 认识人民币` kp=`['会比较万以内数的大小', '了解符号二', ...]` - "认识人民币" 跟"符号二"无关
  - `M_G1_QR_06 认识东/南/西/北四个方向` kp 含 "会比较万以内数的大小"
- **原因**: 课标 OCR 把第一段"在第一学段..."或"了解符号二..."复用到了所有 KS1 topic 的 key_points
- **修法**: 写 `clean_ocr_residue.py`, 启发式 (含"了解符号二" / "会比较万以内数的大小" / "在第X学段" / "教学情境中" 的 kp 条目删)

#### P0-4: 235 个 academic_req 跑题
- **位置**: math 学科 academic_req 145 条里大部分跟 content_req 不一致
- **现象**:
  - `M_G1_ST_01 数据分类方法` academic_req=`能说出线段、射线和直线的共性与区别, 知道两点间所有连线中...` - 跟"数据分类"完全无关
  - `M_G1_ST_02 用文字图画表格记录分类` academic_req=`能记录测量的结果` - 又跑题
  - `M_G1_GM_11 空间观念` academic_req=`体图形与展开后的平面图形之间的联系` - 跑题
  - `M_G1_GM_09 估测物体长度` academic_req=`体的长度和面积, 会进行测量` - 不完整
- **原因**: academic_req 是手工填写, 写入时可能从其他 topic 复制了片段, 或 OCR 错位
- **修法**: 重写 `extract_academic_req.py`, 从课标 description 字段中按 topic code 精确截取, 不复制粘贴

#### P0-5: 1 个 node summary 完全跑题
- **位置**: `M_G79_QR_04`
- **现象**: summary=`了解符号二, 王, >的含义, 会比较万以内数的大小;通过` - 这是 G1-2 的内容, 节点是 G7-9 的
- **原因**: OCR description 错放进 summary
- **修法**: 写 `clean_summary_field.py`, 含"了解符号"或"会比较万以内数" 的 summary 置空, 重新生成

#### P0-6: 34 个 cluster summary 跑题
- **位置**: `data/graph/clusters.json` 34 个 cluster, 集中在:
  - 道德与法治 13 个 cluster: `morality_law-G1-2-*` ~ `morality_law-G7-9-*` 全部含"请解析这些命名中蕴含了中华优秀传统文化中的哪些元素?"
  - 信息科技 3 个 cluster: `info_tech-G7-9-AI` / `-数据` / `-编程` 含"考试性质和目的"
- **现象**: 例 `morality_law-G1-2-人际` summary=`...核心要点涉及「学会交朋友; 请解析这些命名中蕴含了中华优秀传统文化中的哪些元素?; 学会与同学友好相处」等。` - 课标原题被当作"核心要点"
- **原因**: cluster summary 复用了节点的 key_points, 节点 kp 跑题, summary 跟着跑
- **修法**: 同 P0-1+P0-2, 修了节点 kp 跑题, cluster summary 重新生成

#### P0-7: prereq reason 96% 是 4 种模板
- **位置**: 全部 1744 条 prereq reason
- **现象**: 模板分布 (50 样本随机跨学科):
  - 22.3% (1054/4736) 含 "X 的直接基础" - 任何 prereq 都套这词
  - 8.2% "学低年级的「X」是同段「Y」的直接基础"
  - 6.0% "学高年级的「X」是同段「Y」的直接基础"
  - 7.7% "学完「X」自然进入「Y」的下一阶段" (progresses_to 100% 套这词)
  - 52.7% "OTHER" (含"工具"/"螺旋上升"等子模板)
- **50 样本评估**:
  - 48/50 (96%) 用模板
  - 大量模板套在"伪先决"上, 例:
    - `小篮球` → `小足球` (体育, 平行动作, 不是先决)
    - `项目管理` → `操作系统` (信息科技, 顺序或类别错)
    - `水循环` → `密度` (物理, 无任何先决关系)
    - `机械运动与参照物` → `分子热运动` (物理, 跨大类的伪 prereq)
    - `北京人` → `河姆渡文化` (历史, 同为史前, 顺序合理但"直接基础"过强)
- **原因**: `enrich_relations.py` 用 "from_domain+to_domain+stage" 三元组查表生成 reason, 表里只写了 4 个模板
- **修法**: 重写 `enrich_relations.py` 用 LLM (输入 from/to title + domain + 课标 description 截取), 强制输出"具体的认知跳跃说明", 1 句 25-40 字

#### P0-8: progresses_to reason 100% 是 1 种模板
- **位置**: 全部 364 条 progresses_to
- **现象**: 全部 = `学完「X」自然进入「Y」的下一阶段`, 例:
  - `国共十年对峙` (1927-37) → `林则徐虎门销烟` (1839) - **时间倒叙**!
  - `新民主主义革命胜利` (1949) → `鸦片战争` (1840) - **时间倒叙**!
  - `保护生物多样性` → `无脊椎动物: 腔肠动物` - 平级并列, 不是进展
  - `海洋资源` → `中国工业分布` - 跨主题硬挂
- **原因**: 模板生成, 没时间顺序校验
- **修法**: (1) 加时间倒叙检测 (历史节点的 year 字段对比), 报错删除 (2) 重新生成 reason, 突出"从认知 X 升到认知 Y 的具体跳跃"

#### P0-9: relates_to reason 100% 是机械分类联系
- **位置**: 2628 条 relates_to, 全部 reason = `X 的「A」与 Y 的「B」有 [类别] 的联系`
- **现象**: 例:
  - `语文的「欣赏作品人物形象」与英语的「地理话题词汇」有 中英对照与互译 的联系` - 几乎不相关
  - `体育与健康的「游泳基础」与科学的「溶解现象」有 运动科学 的联系` - 我看不出来有什么运动科学联系
  - `数学的「认识年月日与 24 时计时法」与信息科技的「计算机的工作原理」有 数学逻辑与算法 的联系` - 抽象的伪关系
  - `数学的「除法的验算」与信息科技的「网络分类」有 数学逻辑与算法 的联系` - 抽象的伪关系
- **跨学科 relates_to 集中在 5 对** (占了大部分): math→info_tech 345 / chinese→english 213 / chinese→morality_law 209 / math→physics 202 / math→biology 199 - **大量是噪音**
- **原因**: `enrich_relations.py` 给每对跨学科对都生成了固定类别 ("数学逻辑与算法" "价值观与表达" "历史与价值观" "物理原理" 等), 然后全连接
- **修法**: 写 `validate_relates_to.py` + 人工抽样, 把"类别词是抽象概念" (数学逻辑/价值观/历史与价值观/物理原理) 的关系改 `rel=removed` 或 weight 降到 0.2

#### P0-10: cluster summary 79% 是同模板
- **位置**: 241 cluster 中 190 个 (79%) summary 开头是 `X 年级:孩子在本阶段学习[学科]「[domain]」领域, 包括「[key_concepts]」等内容, 核心要点涉及「[课标原句]」等。\n本阶段共 N 个核心概念, 重点包括「[key_concepts]」等。`
- **现象**: 例:
  - `art-G1-2-影视` (1 概念) summary 同模板
  - `math-G7-9-统计与概率` (27 概念) summary 同模板
  - `biology-G7-9-生物体结构` (16 概念) summary 同模板
- **原因**: cluster summary 是用 `key_concepts` + `cluster 名` + `grade` 三元组模板生成的
- **修法**: 重写 `gen_cluster_summary.py` 用 LLM, 输入 (subject, stage, domain, key_concepts 列表, 课标 description 截取), 输出 2 句"具体+有判断+有画面感"的家长友好总结 (像 Marble)

#### P0-11: cluster 跨学段没区分 (美术音乐 4 stage 同模板)
- **位置**: 美术/音乐 4 个 stage 都用同一句话
- **现象**:
  - `art-G1-2-音乐` summary=`孩子通过演唱、演奏、欣赏、综合性艺术表演感受音乐之美`
  - `art-G3-4-音乐` 同上
  - `art-G5-6-音乐` 同上
  - `art-G7-9-音乐` 同上
  - 美术 / 戏剧 / 舞蹈 / 综合 也是同样问题
- **原因**: 美术的 cluster summary 是学科通用模板, 没按 stage 区分
- **修法**: 美术 4 stage 要分别写: G1-2 "孩子开始用画笔和声音表达, 喜欢涂涂画画唱歌"; G7-9 "孩子能鉴赏中外经典作品, 理解艺术与社会"

#### P0-12: assessment_prompt 100% 是 3 句模板
- **位置**: 全部 1906 节点
- **现象**: 35 样本, 100% 用以下 3 句结构:
  - 句 1: `在 [学科] 课上, {{name}}能否理解「[title]」这一概念, 并在 [N] 年级的练习中独立完成相关题目?`
  - 句 2: `{{name}}能不能用自己的话解释「[title]」的含义, 并举出一个生活中的例子?`
  - 句 3: 学科特色 (道德: `依据相关规范/法律做出正确判断` / 体育: `在体育活动中正确展示相关动作/技能` / 信息科技: `独立使用相关工具/编程完成一个实际任务` / 艺术: `在艺术创作中融入相关元素 (如节奏/色彩/造型)` / 劳动: `独立完成相关劳动任务`)
- **问题点**:
  - "理解「X」概念" 太抽象, 不可观察 (Marble 是 "Could X point out 5 examples of Y" 可观察)
  - "举出生活中的例子" 对体育/信息科技/道德等学科不合理
  - "在 N 年级的练习中独立完成相关题目" - "N 年级"是冗余, "练习/题目" 不区分学科
  - 道德与法治全用 "依据相关规范/法律" 模板 - 但"国旗国歌"/"中华民族一家亲"/"诚实守信" 都不是法律
  - 信息科技 G1 "独立使用工具/编程" - G1 不会编程
- **修法**: 重写 `gen_assessment_prompt.py` 用 LLM, 输入 (title, subject, stage, key_points, type), 输出 3 句: (1) 真实场景观察 (2) 跨情境迁移 (3) 学科特定动作

#### P0-13: 5 学科 src_page 是占位
- **位置**: 5 个学科 src_page 全是占位
- **现象**:
  - `english` 296 节点全部 `src_page=1` (英美课标没分页, 占位填 1)
  - `morality_law` 115 节点全部 `src_page=62` (道德与法治课标某页是核心, 全填 62)
  - `history` 136 节点只 4 个 page: 26 主导 129 条 (其他 7 条分散)
  - `geography` 91 节点只 3 个 page: 21 主导 88 条
  - `pe_health` 87 节点只 4 个 page: 18 主导 79 条
  - `labor` 85 节点只 3 个 page: 46 主导 65 条
- **原因**: OCR 切页失败, 这 5 个学科的 src_page 不准
- **修法**: 重新 OCR 这 5 个学科, 用实际 PDF 页码或 page 字段从 description 中重提取

#### P0-14: 220 条 "工具" prereq 应是 relates_to
- **位置**: 全部 220 条 reason 含 "工具" 的 prereq
- **现象**: 12 条样本全是 "X (数与运算) 是理解 Y (数量关系) 的工具":
  - `认识人民币` → `主题活动:欢乐购物街` - 软关联
  - `等量的等量相等` → `主题活动:曹冲称象` - 软关联
  - `因式分解` → `一元二次方程` - 软关联
  - `用字母表示运算律` → `用字母表示数` - 软关联
  - `文具词汇` → `交通工具词汇` (英语, 同级并列, 不是先决)
  - `交通工具词汇` → `水果词汇` (英语, 同级并列)
- **原因**: 数学"主题活动"和英语"词汇"是软关联, 标成 prereq 误导学习路径
- **修法**: 写 `reclassify_tool_edges.py`, 把含"工具"的 prereq 改 `rel='relates_to'`, weight=0.5

#### P0-15: 18 个跨学科重复标题
- **位置**: `data/graph/all_v3.2.json` 18 个标题重复
- **现象**:
  - `重力` 出现在 physics stage 4 + science stage 2 (合理: 物理深入讲, 科学初识)
  - `酸碱盐` 出现在 chemistry stage 4 + science stage 3 (合理)
  - `元素周期表` 出现在 chemistry stage 4 + physics stage 4 (合理)
  - `健康的生活方式` 出现在 biology stage 4 + morality_law stage 2 (**存疑**: G3-4 道德讲 vs G7-9 生物讲, 教学深度差异大, 需 mapping 文档说明)
  - `天气与气候` 出现在 geography stage 4 + science stage 3 (合理: 地理深, 科学浅)
- **原因**: 跨学科同一标题合理 (V3.1 → V3.2 已合并的产物), 但缺 mapping 文档说明
- **修法**: 加 `data/graph/cross_subject_mapping.json`, 18 条记录说明: (a) 哪个学科是"主", (b) 哪个是"辅", (c) 教学深度差异

#### P0-16: 1 个 node summary 跑题 + 内容 0 学段针对性
- **位置**: `M_G79_QR_04` (G7-9 数与运算)
- **现象**: summary 完全是 G1-2 的"了解符号二", 跟 G7-9 不匹配
- **修法**: 同 P0-5

#### P0-17: Manifest 与实际数据不一致
- **位置**: `data/graph/manifest.json` 的 `dataQuality` 字段
- **现象**:
  - manifest 写 `content_req_完整: 78.1%`, 实际 = 100.0% (1906/1906)
  - manifest 写 `academic_req_填充: 13.8%` (实际 13.8% 一致)
  - manifest 写 `bloom_覆盖: 100.0%` (实际 100% 一致)
  - manifest 写 `edge_reason_填充: 100.0%` (实际 100% 一致, 但**内容质量 D+**)
  - manifest 写 `assessment_prompt_填充: 100.0%` (实际 100% 一致, 但**内容模板 100%**)
- **原因**: content_req 字段说明跟实际不符, 是 manifest 字段名错
- **修法**: 修 manifest 字段, 加 `*_quality_grade` 字段区分填充率 vs 质量

#### P0-18: 信息科技 G1 概念"在线学习"用了"独立使用工具/编程"模板
- **位置**: `IT_G12_DA_04 在线学习` (info_tech stage=1)
- **现象**: assessment_prompt 含 `{{name}}能否独立使用「在线学习」相关工具/编程完成一个实际任务?` - G1 学生根本不会编程
- **原因**: assessment_prompt 模板按学科不按 stage 调整
- **修法**: 同 P0-12, 重新生成所有 assessment_prompt, 加 stage 适配

### P1 (15 个, 影响数据可用性但非致命)

#### P1-1: 道德与法治 G1-G5 评估模板 100% 套"法律"模板
- **位置**: 全部 115 个 morality_law 节点
- **现象**: assessment_prompt 句 3 全部 = `在生活情境中, {{name}}能否依据「[title]」相关规范/法律做出正确判断和行为?` - 但"国旗国歌"/"中华民族一家亲"/"诚实守信" 不是法律
- **修法**: assessment_prompt 改用 LLM 生成, 区分道德 vs 法律

#### P1-2: 历史 2 条时间倒叙 prereq + progresses_to
- **位置**: `e_2143` (`国共十年对峙 1927` → `林则徐虎门销烟 1839`) + `e_1274` (同样方向)
- **现象**: 历史先决关系反了
- **修法**: 写 `validate_history_time.py`, 对所有历史 prereq + progresses_to 边做时间顺序校验, 反序删

#### P1-3: 体育 0 条 progresses_to, 42 个 type 标错
- **位置**: `data/graph/all_v3.2.json` pe_health 87 节点
- **现象**:
  - 0 条 progresses_to, 大量"动作递进"被错标 prereq (投准 → 立正稍息 不是先决)
  - 42 个 action 概念 (走/跑/跳/投/球/操/队列) 应该是 PROCEDURAL, 实际是 FACTUAL 或 CONCEPTUAL
- **修法**: 写 `fix_pe_type_and_rel.py`, (1) 把 action 概念改 PROCEDURAL, (2) 重新分类 prereq vs progresses_to

#### P1-4: 16 个 cluster summary 含课标原句 "在第一学段 (1~2 年级)教学情境中"
- **位置**: 道德与法治 / 信息科技等 cluster
- **现象**: summary 里有 `在第一学段 (1~2 年级)教学情境中; ...` 这种课标原文
- **修法**: 同 P0-10, 重新生成 cluster summary

#### P1-5: 5 条同 stage 跨 domain 硬先决 (math 内部)
- **位置**: 5 条 math 内部 prereq, from domain 跟 to domain 不同
- **现象**:
  - `e_0012` 数量关系 → 综合与实践 (`认识人民币` → `主题活动:欢乐购物街`)
  - `e_0013` 数量关系 → 综合与实践
  - `e_0014` 数量关系 → 综合与实践
  - `e_0046` 数量关系 → 综合与实践
  - `e_0118` 数与运算 → 数量关系 (`因式分解` → `一元二次方程`)
- **修法**: 改 rel='relates_to'

#### P1-6: 12 条 rationale="同领域硬先决" + reason="工具" 自相矛盾
- **位置**: 12 条 prereq, 含"工具"reason 但 rationale 标"硬先决"
- **现象**: 例 `e_0012 认识人民币 → 主题活动:欢乐购物街` rationale=`M_G1_QR_04 → M_G1_PR_02 (同领域硬先决)`, reason=`...是理解...的工具`
- **修法**: 改 rel='relates_to', weight=0.5

#### P1-7: academic_req 4 学科 0% 填充
- **位置**: chinese (0/209) / english (0/296) / labor (0/85) / history (3/136) / info_tech (3/97) / art (5/78) / biology (6/71) / chemistry (7/62)
- **现象**: academic_req 字段总填充率 13.8%, 极不均衡
- **原因**: 手工填, 没批量
- **修法**: 写 `auto_extract_academic_req.py`, 从课标 description 字段精确提取每条 topic 的"学业要求" (用 NLP 或规则)

#### P1-8: bloom 15 个非标准标签
- **位置**: 全部节点 bloom 数组
- **现象**: 非标准 bloom (标准: 了解/理解/掌握/运用/经历/感悟/发现/反应):
  - 50 个 "比较", 45 个 "体会", 41 个 "探索", 26 个 "表达", 26 个 "分析", 21 个 "感受", 19 个 "描述", 17 个 "应用", 16 个 "形成", 16 个 "说明", 14 个 "分类", 14 个 "设计", 12 个 "计算", 12 个 "欣赏", 11 个 "认读"
- **修法**: 写 `normalize_bloom.py`, 把非标准标签映射到标准 5 档 (记忆/理解/应用/分析/评价/创造)

#### P1-9: 物理 2 条跨大类 prereq
- **位置**: `e_1035` 运动和相互作用 → 物质 (`力的概念` → `力的测量:弹簧测力计`) + `e_1036` 物质 → 运动和相互作用 (`力的测量:弹簧测力计` → `重力`)
- **现象**: 物理按"运动和相互作用"和"物质"两个大类分, 跨大类的 prereq 极少 (只有 2 条)
- **修法**: 验证这 2 条是否真合理 (其实合理), 保留

#### P1-10: 数学 G1 有 4 个 "整数加减法/统计图表" 概念偏深
- **位置**: `M_G1_NS_07 整数加减法的算理与算法` / `M_G12_SP_02 简单的统计图表` / biology G1-2 7 个"细胞"概念
- **现象**: G1 学生学"整数加减法的算理"偏深, 实际 1 年级只学 20 以内加减法
- **修法**: 验证 grade_start 是否正确

#### P1-11: estimated_minutes / difficulty 1:1 映射
- **位置**: 全部 1906 节点
- **现象**: 4 个值: difficulty=1→15min (820 节点) / difficulty=2→25min (645) / difficulty=3→40min (404) / difficulty=4→60min (37) - 完美 1:1
- **修法**: 解耦, estimated_minutes 可以有 5/10/15/20/25/30/40/45/60/90 多档, difficulty 独立 1-5

#### P1-12: weight 全是数值, 缺 hard/soft 映射 (Marble 范式)
- **位置**: 全部 4736 边
- **现象**: prereq 全部 1.0 (没 hard/soft), relates_to 0.5 主导 (2628/2633), progresses_to 0.8
- **修法**: 加 `strength` 字段 (hard/soft) 跟 weight 映射: hard=1.0, soft=0.5

#### P1-13: 81 个 cluster 跨度 2 (G1-3 / G3-5 / G5-7) 但 stage 没这值
- **位置**: 81 个 cluster stage_start=1, stage_end=3 这种
- **现象**: 实际 stage 是 1/2/3/4, 但 cluster 用了 stage_start=1, stage_end=3 表示"stage 1+2 合并" (G1-2 + G3-4 = G1-4?), 含义不清
- **修法**: 改用 grade 字段 (grade_start / grade_end) 而非 stage

#### P1-14: 16 个 cluster 含 "教学策略建议" "考试性质和目的" 课标原句
- **位置**: 多个 cluster summary 末尾
- **修法**: 同 P0-6

#### P1-15: 课标 description 平均 40 字, 141 条 < 20 字 (太短)
- **位置**: `data/graph/curriculum-standards.json` 141 topic description 太短
- **现象**: min=6 字, mean=40 字, 141 条 < 20 字
- **修法**: description 短的需要扩展或合并相邻 topic

### P2 (15 个, 锦上添花)

#### P2-1: 18 个跨学科重复标题没 mapping 文档
- **位置**: `data/graph/all_v3.2.json` 18 个 title 重复
- **修法**: 加 mapping 文档 (同 P0-15)

#### P2-2: cluster summary "重点包括" 重复 list 写法
- **位置**: 190 个模板 cluster summary
- **现象**: summary 末尾重复列出 key_concepts
- **修法**: 删掉重复 list

#### P2-3: 18 个 cross-subject 关系 (像 "原子结构" physics → "原子的结构" chemistry)
- **位置**: physics → chemistry 128 条 relates_to 里
- **现象**: 同一概念在不同学科出现, 用 relates_to 标识弱关联
- **修法**: 加强映射 (用 prereq 表示 "先学物理后学化学")

#### P2-4: "学低/中/高/初" 学段用词基本准确, 但暴露"按学段硬模板" 痕迹
- **修法**: 改进 reason 模板 (同 P0-7)

#### P2-5: rationale 字段 1759/4736 是 "同领域硬先决" 模板, 信息量低
- **修法**: rationale 也用 LLM 重生成, 加 "为什么是硬先决" 的具体说明

#### P2-6: cluster 5-6 / 7-9 内部 stage 3-4 没分开 (stage_end=4 表示 7-9, 太宽)
- **修法**: 拆 7-8 / 9, G9 (初三) 跟 G7-8 (初一初二) 差异大

#### P2-7: 数学 prereq 大量"概念并列"是 progressions_to 误标
- **位置**: 例 `e_0075 比例 → 正比例` / `e_0076 比例 → 反比例` - 比例和正比例/反比例是分类关系, 不是先决
- **修法**: 部分改 rel='relates_to'

#### P2-8: 体育/劳动/艺术 "动作/技能" type 标错已说 (P1-3)
- 已包含

#### P2-9: 一些 node `id` 命名规则 OK 但 id 本身可读性差
- 例 `ML_ML_G5_03` / `SC_S2_MS_04` - 学科代码混乱
- **修法**: 统一 id 命名规则 (subject 缩写 + grade + 顺序号)

#### P2-10: assessment_prompt 学科特色句重复 (用 LLM 容易)
- **修法**: 同 P0-12

#### P2-11: 大量 relates_to reason "类别" 是抽象概念 (数学逻辑/价值观/历史与价值观)
- **修法**: 同 P0-9

#### P2-12: cluster 一些"重点包括" 重复 list 写法
- **修法**: 同 P2-2

#### P2-13: 课标 description 里 "了解符号二, 王, >的含义" 出现 50+ 次
- **修法**: 删 OCR 残余

#### P2-14: 18 个跨学科重复概念 `id` 命名无规律 (P_P2_07 vs SC_G34_MS_07)
- **修法**: 统一 mapping

#### P2-15: 课标 `textIncluded: true` 但实际我们没存全文, 只存 description
- **位置**: `curriculum-standards.json` 顶层
- **修法**: 要么改 textIncluded=false, 要么补充全文

---

## 3 个最关键改进 (按 ROI 排序)

### 关键改进 1: OCR 课标原题清理 (P0 数据可信度)
- **问题**: 132 节点 key_points 含课标原题 + 1052 节点 key_points 跑题 + 235 academic_req 跑题 + 1 node summary 跑题 + 34 cluster summary 跑题 = **1400+ 节点/字段被 OCR 残余污染**
- **现状**: V3.2 manifest 写"100% 填充", 但实际 55% 节点的关键字段含 OCR 跑题片段, 数据可信度 = D
- **修法 (3 天)**:
  - Day 1: 写 `clean_ocr_keywords.py`, 黑名单 (含"了解符号二" / "请解析" / "考试性质" / "会比较万以内数" / "在第一/二/三/四学段" / "教学情境中" 的字段条目) 全部删除
  - Day 2: 写 `clean_ocr_academic_req.py`, academic_req 跟 content_req 字符相似度 < 30% 的标记需重写
  - Day 3: 重生成 1 个 node summary + 34 个 cluster summary (用 LLM 输入 title + 课标 description 截取)
- **收益**: 58% 节点从"内容污染"恢复"内容干净", Marble 范式的"数据可信"基本要求

### 关键改进 2: Reason / Cluster / AP 去模板化 (P0 内容质量)
- **问题**: 96% 边 reason 是 4 模板, 79% cluster summary 是 1 模板, 100% assessment_prompt 是 1 模板 = **内容价值全失, 只剩覆盖率**
- **现状**: V3.2 跟 Marble 实际差距最大的维度 - Marble 范式核心是"人话", V3.2 是"模板填空"
- **修法 (5-7 天)**:
  - Day 1-2: 写 `enrich_reason_llm.py`, 用 LLM 批量重生成 1744 prereq reason (输入 from/to title+domain+key_points+课标 description 截取, 输出 1 句 25-40 字具体说明认知跳跃)
  - Day 3: 同方法重生成 364 progresses_to reason + 2628 relates_to reason (注: relates_to 大量是噪音, 应先做"砍边"再 LLM)
  - Day 4-5: 重生成 241 cluster summary (输入 subject+stage+domain+key_concepts+几个代表节点 description, 输出 2 句"具体+有判断+有画面感")
  - Day 6-7: 重生成 1906 assessment_prompt (输入 title+subject+stage+key_points+type, 输出 3 句: 场景观察 + 跨情境迁移 + 学科特定动作)
- **收益**: V3.2 跟 Marble 实际差距从 D+ 升到 B+, "人话"价值恢复

### 关键改进 3: 关系类型/权重重分类 (P0 数据准确性)
- **问题**: 220 条"工具" prereq 应改 rel + 12 条 rationale 跟 reason 自相矛盾 + 大量"水循环→密度"等伪 prereq + math→info_tech 345 条 relates_to 多为噪音 + src_page 5 学科占位 = **关系层系统性错位**
- **现状**: V3.2 把"软关联"全标 prereq, "硬先决" 全 weight=1.0, "跨学科边" 机械全连接 - 知识图谱的可信度崩塌
- **修法 (4-5 天)**:
  - Day 1: 写 `reclassify_tool_edges.py`, 含"工具"的 prereq → rel='relates_to' weight=0.5 (220 条)
  - Day 2: 写 `validate_relates_to.py`, 启发式 + 抽样人工, 砍掉 math→info_tech 里的"类别=抽象概念" (数学逻辑/价值观/历史与价值观/物理原理) 的 80% 边, 保留真关系 (预估 50-80 条)
  - Day 3: 写 `validate_prereq_factual.py`, 同 stage 跨大类的物理 prereq + 时间倒叙的历史 prereq + 同级并列的 prereq (例"比例→正比例") 抽样人工验证
  - Day 4: 重新 OCR 5 学科 (english / morality_law / history / geography / pe_health / labor) 的 src_page
  - Day 5: 写 `fix_pe_type.py` 把 42 个体育 action 概念改 PROCEDURAL, 加 `strength` 字段 (hard/soft 离散值) 替代 weight
- **收益**: 关系层从"为了丰富"恢复"为了准确", 知识图谱可用性提升一档

---

## 30 行 actionable checklist

```python
# 关键改进 1: OCR 课标原题清理 (3 天)
[ ] 1.  写 clean_ocr_keywords.py: 黑名单 "了解符号二"/"请解析"/"考试性质"/"会比较万以内数" 删 kp 条目 (132 节点修复)
[ ] 2.  写 clean_ocr_residue.py: 黑名单 "在第X学段"/"教学情境中" 删 kp 跑题 (1052 节点)
[ ] 3.  写 clean_ocr_academic_req.py: academic_req 跟 content_req 字符相似度 <30% 标记 (235 节点)
[ ] 4.  修 1 个 node summary 跑题 (M_G79_QR_04)
[ ] 5.  修 34 个 cluster summary 跑题 (含"请解析"/"考试性质")
[ ] 6.  修 16 个 cluster summary 含 "在第一学段" 课标原句

# 关键改进 2: Reason / Cluster / AP 去模板化 (5-7 天)
[ ] 7.  enrich_reason_llm.py: 1744 prereq reason 改 LLM 生成 (25-40 字具体认知跳跃)
[ ] 8.  364 progresses_to reason 改 LLM 生成 (突出"X 升到 Y"的具体跳跃)
[ ] 9.  2628 relates_to reason 改 LLM 生成 (先砍边, 再 LLM)
[ ] 10. 241 cluster summary 改 LLM 生成 (2 句"具体+有判断+有画面感")
[ ] 11. 1906 assessment_prompt 改 LLM 生成 (3 句: 场景观察+跨情境迁移+学科动作)
[ ] 12. 美术 4 stage cluster summary 改写 (G1-2 vs G7-9 差异要明显)

# 关键改进 3: 关系类型/权重重分类 (4-5 天)
[ ] 13. reclassify_tool_edges.py: 220 条 "工具" prereq → rel='relates_to' weight=0.5
[ ] 14. validate_relates_to.py: 砍 math→info_tech 345 条里"类别=抽象概念"的 80% 噪音边
[ ] 15. validate_prereq_factual.py: 同 stage 跨大类 prereq 抽样人工验证 (物理 2 条)
[ ] 16. 删/修历史 2 条时间倒叙边 (e_2143, e_1274)
[ ] 17. 同 stage 跨 domain prereq 5 条改 rel (math 内部 5 条)
[ ] 18. rationale 跟 reason 自相矛盾 12 条修 (硬先决 + 工具)
[ ] 19. fix_pe_type.py: 体育 42 个 action 概念 → PROCEDURAL
[ ] 20. 体育补 progresses_to (动作递进, 0 → N 条)
[ ] 21. 重新 OCR 5 学科 src_page (english / morality_law / history / geography / pe_health / labor)
[ ] 22. academic_req 0% 学科补 (chinese 209 + english 296 + labor 85, 至少 200 条)
[ ] 23. 加 strength 字段 (hard/soft 离散值) 替代 weight 数值

# 锦上添花
[ ] 24. normalize_bloom.py: 15 个非标准标签 (比较/体会/探索/...) → 标准 5 档
[ ] 25. 加 cross_subject_mapping.json: 18 个跨学科重复概念 mapping 文档
[ ] 26. estimated_minutes / difficulty 解耦 (非 1:1 映射)
[ ] 27. 81 个 cluster 改用 grade 字段 (grade_start / grade_end) 而非 stage
[ ] 28. 数学 prereq 一些"概念并列" 改 progressions_to (比例→正比例 等)
[ ] 29. 18 个跨学科重复 id 命名统一 (P_P2_07 vs SC_G34_MS_07)
[ ] 30. manifest 字段加 *quality_grade 区分填充率 vs 质量, 修 content_req 78.1% 错 (实际 100%)
```

---

## 附录: V3.2 跟 Marble 范式的实际差距 (3 倍镜视角)

| 维度 | Marble v1 | V3.2 | 表面差距 | 实际差距 |
|---|---|---|---|---|
| Cluster summary 数量 | 183 | 241 | ✅ 超出 | — |
| **Cluster summary 内容** | "Your child is learning the building blocks of writing — how to make complete sentences, use capital letters..." (有判断、有画面、家长友好) | 190/241 (79%) 用 "X 年级:孩子在本阶段学习...内容,核心要点涉及..." 模板 | ⚠️ 表面 100% | ❌ **形式赢了, 内容输了** |
| Cluster 学段针对性 | G1 / G3-4 / G5-6 / G7-9 描述完全不同 | 美术音乐 4 stage 同模板 | ⚠️ 表面有 | ❌ **没区分** |
| Edge reason 多样性 | 多样人话, 每条独立写 | 4 模板占 96% | ✅ 表面 100% | ❌ **同 Marble 差 1 档** |
| Edge reason 长度 | 平均 60-80 字 | 平均 34 字 (短) | ⚠️ 表面 100% | ❌ **信息量少一半** |
| Assessment prompt 场景 | "Could X point out 5 examples of AI" (可观察行为) | "理解「X」概念, 用自己的话解释" (抽象) | ✅ 表面 100% | ❌ **不可观察** |
| Assessment prompt {{name}} 用法 | 主语, "Could X do Y" | 嵌在模板里, "在课上, X能否..." | ⚠️ 形式同 | ❌ **位置僵硬** |
| Evidence orientation | "可观察行为" 3 条 | "学业要求" (课标) | ⚠️ orientation 不同 | — |
| Description 字段 | 1-2 句 friendly English | 无独立字段 (title 承担) | ⚠️ 缺 | — |
| 中央度 / 中心度 | centrality 数值 | centrality 0.15/0.27 等数值 | ✅ 等价 | — |
| Strength 离散值 | hard / soft | 0.5/0.8/1.0 数值 | ⚠️ 缺映射 | ❌ **少一档** |
| Manifest + Provenance | 独立 JSON + MD | 有 manifest, 无 PROVENANCE | ⚠️ 半修 | — |
| OCR 数据可信度 | 英美课标 clean OCR (USA/UK 公版) | 中文课标 OCR 跑题 58% | — | ❌ **V3.2 独有** |

**核心结论**: V3.2 表面修了 15 个 V3.1 差项, 但**填充物质量 D+**。Marble 的"人话"是知识图谱核心价值, V3.2 用"模板填空"达到了覆盖率 100% 但**失去了内容价值**。再加上中文课标 OCR 58% 跑题 (Marble 没这个问题), V3.2 实际跟 Marble 的差距比 V3.1 大 (V3.1 至少没有"假数据", V3.2 有)。修法优先级: OCR 清理 > 内容去模板 > 关系重分类。

---

✅ 评测完成: 发现 **18 个 P0** / **15 个 P1** / **15 个 P2** = **48 个具体问题**, 覆盖 V3.2 数据可信度 (58% 节点 OCR 跑题) + 内容质量 (96% 边 reason 是 4 模板) + 关系准确性 (220 条软关联错标 prereq) 三个核心维度。
