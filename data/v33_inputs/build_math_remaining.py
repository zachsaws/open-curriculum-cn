#!/usr/bin/env python3
"""
V3.3.2 数学 287 概念 LLM 化 — 批量调 LLM 生成 (description, assessment_prompt).

设计要点:
- 每批 30 概念, 一次 prompt 让 LLM 一次返回 30 条 JSON
- 287 概念分 ~10 批
- post-validation 在脚本内做完; 不达标的概念单独重试
- 输出格式与 math_v33_llm.json (PoC) 一致
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ============== 路径 ==============
# __file__ = /…/open-curriculum-cn/data/v33_inputs/build_math_remaining.py
# PROJECT = 项目根
PROJECT = Path(__file__).resolve().parent.parent.parent
IN = PROJECT / "data" / "v33_inputs" / "math_remaining_input.json"
OUT = PROJECT / "data" / "graph" / "math_v33_remaining_llm.json"
CACHE = PROJECT / "data" / "v33_inputs" / "_math_remaining_cache.json"

# ============== LLM 配置 ==============
API_KEY = "sk-cp-wf9YRvboamc0VV1smntYd2CyTW8ehSo6VmT6s3AqpfNyZHkCTFE_IkFLlPrNkYMm6XwidC1XVn6uIf8atNzBGXjegdWlEVft8782guRS9w3y0BoBqG-3uHU"
BASE_URL = "https://api.minimaxi.com/anthropic"
MODEL = "MiniMax-M2.7"
MAX_TOKENS = 16000
TIMEOUT = 240

# ============== Banned ==============
BANNED = [
    "理解", "培养", "掌握", "运用", "知识点", "课标", "教学目标",
    "含义", "定义", "本概念", "该概念", "本节", "本文", "通过本",
    "课标要求", "具体含义",
]
TEMPLATES = [
    r"在.{1,8}课上[，,]",
    r"用自己的话解释",
    r"独立完成相关题目",
    r"举出一个生活中的例子",
]

# ============== 校验 ==============
def has_banned(s: str) -> list[str]:
    hits = [w for w in BANNED if w in s]
    for tpl in TEMPLATES:
        if re.search(tpl, s):
            hits.append(f"TPL:{tpl}")
    return hits

def check(desc: str, ass: str) -> tuple[bool, list[str]]:
    """返回 (是否达标, 不达标原因列表)"""
    reasons = []
    dlen = len(desc)
    alen = len(ass)
    ncount = ass.count("{{name}}")
    nlcount = ass.count("\n")
    bd = has_banned(desc)
    ba = has_banned(ass)
    if not (60 <= dlen <= 100):
        reasons.append(f"desc_len={dlen}")
    if not (150 <= alen <= 220):
        reasons.append(f"ass_len={alen}")
    if ncount != 3:
        reasons.append(f"name={ncount}")
    if nlcount < 2:
        reasons.append(f"newline={nlcount}")
    if bd:
        reasons.append(f"banned_desc={bd}")
    if ba:
        reasons.append(f"banned_ass={ba}")
    return (len(reasons) == 0, reasons)

# ============== LLM 调用 ==============
def call_llm(system: str, user: str, max_retries: int = 2) -> str:
    """调 LLM 返回 text (排除 thinking block)"""
    url = f"{BASE_URL}/v1/messages"
    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": API_KEY,
                    "anthropic-version": "2023-06-01",
                },
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                data = json.loads(r.read().decode("utf-8"))
            # 提取 text block
            for blk in data.get("content", []):
                if blk.get("type") == "text":
                    return blk.get("text", "")
            return ""
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")[:300]
            last_err = f"HTTP {e.code}: {err_body}"
            print(f"  [HTTP {e.code}] {err_body[:200]}")
            time.sleep(3 + attempt * 2)
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            print(f"  [ERR] {last_err[:200]}")
            time.sleep(2 + attempt * 2)
    raise RuntimeError(f"LLM call failed after retries: {last_err}")

# ============== 解析 LLM 输出的 JSON ==============
def parse_json_array(text: str) -> list[dict]:
    """从 LLM 输出里抽取 JSON 数组"""
    text = text.strip()
    # 去掉 markdown code fence
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
    # 尝试直接 parse
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict) and "concepts" in obj:
            return obj["concepts"]
    except json.JSONDecodeError:
        pass
    # 找最外层 [ ... ] (处理 LLM 在前后加文字)
    m = re.search(r"\[\s*\{", text)
    if m:
        start = m.start()
        # 从 start 算起, 找匹配的 ]
        depth = 0
        in_str = False
        esc = False
        end = -1
        for i in range(start, len(text)):
            ch = text[i]
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"' and not esc:
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > 0:
            try:
                obj = json.loads(text[start:end])
                if isinstance(obj, list):
                    return obj
            except json.JSONDecodeError:
                pass
    raise RuntimeError(f"Failed to parse JSON array from LLM output ({len(text)} chars): {text[:200]!r}")

# ============== 提示词 ==============
SYSTEM = """你是 V3.3.2 数学内容 LLM 化工程师, 任务: 为每个数学概念生成"人话级"的 description 和 assessment_prompt.

# 严格要求

## description 风格
- 长度 60-100 字 (含标点), 1 段, 中间可用「」, 不允许换行
- 用具体场景代替抽象定义 — "在披萨上切一半 = 1/2" 而非"理解分数的概念"
- 避免绝对化承诺 — 不要"一定/必然/肯定"等词
- 要反直觉, 要画面感 — 优于课标原文 (例: "3 不只是 3 而是 3 个百" 优于 "理解位值的意义")
- 用具体物品代替抽象: 苹果/披萨/计数器/算盘/教室/超市/操场/积木/小棒/钱币/钟面

## assessment_prompt 风格 (核心)
- 长度 150-220 字
- 必须正好 3 个评估问题, 每问 1 行, 行间用 \n (反斜杠加 n) 分隔
- 每问必须含 {{name}} 占位符 (1 个, 不能多, 不能少)
- 场景必须具体: 含具体数字/具体物品/具体动作/具体对话 — 拒绝"理解 X 这一概念, 能否独立完成相关题目?" 这种空问
- 要区分度: 3 问难度递进 — 第 1 问直接识别, 第 2 问操作/反例, 第 3 问解释/迁移
- 中文要自然: 用"能不能 / 会不会" 优于 "能否"

## 禁词 (BANNED, 0 容忍)
- 理解 / 培养 / 掌握 / 运用 / 知识点 / 课标 / 教学目标 / 含义 / 定义 / 本概念 / 该概念 / 本节 / 本文 / 通过本 / 课标要求 / 具体含义

## 模板词 (BANNED)
- "在 X 课上, {name} 能否..."
- "用自己的话解释 X 的含义"
- "独立完成相关题目"
- "举出一个生活中的例子"

# 标杆 (这就是底线, 不要低于此)

概念: M_G1_NS_02 位值
description: 同一个数字「2」,放在个位是 2、放在十位是 20、放在百位是 200——位置变了,值就变了。孩子写「345」时知道 3 不只是 3 而是 3 个百,这就是位值感。
assessment: 看到数字 506,{{name}}能不能马上说「5 在百位上所以是 500,0 在十位上是 0 个十」?\n把 4 写在十位、把 4 写在个位组成两个数(如 44 和 404),{{name}}能不能解释为什么这两个 4 差这么多?\n在计数器上拨珠子,{{name}}能不能拨出一个 4 位数后,再拨一个 4 位数,自己说出「我移了一个珠子,从 1000 变成 100」?

# 输出格式 (严格 JSON 数组, 不要 markdown, 不要多余文字)
[
  {"id": "M_xxx_xx", "description": "...", "assessment_prompt": "...\\n...\\n..."},
  ...
]
"""

def make_user_prompt(batch: list[dict]) -> str:
    items = []
    for c in batch:
        title = c["title"]
        # 用 title 即可, 必要时参考 summary
        summ = c.get("summary", "")
        kp = "、".join(c.get("key_points", []) or [])[:120]
        # 控制长度
        age = f"年龄 {c.get('age_range_start','')}-{c.get('age_range_end','')}"
        items.append({
            "id": c["id"],
            "title": title,
            "summary": summ,
            "key_points": kp,
            "age": age,
        })
    return f"请为以下 {len(batch)} 个数学概念生成 (description, assessment_prompt), 严格按 JSON 数组返回, 每条必须有 id/description/assessment_prompt 三个字段:\n\n```\n{json.dumps(items, ensure_ascii=False, indent=2)}\n```\n\n直接返回 JSON 数组, 不要解释, 不要 markdown code fence."

# ============== 写文件 ==============
def write_output(results: list[dict], input_items: list[dict]) -> None:
    """results 顺序与 input 一致; 每条只含 id/description/assessment_prompt"""
    out = []
    for item in input_items:
        iid = item["id"]
        if iid in results and "description" in results[iid]:
            d = results[iid]["description"]
            a = results[iid]["assessment_prompt"]
        else:
            d = f"⚠️ MISSING: {item['title']}"
            a = f"⚠️ MISSING: {{name}}能不能处理 {item['title']}?\\n⚠️ MISSING: 这个概念未生成, 需手动补。\\n⚠️ MISSING: 报告这条给开发者。"
        out.append({"id": iid, "description": d, "assessment_prompt": a})
    doc = {
        "version": "v3.3.2-math-remaining",
        "subject": "math",
        "conceptCount": len(out),
        "generatedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "concepts": out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"[WRITE] {OUT} ({OUT.stat().st_size:,} bytes, {len(out)} concepts)")

# ============== 主流程 ==============
def main():
    with open(IN, encoding="utf-8") as f:
        inp = json.load(f)
    print(f"[INPUT] {len(inp)} concepts from {IN.name}")

    # 加载缓存 (允许断点续传)
    cache: dict[str, dict] = {}
    if CACHE.exists():
        try:
            with open(CACHE, encoding="utf-8") as f:
                cache = json.load(f)
            print(f"[CACHE] loaded {len(cache)} from {CACHE.name}")
        except Exception as e:
            print(f"[CACHE] load failed: {e}")
            cache = {}

    # 切批
    BATCH_SIZE = 25  # 25 概念/批 — 保守点, 避免输出超 16k tokens
    batches = [inp[i:i + BATCH_SIZE] for i in range(0, len(inp), BATCH_SIZE)]
    print(f"[BATCH] {len(batches)} batches of ~{BATCH_SIZE}")

    rewrite_count = 0
    for bi, batch in enumerate(batches):
        ids = [c["id"] for c in batch]
        # 全部已在 cache 且全 OK -> 跳过
        all_ok = True
        for c in batch:
            if c["id"] not in cache:
                all_ok = False
                break
            ok, _ = check(cache[c["id"]]["description"], cache[c["id"]]["assessment_prompt"])
            if not ok:
                all_ok = False
                break
        if all_ok:
            print(f"[BATCH {bi+1}/{len(batches)}] skip (cached OK) — {ids[0]}..{ids[-1]}")
            continue

        print(f"\n[BATCH {bi+1}/{len(batches)}] {len(batch)} concepts: {ids[0]}..{ids[-1]}")
        t0 = time.time()
        try:
            user_prompt = make_user_prompt(batch)
            text = call_llm(SYSTEM, user_prompt)
            parsed = parse_json_array(text)
            print(f"  [LLM OK] {len(parsed)} entries, {time.time()-t0:.1f}s, raw_len={len(text)}")
        except Exception as e:
            print(f"  [BATCH ERR] {e}")
            # 整批失败 -> 每条单独重试
            parsed = []
            for c in batch:
                try:
                    user_prompt = make_user_prompt([c])
                    text = call_llm(SYSTEM, user_prompt)
                    single = parse_json_array(text)
                    if single:
                        parsed.extend(single)
                except Exception as e2:
                    print(f"    [SINGLE ERR] {c['id']}: {e2}")
                time.sleep(0.5)

        # 收集结果
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            eid = entry.get("id")
            if not eid:
                continue
            d = entry.get("description", "").strip()
            a = entry.get("assessment_prompt", "").strip()
            if not d or not a:
                continue
            # 处理 LLM 偶发的 \n 双重转义
            a = a.replace("\\n", "\n")
            d = d.replace("\\n", " ")
            cache[eid] = {"description": d, "assessment_prompt": a}

        # 保存中间缓存
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"  [CACHE] saved ({len(cache)} entries)")
        time.sleep(0.5)

    # ===== 重试不达标的概念 (单独生成) =====
    print("\n=== Pass 2: 重试不达标 ===")
    fails = []
    for c in inp:
        if c["id"] not in cache:
            fails.append((c["id"], ["missing"]))
            continue
        d = cache[c["id"]]["description"]
        a = cache[c["id"]]["assessment_prompt"]
        ok, reasons = check(d, a)
        if not ok:
            fails.append((c["id"], reasons))
    print(f"  fails before rewrite: {len(fails)} / {len(inp)}")

    for i, (iid, reasons) in enumerate(fails):
        item = next((c for c in inp if c["id"] == iid), None)
        if not item:
            continue
        if i % 20 == 0:
            print(f"  rewriting {i+1}-{min(i+20, len(fails))} / {len(fails)}")
        ok = False
        for attempt in range(3):
            try:
                user_prompt = make_user_prompt([item])
                # 强调约束
                user_prompt += f"\n\n注意: 这是第 {attempt+1} 次重写, 上次没通过的原因: {reasons}. 严格满足: description 60-100 字, assessment 150-220 字, 正好 3 个 {{name}}, 至少 2 个 \\n, 0 个禁词."
                text = call_llm(SYSTEM, user_prompt, max_retries=1)
                parsed = parse_json_array(text)
                for entry in parsed:
                    if entry.get("id") == iid:
                        d = entry.get("description", "").strip().replace("\\n", " ")
                        a = entry.get("assessment_prompt", "").strip().replace("\\n", "\n")
                        if d and a:
                            cache[iid] = {"description": d, "assessment_prompt": a}
                            ok_now, new_reasons = check(d, a)
                            if ok_now:
                                ok = True
                                rewrite_count += 1
                                break
                            else:
                                reasons = new_reasons
                if ok:
                    break
            except Exception as e:
                print(f"    [REWRITE ERR] {iid} attempt {attempt+1}: {e}")
            time.sleep(0.3)
        if not ok:
            print(f"  [STILL FAIL] {iid}: {reasons}")

        # 每 20 条保存一次
        if (i + 1) % 20 == 0:
            with open(CACHE, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)

    # 最终保存
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    # 写 output
    write_output(cache, inp)

    # ===== 最终统计 =====
    total = len(inp)
    succ = 0
    desc_lens = []
    ass_lens = []
    banned_total = 0
    fail_list = []
    for c in inp:
        if c["id"] in cache:
            d = cache[c["id"]]["description"]
            a = cache[c["id"]]["assessment_prompt"]
            ok, reasons = check(d, a)
            if ok:
                succ += 1
            else:
                fail_list.append((c["id"], c["title"], reasons))
            desc_lens.append(len(d))
            ass_lens.append(len(a))
            banned_total += len(has_banned(d)) + len(has_banned(a))
    print(f"\n=== 报告 ===")
    print(f"成功: {succ} / {total}")
    if desc_lens:
        print(f"平均 description 字数: {sum(desc_lens)/len(desc_lens):.1f}")
        print(f"平均 assessment_prompt 字数: {sum(ass_lens)/len(ass_lens):.1f}")
    print(f"禁词命中数: {banned_total}")
    print(f"重写次数: {rewrite_count}")
    print(f"输出文件: {OUT} ({OUT.stat().st_size:,} bytes)")
    if fail_list:
        print(f"\n仍未达标 ({len(fail_list)}):")
        for iid, t, r in fail_list[:20]:
            print(f"  {iid} {t}: {r}")
        if len(fail_list) > 20:
            print(f"  ... 还有 {len(fail_list) - 20} 条")

    return 0 if not fail_list else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
