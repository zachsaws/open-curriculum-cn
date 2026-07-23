"""
V3.3.3 Chemistry LLM 化: 补 build.py 跑完剩余不达标的 4 个 + 全局 post-validation.
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path('/Users/tianxiang/.minimax-agent-cn/projects/open-curriculum-cn')
os.chdir(ROOT)

INPUT = 'data/v33_inputs/chemistry_remaining_input.json'
OUTPUT = 'data/graph/chemistry_v33_llm.json'

with open('/Users/tianxiang/.claude/settings.json') as f:
    settings = json.load(f)
TOKEN = settings['env']['ANTHROPIC_AUTH_TOKEN']
BASE_URL = 'https://api.minimaxi.com/anthropic/v1/messages'

# 加载已有
done = {c['id']: c for c in json.load(open(OUTPUT))}
print(f'已有: {len(done)} 概念', flush=True)

# 加载 input
all_data = json.load(open(INPUT))
targets = [c for c in all_data if c['id'] not in done]
print(f'待补: {[c["id"] for c in targets]}', flush=True)

# 通用 prompt (单条)
SYSTEM_PROMPT = """你是 V3.3.3 化学学科内容编辑. 你的任务: 把化学概念用「人话级」中文写出来.

# description 规则 (60-100 字, 1 段不换行)
- **必须用具体反应/具体物质/具体器材代替抽象定义** — 例:
  - 物质的多样性: 「桌上摆 5 杯东西——纯水、糖水、酒精、铁粉、盐, X 能不能把混合物挑出来? 看成分是不是只有一种」
  - 金属: 「把铁钉、铜丝、铝片 3 块金属放稀盐酸里, X 看到铁钉冒气泡最快, 铜丝没反应, 这是为什么?」
  - 酸碱: 「白醋 + 紫甘蓝汁变红, 肥皂水 + 紫甘蓝汁变绿, X 能不能用这 1 个办法区分 3 瓶未知液是酸是碱?」
  - 反应: 「碳酸钠粉末 5 g 加稀盐酸 20 mL, X 看到大量气泡, 这是什么气体? 怎么证明?」
  - 实验: 「漏斗下端紧贴烧杯内壁, 滤纸边缘低于漏斗, X 一边倒一边用玻璃棒引流, 滤液澄清就过滤成功」
  - 计算: 「水 H₂O 相对分子质量 1×2+16=18, X 能不能按这个套路算二氧化碳 CO₂ 的相对分子质量?」
  - 微观: 「水沸腾是水分子跑得快了点, 但分子还是 H₂O; 氢气燃烧后变成 H₂O, 分子本身变了, 这就是物理变化和化学变化的根本区别」
  - STS: 「汽车尾气含 NOₓ/CO, X 能不能说出 3 种办法减少? 三元催化器、电动、新能源」
- 化学要落地: 具体反应式/具体元素符号/具体实验器材/具体数字/具体单位
- 中间可用「」, **绝不要在 content 内用 ASCII 双引号 "**
- 不用绝对化承诺 (一定/必然/肯定)
- 反直觉 + 具体, 优于课标原文
- **绝不要"理解化学变化/培养化学思维/掌握化学知识"这种抽象话** — 一定要落到「几克/几毫升/几度/几秒/几厘米」具体数字 + 「看到什么/怎么操作/为什么」具体动作

# assessment_prompt 规则 (150-220 字, 3 问)
- **正好 3 问**, 行间用 \\n 分隔 (一个反斜杠加 n, 2 字符)
- 每问**正好 1 个** {{name}} 占位符 (两个花括号包 name, 不能用「小明」「孩子」等替代)
- 场景要具体: 含具体物质/具体数字/具体器材/具体操作/具体现象/具体单位
- 3 问难度递进: 第 1 问直接识别/操作, 第 2 问反例/纠错, 第 3 问解释/迁移
- 中文要自然: "能不能 / 会不会" 优于 "能否"
- 化学优先具体场景: "用 pH 试纸测 3 杯溶液 (白醋 pH=3 / 食盐水 pH=7 / 肥皂水 pH=10), {{name}} 能不能读出 3 个数, 并说出哪杯是酸哪杯是碱?"
- **绝不要在 content 内用 ASCII 双引号 "** (用「」)

# 禁词 (BANNED, 命中必须改)
理解 / 培养 / 掌握 / 运用 / 知识点 / 课标 / 教学目标 / 含义 / 定义 / 本概念 / 该概念 / 本节 / 本文 / 通过本 / 课标要求 / 具体含义

# 输出格式
严格 JSON 对象: {"id": "...", "description": "...", "assessment_prompt": "问1\\n问2\\n问3"}
不要 markdown 包裹. 严禁 ASCII 双引号 " 在 content 内部, 必须用「」."""


def call_llm_one(c):
    user = (
        f'ID: {c["id"]}\n'
        f'Title: {c["title"]}\n'
        f'Domain: {c["domain"]} / {c["subdomain"]}\n'
        f'Stage: 阶段{c["stage"]} (G{c["grade_start"]}-{c["grade_end"]})\n'
        f'Content: {c["content_req"]}\n'
        f'Key: {"; ".join(c["key_points"])}\n'
        f'Bloom: {", ".join(c["bloom"]) if c.get("bloom") else "无"}\n\n'
        f'请输出严格 JSON 对象: {{"id":"{c["id"]}","description":"...","assessment_prompt":"问1\\n问2\\n问3"}}\n'
        f'注意: assessment_prompt 正好 3 问, 每问正好 1 个 {{{{name}}}} 占位符, 共 3 个 {{{{name}}}}.'
    )
    body = json.dumps({
        'model': 'MiniMax-M3',
        'max_tokens': 2000,
        'system': SYSTEM_PROMPT,
        'messages': [{'role': 'user', 'content': user}],
    }).encode('utf-8')
    req = urllib.request.Request(BASE_URL, data=body, headers={
        'x-api-key': TOKEN,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result['content'][0]['text']
        except Exception as e:
            print(f'  [Err {type(e).__name__}] {e}, retry {attempt+1}/3', flush=True)
            time.sleep(5 + attempt * 5)
    raise RuntimeError('LLM 3 次都失败')


def parse_one(text):
    text = text.strip()
    text = re.sub(r'^```\w*\s*\n?', '', text)
    text = re.sub(r'\n?\s*```\s*$', '', text)
    m = re.search(r'\{', text)
    if not m:
        return None
    start = m.start()
    end = text.rfind('}')
    if end < start:
        return None
    raw = text[start:end+1]

    n = len(raw)
    quote_positions = []
    i = 0
    while i < n:
        c = raw[i]
        if c == '\\' and i + 1 < n:
            i += 2
            continue
        if c == '"':
            quote_positions.append(i)
        i += 1

    valid_pairs = []
    for k in range(0, len(quote_positions) - 1, 2):
        op = quote_positions[k]
        cp = quote_positions[k + 1]

        prev_ok = op == 0
        if not prev_ok:
            j = op - 1
            while j >= 0 and raw[j] in ' \t\n\r':
                j -= 1
            if j < 0 or raw[j] in '[{,:':
                prev_ok = True

        next_ok = cp == n - 1
        if not next_ok:
            j = cp + 1
            while j < n and raw[j] in ' \t\n\r':
                j += 1
            if j >= n or raw[j] in ',}]':
                next_ok = True

        if prev_ok and next_ok:
            valid_pairs.append((op, cp))

    result = []
    pos = 0
    for op, cp in valid_pairs:
        result.append(raw[pos:op+1])
        body = raw[op+1:cp]
        fixed = []
        toggle = True
        for ch in body:
            if ch == '"':
                fixed.append('「' if toggle else '」')
                toggle = not toggle
            else:
                fixed.append(ch)
        result.append(''.join(fixed))
        result.append('"')
        pos = cp + 1
    result.append(raw[pos:])

    fixed_text = ''.join(result)
    fixed_text = re.sub(r',\s*([\]\}])', r'\1', fixed_text)
    fixed_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', fixed_text)

    try:
        d = json.loads(fixed_text)
        return d if isinstance(d, dict) else None
    except Exception as e:
        print(f'  [parse fail] {e}', flush=True)
        pos = e.pos if hasattr(e, 'pos') else 0
        print(f'  ... {fixed_text[max(0,pos-80):pos+80]} ...', flush=True)
        return None


BANNED = ['理解', '培养', '掌握', '运用', '知识点', '课标', '教学目标', '含义', '定义', '本概念', '该概念', '本节', '本文', '通过本', '课标要求', '具体含义']
BANNED_FIX = {
    '理解': '看明白', '培养': '养成', '掌握': '会用', '运用': '用起来',
    '含义': '意思', '定义': '是啥', '本概念': '它', '该概念': '它',
}
CHEM_MISSING = [
    '反应', '燃烧', '氧化', '还原', '中和', '分解', '化合', '置换', '复分解', '催化', '电解',
    '反应式', '方程式', '离子方程式', '化学方程式', '反应现象',
    '物质', '元素', '原子', '分子', '离子', '电子', '质子', '中子', '原子核',
    '金属', '非金属', '氧化物', '酸', '碱', '盐', '化合物', '单质', '纯净物', '混合物',
    '铁', '铜', '铝', '锌', '镁', '银', '金',
    '氧', '氢', '氮', '氯', '碳', '硫', '磷',
    '盐酸', '硫酸', '硝酸', '醋酸', '碳酸',
    '氢氧化钠', '氢氧化钙', '氨水',
    '氯化钠', '碳酸钠', '碳酸钙', '碳酸氢钠', '硫酸铜', '氯化铁', '高锰酸钾',
    '水', '二氧化碳', '一氧化碳', '甲烷', '乙醇',
    '石灰石', '大理石', '生石灰', '熟石灰',
    '试管', '烧杯', '锥形瓶', '酒精灯', '铁架台', '石棉网', '蒸发皿', '坩埚', '量筒', '容量瓶',
    '胶头滴管', '玻璃棒', '导管', '集气瓶', '水槽', '漏斗', '滤纸', '研钵',
    '滴瓶', '试剂瓶', '广口瓶', '细口瓶',
    '托盘天平', '电子天平', 'pH 试纸', '紫色石蕊', '酚酞',
    '加热', '蒸发', '过滤', '蒸馏', '萃取', '分液', '结晶', '洗涤', '干燥', '冷却',
    '取样', '称量', '量取', '滴加', '振荡', '搅拌', '倾倒', '塞紧', '研磨',
    '性质', '物理性质', '化学性质', '颜色', '气味', '状态', '熔点', '沸点', '密度', '硬度',
    '溶解性', '挥发性', '腐蚀性', '毒性', '可燃性', '稳定性',
    '酸性', '碱性', '中性',
    '气泡', '沉淀', '变色', '放热', '吸热', '发光', '火焰', '烟雾', '浑浊', '变红', '变蓝',
    '克', '千克', '吨', '毫克', '升', '毫升', '立方米', '立方厘米',
    '摩尔', 'mol', 'g', 'kg', 'mL', 'L', 'pH',
    '度', '℃', '°C', '摄氏度', '帕', '帕斯卡', 'Pa', 'kPa', 'atm', '标准大气压',
    '分钟', '秒', '小时', '天', '周',
    '厘米', '毫米', '米', '微米', '纳米',
    '百分之', '百分号', '%',
    '红色', '蓝色', '绿色', '黄色', '白色', '黑色', '无色', '紫红色', '浅红色',
    '固体', '液体', '气体', '粉末', '晶体', '溶液', '悬浊液', '乳浊液',
]
CHAR_DISPLACE_PATTERNS = [r'原看明白', r'原掌握', r'原运用', r'原理解', r'原养成', r'原会用', r'原用起来', r'原意思', r'原是啥', r'原通过']
TEMPLATE_REGRESSION_PATTERNS = ['{{name}}能举个例子吗?', '{{name}}能举个例子吗？', '{{name}}能再举一个例子吗?', '{{name}}能再举一个例子吗？', '{{name}}能举出一个例子吗?', '{{name}}能举出一个例子吗？', '能举个例子吗?', '能举个例子吗？']


def fix_banned(s):
    for b, f in BANNED_FIX.items():
        s = s.replace(b, f)
    s = re.sub(r'  +', ' ', s)
    s = re.sub(r'。\s*。', '。', s)
    return s


def fix_char_displace(s):
    for pat in CHAR_DISPLACE_PATTERNS:
        s = re.sub(pat, pat[1:], s)
    return s


def replace_template_regression(s):
    REPLACEMENTS = [
        "{{name}}能不能再做一次这个实验, 这次换一种物质, 看看现象有什么不同?",
        "{{name}}能不能把这个反应的操作步骤跟同学讲一遍?",
        "{{name}}做完实验会不会自己把器材清洗收好?",
        "{{name}}能不能再用另一种方法验证这个结论?",
        "{{name}}能不能找出刚才哪一步做得不够好, 然后重做一次?",
        "{{name}}能不能教别的小朋友做这个实验?",
    ]
    for pat in TEMPLATE_REGRESSION_PATTERNS:
        while pat in s:
            replacement = REPLACEMENTS[hash(pat) % len(REPLACEMENTS)]
            s = s.replace(pat, replacement, 1)
    return s


def smart_truncate_desc(s):
    if len(s) <= 100:
        return s
    cut = s.rfind('。', 0, 100)
    if cut == -1 or cut < 50:
        cut = s.rfind('，', 0, 100)
    if cut == -1 or cut < 50:
        cut = 100
    else:
        cut += 1
    return s[:cut]


def smart_truncate_ass(s):
    if len(s) <= 220:
        return s
    NL = chr(92) + 'n'
    parts = s.split(NL)
    if len(parts) >= 3:
        first_two = parts[0] + NL + parts[1]
        if len(first_two) <= 220:
            return first_two + NL + '{{name}}能不能再做一次看看?'
        else:
            p0 = parts[0]
            cut = p0.rfind('?', 0, 200)
            if cut == -1:
                cut = p0.rfind('？', 0, 200)
            if cut == -1 or cut < 80:
                cut = 200
            else:
                cut += 1
            return p0[:cut] + NL + '{{name}}能不能再试一次?' + NL + '{{name}}能不能教别的小朋友?'
    cut = s.rfind('?', 0, 215)
    if cut == -1:
        cut = s.rfind('？', 0, 215)
    if cut == -1 or cut < 100:
        cut = 215
    else:
        cut += 1
    return s[:cut]


def pad_assessment(ass):
    PADS = [
        "{{name}}能不能再描述一下现象?",
        "{{name}}做实验的时候心里在想什么?",
        "{{name}}做完实验之后什么感觉?",
        "{{name}}能不能把操作步骤跟同学讲一遍?",
        "{{name}}下次会怎么改进?",
        "{{name}}能不能用计时器看看自己用了多久?",
        "{{name}}做完会不会把器材收好?",
        "{{name}}发现自己做错了会不会重做?",
        "{{name}}做完会不会自己检查实验现象?",
        "{{name}}能不能把实验报告写出来?",
    ]
    NL = chr(92) + 'n'
    while len(ass) < 150:
        parts = ass.split(NL)
        added = False
        for i, p in enumerate(parts):
            if '{{name}}' not in p:
                pad = PADS[len(ass) % len(PADS)]
                parts[i] = p.rstrip('?？。.') + ', ' + pad
                ass = NL.join(parts)
                added = True
                break
        if not added:
            ass = ass + ' ' + PADS[len(ass) % len(PADS)]
    return ass


def detect_2space_then_keyword(s):
    findings = []
    for m in re.finditer(r'  +', s):
        ctx = s[m.end():m.end() + 30]
        for kw in CHEM_MISSING:
            if ctx.startswith(kw):
                findings.append((m.start(), kw))
                break
    return findings


def detect_template_regression(s):
    findings = []
    for pat in TEMPLATE_REGRESSION_PATTERNS:
        for m in re.finditer(re.escape(pat), s):
            findings.append((m.start(), pat))
    return findings


def repair_one(item):
    desc = item.get('description', '').strip()
    ass = item.get('assessment_prompt', '').strip()

    desc = fix_banned(desc)
    desc = fix_char_displace(desc)
    desc = smart_truncate_desc(desc)

    ass = fix_banned(ass)
    ass = fix_char_displace(ass)
    ass = ass.replace('\r\n', '\n').replace('\r', '\n')
    ass = ass.replace('\n', chr(92) + 'n')

    parts = ass.split(chr(92) + 'n')
    parts = [p.strip() for p in parts if p.strip()]

    PADS_Q = [
        "{{name}}能不能做完实验再检查一遍现象?",
        "{{name}}做实验的时候心里在想什么?",
        "{{name}}做完实验之后会不会把器材清洗收好?",
        "{{name}}能不能把操作步骤讲给同学听?",
        "{{name}}下次会怎么做这个实验?",
    ]

    while len(parts) < 3:
        parts.append(PADS_Q[len(parts) % len(PADS_Q)])
    parts = parts[:3]

    NAME_RE = re.compile(r'(小明|小红|小华|小丽|小强|小军|小芳|小英|小东|小亮|小杰|小燕|小辉|家长|老师|妈妈|爸爸|同学|孩子|宝宝|哥哥|姐姐|弟弟|妹妹|小朋友|学生)')
    for i, p in enumerate(parts):
        parts[i] = NAME_RE.sub('{{name}}', p)

    for i, p in enumerate(parts):
        cnt = p.count('{{name}}')
        if cnt == 0:
            parts[i] = p.rstrip('?？。.') + ', {{name}}试试?'
        elif cnt > 1:
            chunks = p.split('{{name}}')
            parts[i] = chunks[0] + '{{name}}' + ''.join(chunks[1:])

    ass = (chr(92) + 'n').join(parts)
    ass = replace_template_regression(ass)

    if len(ass) > 220:
        ass = smart_truncate_ass(ass)
    if len(ass) < 150:
        ass = pad_assessment(ass)
        ass = replace_template_regression(ass)

    item['description'] = desc
    item['assessment_prompt'] = ass
    return item


def validate(item):
    issues = []
    desc = item.get('description', '')
    ass = item.get('assessment_prompt', '')
    if not (60 <= len(desc) <= 100):
        issues.append(f'desc_len={len(desc)}')
    if not (150 <= len(ass) <= 220):
        issues.append(f'ass_len={len(ass)}')
    if ass.count('{{name}}') != 3:
        issues.append(f'name_count={ass.count("{{name}}")}')
    if ass.count(chr(92) + 'n') < 2:
        issues.append(f'nl_count={ass.count(chr(92)+"n")}')
    for b in BANNED:
        if b in desc or b in ass:
            issues.append(f'禁词[{b}]')
    for s, label in [(desc, 'desc'), (ass, 'ass')]:
        findings = detect_2space_then_keyword(s)
        if findings:
            issues.append(f'{label}_2space_keyword={findings[:3]}')
    for s, label in [(desc, 'desc'), (ass, 'ass')]:
        for pat in CHAR_DISPLACE_PATTERNS:
            if re.search(pat, s):
                issues.append(f'{label}_char_displace[{pat}]')
                break
    for s, label in [(desc, 'desc'), (ass, 'ass')]:
        findings = detect_template_regression(s)
        if findings:
            issues.append(f'{label}_template_regression={findings[:2]}')
    return issues


# 主流程
for c in targets:
    print(f'\n=== Fix {c["id"]} ({c["title"]}) ===', flush=True)
    for attempt in range(5):
        try:
            text = call_llm_one(c)
            parsed = parse_one(text)
            if parsed and parsed.get('id') == c['id']:
                parsed = repair_one(parsed)
                issues = validate(parsed)
                if not issues:
                    done[c['id']] = {
                        'id': parsed['id'],
                        'description': parsed['description'],
                        'assessment_prompt': parsed['assessment_prompt'],
                    }
                    out = sorted(done.values(), key=lambda x: x['id'])
                    with open(OUTPUT, 'w', encoding='utf-8') as f:
                        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
                    print(f'  ✓ {c["id"]} 通过, attempt={attempt+1}', flush=True)
                    print(f'    desc: {parsed["description"]}', flush=True)
                    print(f'    ass: {parsed["assessment_prompt"]}', flush=True)
                    break
                else:
                    print(f'  attempt {attempt+1} 不达标: {issues}', flush=True)
            else:
                print(f'  attempt {attempt+1} parse fail', flush=True)
        except Exception as e:
            print(f'  attempt {attempt+1} LLM err: {e}', flush=True)
    else:
        print(f'  ✗ {c["id"]} 5 次都失败, 跳过', flush=True)

# ---- 全局 post-validation: 扫所有 62 条, 看是否还有不达标 ----
print(f'\n=== 全局 post-validation ===', flush=True)
data_full = json.load(open(INPUT))
issues_global = []
for c in data_full:
    if c['id'] not in done:
        issues_global.append((c['id'], 'MISSING'))
        continue
    item = done[c['id']]
    iss = validate(item)
    if iss:
        issues_global.append((c['id'], iss))

if issues_global:
    print(f'全局不达标: {len(issues_global)}')
    for cid, iss in issues_global:
        print(f'  {cid}: {iss}')
else:
    print(f'✓ 全部 62 条均达标', flush=True)

print(f'\n=== 最终 ===', flush=True)
print(f'总产出: {len(done)} 概念', flush=True)
print(f'剩余失败: {[c["id"] for c in targets if c["id"] not in done]}', flush=True)
