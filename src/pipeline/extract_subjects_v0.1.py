"""
为更多学科生成 V0.1 preseed 概念图谱
- 语文 / 英语 / 科学 / 道法 / 历史 / 地理 / 物理 / 化学 / 生物 / 信息科技 / 艺术 / 体育 / 劳动
- 基于 2022 课标目录 + 人教版/部编版教材结构
"""
import json
from pathlib import Path
from datetime import datetime

PARSED_DIR = Path(__file__).parent.parent.parent / "data" / "parsed"
GRAPH_DIR = Path(__file__).parent.parent.parent / "data" / "graph"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

def make_node(cid, title, subject, stage, g_start, g_end, domain, subdomain):
    return {
        "id": cid,
        "subject": subject,
        "stage": stage,
        "grade_start": g_start,
        "grade_end": g_end,
        "title": title,
        "title_en": "",
        "domain": domain,
        "subdomain": subdomain,
        "core_literacy": [],
        "textbook_versions": ["人教版", "部编版"],
        "example": "",
        "description": "",
        "source_refs": ["2022-curriculum", "preseed-v0.1"],
        "tags": [],
        "difficulty": min(5, max(1, g_start)),
        "estimated_minutes": 30 + g_start * 5,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

def build_subjects_v0_1():
    all_concepts = {}
    all_edges = []

    # ==========================================
    # 语文 (chinese) - 部编版 1-9 年级
    # ==========================================
    chinese = [
        # 1-2 年级：识字与写字
        ("ch-1-pinyin", "汉语拼音", 1, 1, "识字", "pinyin"),
        ("ch-1-char-1600", "认识常用汉字 1600 个", 1, 2, "识字", "chars"),
        ("ch-1-write-800", "会写 800 个常用字", 1, 2, "写字", "writing"),
        ("ch-1-read-50k", "课外阅读 5 万字", 1, 2, "阅读", "reading"),
        ("ch-1-recite-50", "背诵优秀诗文 50 篇", 1, 2, "古诗文", "recitation"),
        # 3-4 年级
        ("ch-2-char-2500", "累计认识 2500 汉字", 3, 4, "识字", "chars"),
        ("ch-2-write-1600", "会写 1600 汉字", 3, 4, "写字", "writing"),
        ("ch-2-mute-read", "默读不出声", 3, 4, "阅读", "reading"),
        ("ch-2-read-40k", "课外阅读 40 万字", 3, 4, "阅读", "reading"),
        ("ch-2-recite-50", "背诵优秀诗文 50 篇(累计 100)", 3, 4, "古诗文", "recitation"),
        ("ch-2-whole-book", "整本书阅读", 3, 6, "阅读", "whole_book"),
        # 5-6 年级
        ("ch-3-char-3000", "累计认识 3000 汉字", 5, 6, "识字", "chars"),
        ("ch-3-write-2500", "会写 2500 汉字", 5, 6, "写字", "writing"),
        ("ch-3-mute-300wpm", "默读 300 字/分钟", 5, 6, "阅读", "reading"),
        ("ch-3-read-100k", "课外阅读 100 万字", 5, 6, "阅读", "reading"),
        ("ch-3-recite-60", "背诵优秀诗文 60 篇(累计 160)", 5, 6, "古诗文", "recitation"),
        ("ch-3-browse", "浏览搜集信息", 5, 6, "阅读", "browse"),
        ("ch-3-composition-16", "习作 16 次/学年", 5, 6, "写作", "composition"),
        # 7-9 年级（初中语文）
        ("ch-7-char-3500", "累计认识 3500 汉字", 7, 9, "识字", "chars"),
        ("ch-7-mute-500wpm", "默读 500 字/分钟", 7, 9, "阅读", "reading"),
        ("ch-7-classic-novels", "每学年读 2-3 部名著", 7, 9, "阅读", "whole_book"),
        ("ch-7-composition-14", "作文 14 次/学年", 7, 9, "写作", "composition"),
        ("ch-7-ancient-prose", "文言文阅读", 7, 9, "古诗文", "classical_chinese"),
        ("ch-7-poetry", "古诗词鉴赏", 7, 9, "古诗文", "poetry"),
        ("ch-7-rhetoric", "修辞手法", 7, 9, "写作", "rhetoric"),
        ("ch-7-critical-reading", "批判性阅读", 8, 9, "阅读", "critical"),
    ]

    # 语文先决关系
    chinese_edges = [
        ("ch-1-pinyin", "ch-1-char-1600"),
        ("ch-1-pinyin", "ch-1-write-800"),
        ("ch-1-char-1600", "ch-1-write-800"),
        ("ch-1-write-800", "ch-1-read-50k"),
        ("ch-1-write-800", "ch-2-char-2500"),
        ("ch-2-char-2500", "ch-2-write-1600"),
        ("ch-2-write-1600", "ch-2-mute-read"),
        ("ch-2-mute-read", "ch-2-read-40k"),
        ("ch-2-read-40k", "ch-2-whole-book"),
        ("ch-2-recite-50", "ch-2-read-40k"),
        ("ch-2-write-1600", "ch-3-char-3000"),
        ("ch-3-char-3000", "ch-3-write-2500"),
        ("ch-3-write-2500", "ch-3-mute-300wpm"),
        ("ch-3-mute-300wpm", "ch-3-read-100k"),
        ("ch-2-whole-book", "ch-3-read-100k"),
        ("ch-2-recite-50", "ch-3-recite-60"),
        ("ch-3-write-2500", "ch-3-composition-16"),
        ("ch-3-write-2500", "ch-3-browse"),
        ("ch-3-composition-16", "ch-7-composition-14"),
        ("ch-3-write-2500", "ch-7-char-3500"),
        ("ch-3-mute-300wpm", "ch-7-mute-500wpm"),
        ("ch-3-read-100k", "ch-7-classic-novels"),
        ("ch-2-whole-book", "ch-7-classic-novels"),
        ("ch-3-recite-60", "ch-7-poetry"),
        ("ch-7-classic-novels", "ch-7-ancient-prose"),
        ("ch-7-classic-novels", "ch-7-rhetoric"),
        ("ch-7-rhetoric", "ch-7-composition-14"),
        ("ch-7-mute-500wpm", "ch-7-critical-reading"),
        ("ch-7-ancient-prose", "ch-7-critical-reading"),
    ]

    # ==========================================
    # 英语 (english) - PEP 3-9 年级
    # ==========================================
    english = [
        # 3-4 年级
        ("en-3-alphabet", "26 个字母", 3, 3, "字母", "alphabet"),
        ("en-3-greeting", "日常问候", 3, 3, "口语", "speaking"),
        ("en-3-numbers", "数字 1-100", 3, 3, "词汇", "vocabulary"),
        ("en-3-color-shape", "颜色和形状", 3, 3, "词汇", "vocabulary"),
        ("en-3-family", "家庭成员称呼", 3, 3, "词汇", "vocabulary"),
        ("en-3-simple-sentence", "简单句", 3, 4, "语法", "sentence"),
        # 5-6 年级
        ("en-5-vocab-500", "核心词汇 500", 5, 6, "词汇", "vocabulary"),
        ("en-5-present-tense", "一般现在时", 5, 5, "语法", "grammar"),
        ("en-5-past-tense", "一般过去时", 5, 6, "语法", "grammar"),
        ("en-5-future-tense", "一般将来时", 5, 6, "语法", "grammar"),
        ("en-5-reading-50w", "阅读量 5 万词", 5, 6, "阅读", "reading"),
        ("en-5-composition-50w", "短文写作 50 词", 5, 6, "写作", "writing"),
        # 7-9 年级
        ("en-7-vocab-1600", "中考词汇 1600", 7, 9, "词汇", "vocabulary"),
        ("en-7-tense-system", "时态系统(8 种)", 7, 9, "语法", "grammar"),
        ("en-7-clauses", "从句(宾/定/状)", 7, 9, "语法", "grammar"),
        ("en-7-passive", "被动语态", 7, 9, "语法", "grammar"),
        ("en-7-reading-100k", "阅读量 10 万词", 7, 9, "阅读", "reading"),
        ("en-7-composition-100w", "作文 100 词", 7, 9, "写作", "writing"),
        ("en-7-listening", "听力理解", 7, 9, "听力", "listening"),
        ("en-7-oral", "口语交际", 7, 9, "口语", "speaking"),
        ("en-9-vocab-2000", "高考词汇 2000", 9, 9, "词汇", "vocabulary"),
    ]

    english_edges = [
        ("en-3-alphabet", "en-3-greeting"),
        ("en-3-alphabet", "en-3-numbers"),
        ("en-3-alphabet", "en-3-color-shape"),
        ("en-3-alphabet", "en-3-family"),
        ("en-3-greeting", "en-3-simple-sentence"),
        ("en-3-simple-sentence", "en-5-vocab-500"),
        ("en-5-vocab-500", "en-5-present-tense"),
        ("en-5-present-tense", "en-5-past-tense"),
        ("en-5-past-tense", "en-5-future-tense"),
        ("en-5-vocab-500", "en-5-reading-50w"),
        ("en-5-vocab-500", "en-5-composition-50w"),
        ("en-5-past-tense", "en-7-tense-system"),
        ("en-5-future-tense", "en-7-tense-system"),
        ("en-5-reading-50w", "en-7-reading-100k"),
        ("en-5-composition-50w", "en-7-composition-100w"),
        ("en-7-tense-system", "en-7-clauses"),
        ("en-7-clauses", "en-7-passive"),
        ("en-7-tense-system", "en-7-listening"),
        ("en-7-tense-system", "en-7-oral"),
        ("en-7-vocab-1600", "en-9-vocab-2000"),
    ]

    # ==========================================
    # 科学 (science) - 1-6 年级 (小学科学)
    # ==========================================
    science = [
        # 1-2 年级
        ("sc-1-plant-observe", "观察植物", 1, 2, "生命科学", "biology"),
        ("sc-1-animal-observe", "观察动物", 1, 2, "生命科学", "biology"),
        ("sc-1-body-parts", "认识身体部位", 1, 2, "生命科学", "body"),
        ("sc-1-weather", "观察天气", 1, 2, "地球科学", "earth"),
        ("sc-1-materials", "常见材料(纸/木/塑料)", 1, 2, "物质科学", "matter"),
        # 3-4 年级
        ("sc-3-animal-classify", "动物分类", 3, 4, "生命科学", "biology"),
        ("sc-3-plant-life", "植物的一生", 3, 4, "生命科学", "biology"),
        ("sc-3-water-cycle", "水循环", 3, 4, "地球科学", "earth"),
        ("sc-3-states-of-matter", "物质三态", 3, 4, "物质科学", "matter"),
        ("sc-3-magnets", "磁铁", 3, 4, "物质科学", "physics"),
        # 5-6 年级
        ("sc-5-cell", "细胞", 5, 6, "生命科学", "biology"),
        ("sc-5-ecosystem", "生态系统", 5, 6, "生命科学", "biology"),
        ("sc-5-solar-system", "太阳系", 5, 6, "地球科学", "earth"),
        ("sc-5-simple-machines", "简单机械", 5, 6, "物质科学", "physics"),
        ("sc-5-energy-forms", "能量的形式", 5, 6, "物质科学", "physics"),
    ]

    science_edges = [
        ("sc-1-plant-observe", "sc-3-plant-life"),
        ("sc-1-animal-observe", "sc-3-animal-classify"),
        ("sc-1-body-parts", "sc-5-cell"),
        ("sc-1-weather", "sc-3-water-cycle"),
        ("sc-1-materials", "sc-3-states-of-matter"),
        ("sc-1-materials", "sc-3-magnets"),
        ("sc-3-animal-classify", "sc-5-ecosystem"),
        ("sc-3-plant-life", "sc-5-ecosystem"),
        ("sc-3-water-cycle", "sc-5-solar-system"),
        ("sc-3-states-of-matter", "sc-5-energy-forms"),
        ("sc-3-magnets", "sc-5-simple-machines"),
        ("sc-3-states-of-matter", "sc-5-simple-machines"),
    ]

    # ==========================================
    # 道法 (morality_law) - 全学段
    # ==========================================
    ml = [
        ("ml-1-self", "认识自己", 1, 2, "自我认识", "self"),
        ("ml-1-family", "我爱我家", 1, 2, "家庭", "family"),
        ("ml-1-friends", "我和同学", 1, 2, "交往", "social"),
        ("ml-3-school", "我们的学校", 3, 4, "学校", "school"),
        ("ml-3-hometown", "家乡的抚育", 3, 4, "家乡", "hometown"),
        ("ml-3-public-life", "公共生活", 3, 4, "社会", "public"),
        ("ml-5-constitution", "宪法是根本法", 5, 6, "法治", "law"),
        ("ml-5-citizen-rights", "公民权利与义务", 5, 6, "法治", "rights"),
        ("ml-5-china-profile", "中国概况", 5, 6, "国情", "china"),
        ("ml-7-political-system", "我国政治制度", 7, 9, "政治", "politics"),
        ("ml-7-economy", "经济发展", 7, 9, "经济", "economy"),
        ("ml-7-culture", "文化传承", 7, 9, "文化", "culture"),
        ("ml-7-rule-of-law", "全面依法治国", 7, 9, "法治", "law"),
        ("ml-7-philosophy", "哲学入门", 8, 9, "哲学", "philosophy"),
    ]

    ml_edges = [
        ("ml-1-self", "ml-1-family"),
        ("ml-1-self", "ml-1-friends"),
        ("ml-1-family", "ml-3-school"),
        ("ml-1-friends", "ml-3-school"),
        ("ml-3-school", "ml-3-hometown"),
        ("ml-3-school", "ml-3-public-life"),
        ("ml-3-hometown", "ml-5-china-profile"),
        ("ml-3-public-life", "ml-5-citizen-rights"),
        ("ml-5-constitution", "ml-5-citizen-rights"),
        ("ml-5-china-profile", "ml-7-political-system"),
        ("ml-5-citizen-rights", "ml-7-political-system"),
        ("ml-5-citizen-rights", "ml-7-rule-of-law"),
        ("ml-7-political-system", "ml-7-economy"),
        ("ml-7-political-system", "ml-7-culture"),
        ("ml-7-culture", "ml-7-philosophy"),
    ]

    # ==========================================
    # 历史 (history) - 7-9 年级
    # ==========================================
    history = [
        ("hi-7-prehistory", "中国古代史前", 7, 7, "中国古代史", "ancient"),
        ("hi-7-xia-shang-zhou", "夏商周", 7, 7, "中国古代史", "ancient"),
        ("hi-7-qin-han", "秦汉", 7, 7, "中国古代史", "ancient"),
        ("hi-7-tang-song", "唐宋", 7, 7, "中国古代史", "ancient"),
        ("hi-7-yuan-ming-qing", "元明清", 7, 7, "中国古代史", "ancient"),
        ("hi-7-near-ancient", "中国近代史", 7, 8, "中国近代史", "modern"),
        ("hi-7-contemporary", "中国现代史", 8, 8, "中国现代史", "contemporary"),
        ("hi-8-world-ancient", "世界古代史", 7, 7, "世界史", "world"),
        ("hi-8-world-modern", "世界近代史", 8, 8, "世界史", "world"),
        ("hi-8-world-contemp", "世界现代史", 9, 9, "世界史", "world"),
        ("hi-9-revolution", "革命史专题", 9, 9, "中国现代史", "revolution"),
    ]

    history_edges = [
        ("hi-7-prehistory", "hi-7-xia-shang-zhou"),
        ("hi-7-xia-shang-zhou", "hi-7-qin-han"),
        ("hi-7-qin-han", "hi-7-tang-song"),
        ("hi-7-tang-song", "hi-7-yuan-ming-qing"),
        ("hi-7-yuan-ming-qing", "hi-7-near-ancient"),
        ("hi-7-near-ancient", "hi-7-contemporary"),
        ("hi-7-prehistory", "hi-8-world-ancient"),
        ("hi-8-world-ancient", "hi-8-world-modern"),
        ("hi-8-world-modern", "hi-8-world-contemp"),
        ("hi-7-contemporary", "hi-9-revolution"),
    ]

    # ==========================================
    # 地理 (geography) - 7-9 年级
    # ==========================================
    geography = [
        ("ge-7-earth", "地球与地图", 7, 7, "自然地理", "earth"),
        ("ge-7-weather-climate", "天气与气候", 7, 7, "自然地理", "climate"),
        ("ge-7-landforms", "地形地貌", 7, 7, "自然地理", "landform"),
        ("ge-7-rivers-lakes", "河流与湖泊", 7, 7, "自然地理", "hydrology"),
        ("ge-7-population", "人口与民族", 7, 7, "人文地理", "population"),
        ("ge-7-china-overview", "中国地理概况", 7, 8, "中国地理", "china"),
        ("ge-8-china-regions", "中国分区", 8, 8, "中国地理", "china"),
        ("ge-8-world-overview", "世界地理概况", 8, 8, "世界地理", "world"),
        ("ge-8-world-regions", "世界分区", 8, 8, "世界地理", "world"),
        ("ge-9-economic", "经济发展与差异", 9, 9, "人文地理", "economy"),
    ]

    geography_edges = [
        ("ge-7-earth", "ge-7-weather-climate"),
        ("ge-7-weather-climate", "ge-7-landforms"),
        ("ge-7-landforms", "ge-7-rivers-lakes"),
        ("ge-7-rivers-lakes", "ge-7-china-overview"),
        ("ge-7-population", "ge-7-china-overview"),
        ("ge-7-china-overview", "ge-8-china-regions"),
        ("ge-7-earth", "ge-8-world-overview"),
        ("ge-8-world-overview", "ge-8-world-regions"),
        ("ge-8-china-regions", "ge-9-economic"),
    ]

    # ==========================================
    # 物理 (physics) - 8-9 年级
    # ==========================================
    physics = [
        ("ph-8-mechanics-intro", "机械运动", 8, 8, "力学", "mechanics"),
        ("ph-8-force", "力", 8, 8, "力学", "force"),
        ("ph-8-pressure", "压强", 8, 8, "力学", "pressure"),
        ("ph-8-floating", "浮力", 8, 8, "力学", "buoyancy"),
        ("ph-8-work-power", "功和机械能", 8, 9, "力学", "energy"),
        ("ph-8-heat", "内能", 8, 9, "热学", "heat"),
        ("ph-9-electricity", "电路基础", 9, 9, "电学", "electricity"),
        ("ph-9-ohm", "欧姆定律", 9, 9, "电学", "ohm"),
        ("ph-9-power", "电功率", 9, 9, "电学", "power"),
        ("ph-9-magnetism", "电与磁", 9, 9, "电学", "magnetism"),
        ("ph-9-wave", "信息的传递(波)", 9, 9, "光学", "wave"),
    ]

    physics_edges = [
        ("ph-8-mechanics-intro", "ph-8-force"),
        ("ph-8-force", "ph-8-pressure"),
        ("ph-8-force", "ph-8-floating"),
        ("ph-8-pressure", "ph-8-floating"),
        ("ph-8-force", "ph-8-work-power"),
        ("ph-8-mechanics-intro", "ph-8-work-power"),
        ("ph-8-work-power", "ph-8-heat"),
        ("ph-9-electricity", "ph-9-ohm"),
        ("ph-9-electricity", "ph-9-power"),
        ("ph-9-ohm", "ph-9-power"),
        ("ph-9-power", "ph-9-magnetism"),
        ("ph-8-heat", "ph-9-wave"),
    ]

    # ==========================================
    # 化学 (chemistry) - 9 年级
    # ==========================================
    chemistry = [
        ("ch-9-matter", "物质构成的奥秘", 9, 9, "物质构成", "matter"),
        ("ch-9-atom", "原子结构", 9, 9, "物质构成", "atom"),
        ("ch-9-element", "元素与元素周期表", 9, 9, "物质构成", "element"),
        ("ch-9-compound", "化合物", 9, 9, "物质构成", "compound"),
        ("ch-9-reaction", "化学反应基本规律", 9, 9, "化学反应", "reaction"),
        ("ch-9-acid-base", "常见的酸碱盐", 9, 9, "化学反应", "acid_base"),
        ("ch-9-metal", "金属和金属材料", 9, 9, "物质构成", "metal"),
    ]

    chemistry_edges = [
        ("ch-9-matter", "ch-9-atom"),
        ("ch-9-atom", "ch-9-element"),
        ("ch-9-element", "ch-9-compound"),
        ("ch-9-compound", "ch-9-reaction"),
        ("ch-9-reaction", "ch-9-acid-base"),
        ("ch-9-element", "ch-9-metal"),
        ("ch-9-reaction", "ch-9-metal"),
    ]

    # ==========================================
    # 生物 (biology) - 7-8 年级
    # ==========================================
    biology = [
        ("bi-7-cell", "细胞是生命基本单位", 7, 7, "生物体结构", "cell"),
        ("bi-7-cell-structure", "细胞结构", 7, 7, "生物体结构", "cell"),
        ("bi-7-tissue", "组织", 7, 7, "生物体结构", "tissue"),
        ("bi-7-organ", "器官与系统", 7, 7, "生物体结构", "organ"),
        ("bi-7-plant-types", "植物的主要类群", 7, 7, "生物多样性", "plant"),
        ("bi-7-animal-types", "动物的主要类群", 7, 7, "生物多样性", "animal"),
        ("bi-7-microorganism", "微生物", 7, 7, "生物多样性", "micro"),
        ("bi-8-genetics", "生物的遗传和变异", 8, 8, "遗传进化", "genetics"),
        ("bi-8-evolution", "生命的进化", 8, 8, "遗传进化", "evolution"),
        ("bi-8-ecology", "生态系统", 8, 8, "生态系统", "ecology"),
        ("bi-8-health", "健康地生活", 8, 8, "健康", "health"),
    ]

    biology_edges = [
        ("bi-7-cell", "bi-7-cell-structure"),
        ("bi-7-cell-structure", "bi-7-tissue"),
        ("bi-7-tissue", "bi-7-organ"),
        ("bi-7-cell", "bi-7-plant-types"),
        ("bi-7-cell", "bi-7-animal-types"),
        ("bi-7-cell", "bi-7-microorganism"),
        ("bi-7-cell-structure", "bi-8-genetics"),
        ("bi-7-tissue", "bi-8-genetics"),
        ("bi-7-animal-types", "bi-8-evolution"),
        ("bi-7-plant-types", "bi-8-evolution"),
        ("bi-8-genetics", "bi-8-evolution"),
        ("bi-8-evolution", "bi-8-ecology"),
        ("bi-8-ecology", "bi-8-health"),
    ]

    # ==========================================
    # 信息科技 (info_tech) - 3-9 年级
    # ==========================================
    info_tech = [
        ("it-3-device", "认识信息设备", 3, 4, "信息意识", "device"),
        ("it-3-input-output", "输入输出", 3, 4, "信息意识", "io"),
        ("it-5-file", "文件管理", 5, 6, "信息意识", "file"),
        ("it-5-network", "网络基础", 5, 6, "信息意识", "network"),
        ("it-7-algorithm", "算法基础", 7, 9, "计算思维", "algorithm"),
        ("it-7-programming", "编程入门", 7, 9, "计算思维", "programming"),
        ("it-7-data", "数据处理", 7, 9, "计算思维", "data"),
        ("it-9-ai", "人工智能基础", 8, 9, "信息意识", "ai"),
    ]

    info_tech_edges = [
        ("it-3-device", "it-3-input-output"),
        ("it-3-input-output", "it-5-file"),
        ("it-3-input-output", "it-5-network"),
        ("it-5-file", "it-7-data"),
        ("it-5-network", "it-7-data"),
        ("it-7-algorithm", "it-7-programming"),
        ("it-7-algorithm", "it-7-data"),
        ("it-7-data", "it-9-ai"),
        ("it-7-programming", "it-9-ai"),
    ]

    # ==========================================
    # 艺术 (art) - 全学段
    # ==========================================
    art = [
        ("ar-1-song", "学唱歌", 1, 2, "音乐", "singing"),
        ("ar-1-draw", "绘画基础", 1, 2, "美术", "drawing"),
        ("ar-3-instrument", "认识乐器", 3, 4, "音乐", "instrument"),
        ("ar-3-color", "色彩运用", 3, 4, "美术", "color"),
        ("ar-5-compose", "简单作曲", 5, 6, "音乐", "compose"),
        ("ar-5-sculpture", "雕塑基础", 5, 6, "美术", "sculpture"),
    ]

    art_edges = [
        ("ar-1-song", "ar-1-draw"),
        ("ar-1-draw", "ar-3-color"),
        ("ar-1-song", "ar-3-instrument"),
        ("ar-3-instrument", "ar-5-compose"),
        ("ar-3-color", "ar-5-sculpture"),
    ]

    # ==========================================
    # 体育与健康 (pe_health) - 全学段
    # ==========================================
    pe = [
        ("pe-1-basic-move", "基本运动", 1, 2, "运动技能", "movement"),
        ("pe-3-team", "团队运动", 3, 4, "运动技能", "team"),
        ("pe-3-track", "田径基础", 3, 4, "运动技能", "track"),
        ("pe-5-basketball", "篮球", 5, 6, "运动技能", "basketball"),
        ("pe-5-soccer", "足球", 5, 6, "运动技能", "soccer"),
        ("pe-7-fitness", "体能训练", 7, 9, "运动技能", "fitness"),
    ]

    pe_edges = [
        ("pe-1-basic-move", "pe-3-team"),
        ("pe-1-basic-move", "pe-3-track"),
        ("pe-3-team", "pe-5-basketball"),
        ("pe-3-team", "pe-5-soccer"),
        ("pe-3-track", "pe-7-fitness"),
        ("pe-5-basketball", "pe-7-fitness"),
    ]

    # ==========================================
    # 劳动 (labor) - 全学段
    # ==========================================
    labor = [
        ("la-1-clean", "清洁与卫生", 1, 2, "日常生活劳动", "clean"),
        ("la-3-cooking", "简单烹饪", 3, 4, "生产劳动", "cooking"),
        ("la-3-diy", "手工制作", 3, 4, "生产劳动", "diy"),
        ("la-5-garden", "种植与养殖", 5, 6, "生产劳动", "garden"),
        ("la-7-tech", "技术与工程", 7, 9, "服务性劳动", "tech"),
    ]

    labor_edges = [
        ("la-1-clean", "la-3-cooking"),
        ("la-1-clean", "la-3-diy"),
        ("la-3-cooking", "la-5-garden"),
        ("la-3-diy", "la-5-garden"),
        ("la-5-garden", "la-7-tech"),
    ]

    # 汇总所有学科
    subjects = {
        "chinese": (chinese, chinese_edges),
        "english": (english, english_edges),
        "science": (science, science_edges),
        "morality_law": (ml, ml_edges),
        "history": (history, history_edges),
        "geography": (geography, geography_edges),
        "physics": (physics, physics_edges),
        "chemistry": (chemistry, chemistry_edges),
        "biology": (biology, biology_edges),
        "info_tech": (info_tech, info_tech_edges),
        "art": (art, art_edges),
        "pe_health": (pe, pe_edges),
        "labor": (labor, labor_edges),
    }

    # 写每个学科的 graph
    for subj, (concepts, edges) in subjects.items():
        nodes = []
        node_ids = set()
        for cid, title, g_start, g_end, domain, subdomain in concepts:
            node_ids.add(cid)
            stage = "junior_high" if g_start >= 7 else "primary"
            nodes.append(make_node(cid, title, subj, stage, g_start, g_end, domain, subdomain))

        # 验证边
        valid_edges = []
        for f, t in edges:
            if f in node_ids and t in node_ids:
                valid_edges.append([f, t, 1])
            else:
                print(f"  WARN: {subj} edge {f}->{t} has missing node")

        graph = {
            "version": "0.1.0",
            "subject": subj,
            "scope": "义教 1-9 年级 (课标 2022 版)",
            "node_count": len(nodes),
            "edge_count": len(valid_edges),
            "nodes": nodes,
            "edges": valid_edges,
            "generated_at": datetime.now().isoformat(),
            "license": "CC-BY-SA 4.0",
        }
        out_path = GRAPH_DIR / f"{subj}_v0.1.json"
        out_path.write_text(json.dumps(graph, ensure_ascii=False, indent=1))
        print(f"  ✅ {subj}: {len(nodes)} 概念, {len(valid_edges)} 关系")

    return subjects

def main():
    build_subjects_v0_1()
    print("\n完成 V0.1 preseed 全部学科")

if __name__ == "__main__":
    main()
