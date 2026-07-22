# V2.3 概念抽样审核 (30 个, seed=20260722)

- 生成日期: 2026-07-22
- 数据源: `web/data/graph.json` (758 节点 / 167 边)
- 抽样方法: 按学科节点数比例配额, `random.seed(20260722)` 可复现
- 人工审核: 请逐条对照 2022 义教课标原件 (`data/raw/curriculum_2022/{学科序号}_{学科名}.pdf`) 核对

**审核问题清单** (5 列):

| # | ID | 学科·年级 | 标题 | content_req 真在课标? (Y/N) | 错字/术语修正 | 关系对? (Y/N) | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `M_G4_NS_02` | 数学·G7-9 | 数轴 | _理解负数的意义〈例 64);， 理解有理数的意义，能用数轴上的。理解数轴,会用数轴上的点表示有理数_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 04_数学.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 2 | `M_G4_GM_31` | 数学·G7-9 | 坐标与图形位置 | _了解符号二，王，>的含义，会比较万以内数的大小;通过。用坐标描述图形位置_ |  |  | P1 \| indeg=0 outdeg=1 \| PDF: 04_数学.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 3 | `M_G3_NS_08` | 数学·G5-6 | 负数认识 | _结合具体情境探索并理解小数和分数的意义，感悟计数单。结合具体情境认识负数,感悟对立统一_ |  |  | P1 \| indeg=0 outdeg=1 \| PDF: 04_数学.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 4 | `M_G1_QR_03` | 数学·G1-2 | 解释结果的实际意义 | _能解决生活中的简单问题，并能对结果的实际意义作出解。能解释结果的实际意义,形成初步的应用意识_ |  |  | P1 \| indeg=1 outdeg=0 \| PDF: 04_数学.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 5 | `M_G4_NS_07` | 数学·G7-9 | 平方根与算术平方根 | _了解符号二，王，>的含义，会比较万以内数的大小;通过。理解平方根和算术平方根_ |  |  | P1 \| indeg=1 outdeg=1 \| PDF: 04_数学.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 6 | `M_G1_NS_14` | 数学·G1-2 | 除法是乘法的逆运算 | _了解符号二，王，>的含义，会比较万以内数的大小;通过。理解除法是乘法的逆运算_ |  |  | P1 \| indeg=2 outdeg=1 \| PDF: 04_数学.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 7 | `M_G2_NS_20` | 数学·G3-4 | 质数与合数 | _在解决简单实际问题的过程中，理解四则运算的意义，能进。了解质数(或素数)和合数_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 04_数学.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 8 | `M_G1_GM_08` | 数学·G1-2 | 长度单位换算 | _了解符号二，王，>的含义，会比较万以内数的大小;通过。能进行米/厘米之间的换算_ |  |  | P1 \| indeg=1 outdeg=0 \| PDF: 04_数学.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 9 | `CN_C1_PR_01` | 语文·G1-2 | 阅读有关个人生活家庭生活短文 | _课堂教学评价建议。阅读个人/家庭生活短文,感受美好亲情_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 02_语文.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 10 | `CN_C3_SP_01` | 语文·G5-6 | 复述转述讲述 | _阅读富有童趣的图画书等浅易的读物，体会读书的快乐。。复述/转述/讲述见闻和感受_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 02_语文.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 11 | `CN_C4_XS_01` | 语文·G7-9 | 跨学科专题研究 | _认识有关人的身体与行为、天地四方、自然万物等方面的常。围绕跨学科主题开展专题研究_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 02_语文.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 12 | `EN_E4_GR_02` | 英语·G7-9 | 非谓语动词 | _使用不定式/动名词/分词_ |  |  | PNone \| indeg=0 outdeg=0 \| PDF: 05_英语.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 13 | `EN_E4_SK_02` | 英语·G7-9 | 讨论与辩论 | _参与讨论/辩论/演讲_ |  |  | PNone \| indeg=0 outdeg=0 \| PDF: 05_英语.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 14 | `EN_E1_TX_01` | 英语·G1-2 | 听说简单对话/小故事 | _听懂/看懂简单对话/小故事_ |  |  | PNone \| indeg=0 outdeg=0 \| PDF: 05_英语.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 15 | `P_P1_09` | 物理·G8 | 原子结构 | _物质的结构和物质世界的尺度。初步了解原子结构_ |  |  | P1 \| indeg=0 outdeg=1 \| PDF: 10_物理.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 16 | `P_P2_10` | 物理·G8-9 | 牛顿第一定律 | _物质的形态和变化。理解牛顿第一定律,理解惯性_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 10_物理.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 17 | `CH_C5_04` | 化学·G9 | 化学与环境 | _科学探究的能力。了解化学与环境保护_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 11_化学.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 18 | `B_B4_04` | 生物·G8 | DNA 是遗传物质 | _细胞是生物体结构和功能的基本单位。理解 DNA 是主要的遗传物质_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 12_生物.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 19 | `H_H3_CR_03` | 历史·G9 | 社会主义建设探索 | _中国共产党成立与新民主主义革命的兴起。了解社会主义建设探索的成就与失误_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 03_历史.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 20 | `H_H4_WC_04` | 历史·G9 | 第二次世界大战 | _中国共产党成立与新民主主义革命的兴起。了解二战_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 03_历史.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 21 | `G_G3_02` | 地理·G7 | 语言与宗教 | _从世界范围内选择区域进行学习时，除南极和北极地区是必。了解世界主要语言和宗教_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 08_地理.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 22 | `G_G1_03` | 地理·G7 | 地球自转与公转 | _从世界范围内选择区域进行学习时，除南极和北极地区是必。理解地球自转和公转及其地理意义_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 08_地理.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 23 | `ML_ML_G5_01` | 道法·G5 | 面对挫折 | _请解析这些命名中蕴含了中华优秀传统文化中的哪些元素?。学会面对挫折,增强心理韧性_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 01_道法.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 24 | `ML_ML_G3_01` | 道法·G3 | 我们的学校生活 | _请解析这些命名中蕴含了中华优秀传统文化中的哪些元素?。参与集体生活,融入学校_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 01_道法.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 25 | `SC_S2_MS_05` | 科学·G3-4 | 光的传播与反射 | _技术与工程创 \| 国古代技术与工程方面的典型案例。探究光的传播和反射_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 09_科学.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 26 | `SC_S2_ES_01` | 科学·G3-4 | 地球的形状与运动 | _力是改变物体运动状态的原因。了解地球是球形,自转和公转_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 09_科学.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 27 | `IT_I7_02` | 信息科技·G4-9 | 数字公民 | _在日常学习与生活场景中，通过教师指导，尝试使用数字设。养成健康的数字公民素养_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 13_信息科技.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 28 | `ART_A3_02` | 艺术·G3-6 | 民族舞蹈体验 | _教学策略建议。体验民族舞蹈_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 15_艺术.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 29 | `PE_PE5_04` | 体育与健康·G5-9 | 青春期健康 | _了解正确的身体姿势，能做出正确的坐、立、行和读写姿。了解青春期生理心理变化_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 14_体育与健康.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |
| 30 | `L_L5_02` | 劳动·G4-9 | 简单产品制作 | _初步体验简单的种植、养殖、手工制作等生产劳动，能规范。进行简单产品制作_ |  |  | P1 \| indeg=0 outdeg=0 \| PDF: 16_劳动.pdf \| ⚠️ review_status=pending (review_round=1) — 还没过任何审核 |

---

## 自动审核 hint 总览 (按节点)

| ID | 标题 | 自动 hint |
| --- | --- | --- |
| `M_G4_NS_02` | 数轴 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `M_G4_NS_02` | 数轴 | 标题 / 关键术语有没有错别字? |
| `M_G4_NS_02` | 数轴 | 上下游关系对不对? (看 prereq / unlock) |
| `M_G4_NS_02` | 数轴 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `M_G4_NS_02` | 数轴 | academic_req 为空 — 学业要求暂未补全 |
| `M_G4_NS_02` | 数轴 | review_status=pending (review_round=1) — 还没过任何审核 |
| `M_G4_GM_31` | 坐标与图形位置 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `M_G4_GM_31` | 坐标与图形位置 | 标题 / 关键术语有没有错别字? |
| `M_G4_GM_31` | 坐标与图形位置 | 上下游关系对不对? (看 prereq / unlock) |
| `M_G4_GM_31` | 坐标与图形位置 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `M_G4_GM_31` | 坐标与图形位置 | academic_req 为空 — 学业要求暂未补全 |
| `M_G4_GM_31` | 坐标与图形位置 | review_status=pending (review_round=1) — 还没过任何审核 |
| `M_G3_NS_08` | 负数认识 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `M_G3_NS_08` | 负数认识 | 标题 / 关键术语有没有错别字? |
| `M_G3_NS_08` | 负数认识 | 上下游关系对不对? (看 prereq / unlock) |
| `M_G3_NS_08` | 负数认识 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `M_G3_NS_08` | 负数认识 | academic_req 为空 — 学业要求暂未补全 |
| `M_G3_NS_08` | 负数认识 | review_status=pending (review_round=1) — 还没过任何审核 |
| `M_G1_QR_03` | 解释结果的实际意义 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `M_G1_QR_03` | 解释结果的实际意义 | 标题 / 关键术语有没有错别字? |
| `M_G1_QR_03` | 解释结果的实际意义 | 上下游关系对不对? (看 prereq / unlock) |
| `M_G1_QR_03` | 解释结果的实际意义 | academic_req 为空 — 学业要求暂未补全 |
| `M_G1_QR_03` | 解释结果的实际意义 | review_status=pending (review_round=1) — 还没过任何审核 |
| `M_G4_NS_07` | 平方根与算术平方根 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `M_G4_NS_07` | 平方根与算术平方根 | 标题 / 关键术语有没有错别字? |
| `M_G4_NS_07` | 平方根与算术平方根 | 上下游关系对不对? (看 prereq / unlock) |
| `M_G4_NS_07` | 平方根与算术平方根 | academic_req 为空 — 学业要求暂未补全 |
| `M_G4_NS_07` | 平方根与算术平方根 | review_status=pending (review_round=1) — 还没过任何审核 |
| `M_G1_NS_14` | 除法是乘法的逆运算 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `M_G1_NS_14` | 除法是乘法的逆运算 | 标题 / 关键术语有没有错别字? |
| `M_G1_NS_14` | 除法是乘法的逆运算 | 上下游关系对不对? (看 prereq / unlock) |
| `M_G1_NS_14` | 除法是乘法的逆运算 | academic_req 为空 — 学业要求暂未补全 |
| `M_G1_NS_14` | 除法是乘法的逆运算 | review_status=pending (review_round=1) — 还没过任何审核 |
| `M_G2_NS_20` | 质数与合数 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `M_G2_NS_20` | 质数与合数 | 标题 / 关键术语有没有错别字? |
| `M_G2_NS_20` | 质数与合数 | 上下游关系对不对? (看 prereq / unlock) |
| `M_G2_NS_20` | 质数与合数 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `M_G2_NS_20` | 质数与合数 | review_status=pending (review_round=1) — 还没过任何审核 |
| `M_G1_GM_08` | 长度单位换算 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `M_G1_GM_08` | 长度单位换算 | 标题 / 关键术语有没有错别字? |
| `M_G1_GM_08` | 长度单位换算 | 上下游关系对不对? (看 prereq / unlock) |
| `M_G1_GM_08` | 长度单位换算 | academic_req 为空 — 学业要求暂未补全 |
| `M_G1_GM_08` | 长度单位换算 | review_status=pending (review_round=1) — 还没过任何审核 |
| `CN_C1_PR_01` | 阅读有关个人生活家庭生活短文 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `CN_C1_PR_01` | 阅读有关个人生活家庭生活短文 | 标题 / 关键术语有没有错别字? |
| `CN_C1_PR_01` | 阅读有关个人生活家庭生活短文 | 上下游关系对不对? (看 prereq / unlock) |
| `CN_C1_PR_01` | 阅读有关个人生活家庭生活短文 | academic_req 为空 — 学业要求暂未补全 |
| `CN_C1_PR_01` | 阅读有关个人生活家庭生活短文 | review_status=pending (review_round=1) — 还没过任何审核 |
| `CN_C3_SP_01` | 复述转述讲述 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `CN_C3_SP_01` | 复述转述讲述 | 标题 / 关键术语有没有错别字? |
| `CN_C3_SP_01` | 复述转述讲述 | 上下游关系对不对? (看 prereq / unlock) |
| `CN_C3_SP_01` | 复述转述讲述 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `CN_C3_SP_01` | 复述转述讲述 | academic_req 为空 — 学业要求暂未补全 |
| `CN_C3_SP_01` | 复述转述讲述 | review_status=pending (review_round=1) — 还没过任何审核 |
| `CN_C4_XS_01` | 跨学科专题研究 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `CN_C4_XS_01` | 跨学科专题研究 | 标题 / 关键术语有没有错别字? |
| `CN_C4_XS_01` | 跨学科专题研究 | 上下游关系对不对? (看 prereq / unlock) |
| `CN_C4_XS_01` | 跨学科专题研究 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `CN_C4_XS_01` | 跨学科专题研究 | academic_req 为空 — 学业要求暂未补全 |
| `CN_C4_XS_01` | 跨学科专题研究 | review_status=pending (review_round=1) — 还没过任何审核 |
| `EN_E4_GR_02` | 非谓语动词 | content_req 真在 2022 课标第 None 页? (Y/N) |
| `EN_E4_GR_02` | 非谓语动词 | 标题 / 关键术语有没有错别字? |
| `EN_E4_GR_02` | 非谓语动词 | 上下游关系对不对? (看 prereq / unlock) |
| `EN_E4_GR_02` | 非谓语动词 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `EN_E4_GR_02` | 非谓语动词 | academic_req 为空 — 学业要求暂未补全 |
| `EN_E4_GR_02` | 非谓语动词 | review_status=pending (review_round=1) — 还没过任何审核 |
| `EN_E4_SK_02` | 讨论与辩论 | content_req 真在 2022 课标第 None 页? (Y/N) |
| `EN_E4_SK_02` | 讨论与辩论 | 标题 / 关键术语有没有错别字? |
| `EN_E4_SK_02` | 讨论与辩论 | 上下游关系对不对? (看 prereq / unlock) |
| `EN_E4_SK_02` | 讨论与辩论 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `EN_E4_SK_02` | 讨论与辩论 | academic_req 为空 — 学业要求暂未补全 |
| `EN_E4_SK_02` | 讨论与辩论 | review_status=pending (review_round=1) — 还没过任何审核 |
| `EN_E1_TX_01` | 听说简单对话/小故事 | content_req 真在 2022 课标第 None 页? (Y/N) |
| `EN_E1_TX_01` | 听说简单对话/小故事 | 标题 / 关键术语有没有错别字? |
| `EN_E1_TX_01` | 听说简单对话/小故事 | 上下游关系对不对? (看 prereq / unlock) |
| `EN_E1_TX_01` | 听说简单对话/小故事 | academic_req 为空 — 学业要求暂未补全 |
| `EN_E1_TX_01` | 听说简单对话/小故事 | review_status=pending (review_round=1) — 还没过任何审核 |
| `P_P1_09` | 原子结构 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `P_P1_09` | 原子结构 | 标题 / 关键术语有没有错别字? |
| `P_P1_09` | 原子结构 | 上下游关系对不对? (看 prereq / unlock) |
| `P_P1_09` | 原子结构 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `P_P1_09` | 原子结构 | review_status=pending (review_round=1) — 还没过任何审核 |
| `P_P2_10` | 牛顿第一定律 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `P_P2_10` | 牛顿第一定律 | 标题 / 关键术语有没有错别字? |
| `P_P2_10` | 牛顿第一定律 | 上下游关系对不对? (看 prereq / unlock) |
| `P_P2_10` | 牛顿第一定律 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `P_P2_10` | 牛顿第一定律 | academic_req 为空 — 学业要求暂未补全 |
| `P_P2_10` | 牛顿第一定律 | review_status=pending (review_round=1) — 还没过任何审核 |
| `CH_C5_04` | 化学与环境 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `CH_C5_04` | 化学与环境 | 标题 / 关键术语有没有错别字? |
| `CH_C5_04` | 化学与环境 | 上下游关系对不对? (看 prereq / unlock) |
| `CH_C5_04` | 化学与环境 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `CH_C5_04` | 化学与环境 | academic_req 为空 — 学业要求暂未补全 |
| `CH_C5_04` | 化学与环境 | review_status=pending (review_round=1) — 还没过任何审核 |
| `B_B4_04` | DNA 是遗传物质 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `B_B4_04` | DNA 是遗传物质 | 标题 / 关键术语有没有错别字? |
| `B_B4_04` | DNA 是遗传物质 | 上下游关系对不对? (看 prereq / unlock) |
| `B_B4_04` | DNA 是遗传物质 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `B_B4_04` | DNA 是遗传物质 | academic_req 为空 — 学业要求暂未补全 |
| `B_B4_04` | DNA 是遗传物质 | review_status=pending (review_round=1) — 还没过任何审核 |
| `H_H3_CR_03` | 社会主义建设探索 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `H_H3_CR_03` | 社会主义建设探索 | 标题 / 关键术语有没有错别字? |
| `H_H3_CR_03` | 社会主义建设探索 | 上下游关系对不对? (看 prereq / unlock) |
| `H_H3_CR_03` | 社会主义建设探索 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `H_H3_CR_03` | 社会主义建设探索 | academic_req 为空 — 学业要求暂未补全 |
| `H_H3_CR_03` | 社会主义建设探索 | review_status=pending (review_round=1) — 还没过任何审核 |
| `H_H4_WC_04` | 第二次世界大战 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `H_H4_WC_04` | 第二次世界大战 | 标题 / 关键术语有没有错别字? |
| `H_H4_WC_04` | 第二次世界大战 | 上下游关系对不对? (看 prereq / unlock) |
| `H_H4_WC_04` | 第二次世界大战 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `H_H4_WC_04` | 第二次世界大战 | academic_req 为空 — 学业要求暂未补全 |
| `H_H4_WC_04` | 第二次世界大战 | review_status=pending (review_round=1) — 还没过任何审核 |
| `G_G3_02` | 语言与宗教 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `G_G3_02` | 语言与宗教 | 标题 / 关键术语有没有错别字? |
| `G_G3_02` | 语言与宗教 | 上下游关系对不对? (看 prereq / unlock) |
| `G_G3_02` | 语言与宗教 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `G_G3_02` | 语言与宗教 | academic_req 为空 — 学业要求暂未补全 |
| `G_G3_02` | 语言与宗教 | review_status=pending (review_round=1) — 还没过任何审核 |
| `G_G1_03` | 地球自转与公转 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `G_G1_03` | 地球自转与公转 | 标题 / 关键术语有没有错别字? |
| `G_G1_03` | 地球自转与公转 | 上下游关系对不对? (看 prereq / unlock) |
| `G_G1_03` | 地球自转与公转 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `G_G1_03` | 地球自转与公转 | academic_req 为空 — 学业要求暂未补全 |
| `G_G1_03` | 地球自转与公转 | review_status=pending (review_round=1) — 还没过任何审核 |
| `ML_ML_G5_01` | 面对挫折 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `ML_ML_G5_01` | 面对挫折 | 标题 / 关键术语有没有错别字? |
| `ML_ML_G5_01` | 面对挫折 | 上下游关系对不对? (看 prereq / unlock) |
| `ML_ML_G5_01` | 面对挫折 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `ML_ML_G5_01` | 面对挫折 | academic_req 为空 — 学业要求暂未补全 |
| `ML_ML_G5_01` | 面对挫折 | review_status=pending (review_round=1) — 还没过任何审核 |
| `ML_ML_G3_01` | 我们的学校生活 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `ML_ML_G3_01` | 我们的学校生活 | 标题 / 关键术语有没有错别字? |
| `ML_ML_G3_01` | 我们的学校生活 | 上下游关系对不对? (看 prereq / unlock) |
| `ML_ML_G3_01` | 我们的学校生活 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `ML_ML_G3_01` | 我们的学校生活 | academic_req 为空 — 学业要求暂未补全 |
| `ML_ML_G3_01` | 我们的学校生活 | review_status=pending (review_round=1) — 还没过任何审核 |
| `SC_S2_MS_05` | 光的传播与反射 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `SC_S2_MS_05` | 光的传播与反射 | 标题 / 关键术语有没有错别字? |
| `SC_S2_MS_05` | 光的传播与反射 | 上下游关系对不对? (看 prereq / unlock) |
| `SC_S2_MS_05` | 光的传播与反射 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `SC_S2_MS_05` | 光的传播与反射 | academic_req 为空 — 学业要求暂未补全 |
| `SC_S2_MS_05` | 光的传播与反射 | review_status=pending (review_round=1) — 还没过任何审核 |
| `SC_S2_ES_01` | 地球的形状与运动 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `SC_S2_ES_01` | 地球的形状与运动 | 标题 / 关键术语有没有错别字? |
| `SC_S2_ES_01` | 地球的形状与运动 | 上下游关系对不对? (看 prereq / unlock) |
| `SC_S2_ES_01` | 地球的形状与运动 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `SC_S2_ES_01` | 地球的形状与运动 | academic_req 为空 — 学业要求暂未补全 |
| `SC_S2_ES_01` | 地球的形状与运动 | review_status=pending (review_round=1) — 还没过任何审核 |
| `IT_I7_02` | 数字公民 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `IT_I7_02` | 数字公民 | 标题 / 关键术语有没有错别字? |
| `IT_I7_02` | 数字公民 | 上下游关系对不对? (看 prereq / unlock) |
| `IT_I7_02` | 数字公民 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `IT_I7_02` | 数字公民 | academic_req 为空 — 学业要求暂未补全 |
| `IT_I7_02` | 数字公民 | review_status=pending (review_round=1) — 还没过任何审核 |
| `ART_A3_02` | 民族舞蹈体验 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `ART_A3_02` | 民族舞蹈体验 | 标题 / 关键术语有没有错别字? |
| `ART_A3_02` | 民族舞蹈体验 | 上下游关系对不对? (看 prereq / unlock) |
| `ART_A3_02` | 民族舞蹈体验 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `ART_A3_02` | 民族舞蹈体验 | review_status=pending (review_round=1) — 还没过任何审核 |
| `PE_PE5_04` | 青春期健康 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `PE_PE5_04` | 青春期健康 | 标题 / 关键术语有没有错别字? |
| `PE_PE5_04` | 青春期健康 | 上下游关系对不对? (看 prereq / unlock) |
| `PE_PE5_04` | 青春期健康 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `PE_PE5_04` | 青春期健康 | academic_req 为空 — 学业要求暂未补全 |
| `PE_PE5_04` | 青春期健康 | review_status=pending (review_round=1) — 还没过任何审核 |
| `L_L5_02` | 简单产品制作 | content_req 真在 2022 课标第 1 页? (Y/N) |
| `L_L5_02` | 简单产品制作 | 标题 / 关键术语有没有错别字? |
| `L_L5_02` | 简单产品制作 | 上下游关系对不对? (看 prereq / unlock) |
| `L_L5_02` | 简单产品制作 | indegree=0 但 grade>2 — 真的是'零基础可学'吗? 还是只是图谱上游节点缺失? |
| `L_L5_02` | 简单产品制作 | academic_req 为空 — 学业要求暂未补全 |
| `L_L5_02` | 简单产品制作 | review_status=pending (review_round=1) — 还没过任何审核 |

## 审核流程建议

1. 打开 `data/raw/curriculum_2022/{编号}_{学科}.pdf` 对照 `src_page` 找到原页
2. 逐条核对 content_req 是否是 2022 版课标原文 (vs 2011 版)
3. 标题是否有错别字 / 简称 / 与课标不一致 (例: '算理' vs '运算')
4. indegree=0 且 grade>2 的节点: 是不是图谱上游缺边, 真的是零基础?
5. 改完意见后, 回 `data/audit/sampled_30.md` 填写 5 列, 同步更新 `data/graph/{subject}_v0.7.json`
6. 标记 `review_status: audited` 写回节点, 跑 `python3 src/pipeline/audit_sample.py --update` 自动更新
