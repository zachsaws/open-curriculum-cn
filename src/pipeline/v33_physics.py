"""
V3.3.1 Physics LLM 化 — 121 物理概念生成 description + assessment_prompt

输入: data/v33_inputs/physics_input.json
输出: data/graph/physics_v33_llm.json (JSON list)

工作流:
1. 读 input
2. 分批 (每批 10 个) 调 LLM
3. 后处理: 把 assessment_prompt 里的真换行统一替换为字面 \\n
4. 校验: desc 60-100, ass 150-220, {{name}}=3, \\n>=2, 禁词=0
5. 不达标的概念重写 (单条重写调用)
6. 写最终 JSON
"""
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).parent.parent.parent
IN = ROOT / "data" / "v33_inputs" / "physics_input.json"
OUT = ROOT / "data" / "graph" / "physics_v33_llm.json"

API_URL = "https://agent.minimaxi.com/mavis/api/v1/llm/v1/messages"
MODEL = "MiniMax-M3"

# 禁词 (BANNED, 任何位置命中都算违规)
BANNED = [
    "理解", "培养", "掌握", "运用", "知识点", "课标", "教学目标",
    "含义", "定义", "本概念", "该概念", "本节", "本文", "通过本",
    "课标要求", "具体含义",
]
# 禁模板句 (substring 匹配)
BANNED_TEMPLATES = [
    "在 X 课上",
    "在物理课上",
    "在数学课上",
    "在生物课上",
    "在化学课上",
    "用自己的话解释",
    "独立完成相关题目",
    "举出一个生活中的例子",
    "举出生活中的例子",
]


def load_token() -> str:
    with open(os.path.expanduser("~/.mavis/local-runtime.auth.json")) as f:
        auth = json.load(f)
    return auth["auth"]["accessToken"]


def call_llm(system: str, user: str, max_tokens: int = 2000) -> str:
    token = load_token()
    headers = {
        "x-api-key": token,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
    }
    body = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    last_err = None
    for attempt in range(3):
        try:
            r = httpx.post(API_URL, headers=headers, json=body, timeout=120)
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                time.sleep(2 + attempt * 2)
                continue
            j = r.json()
            return j["content"][0]["text"]
        except Exception as e:
            last_err = str(e)
            time.sleep(2 + attempt * 2)
    raise RuntimeError(f"LLM 调用失败: {last_err}")


def strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        # remove first ``` line and last ``` line
        lines = t.split("\n")
        # find the first line that ends with ``` and is just ```
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines)
    return t.strip()


def extract_json(text: str) -> Any:
    t = strip_code_fence(text)
    # try direct
    try:
        return json.loads(t)
    except Exception:
        pass
    # try to find first [ or {
    for opener, closer in [("[", "]"), ("{", "}")]:
        i = t.find(opener)
        if i < 0:
            continue
        depth = 0
        in_str = False
        esc = False
        for j in range(i, len(t)):
            c = t[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    return json.loads(t[i:j + 1])
    raise RuntimeError(f"无法解析 JSON: {t[:200]}")


def has_banned(text: str) -> list[str]:
    hits = []
    for w in BANNED:
        if w in text:
            hits.append(w)
    for t in BANNED_TEMPLATES:
        if t in text:
            hits.append(f"模板:{t}")
    return hits


def validate(d: str, a: str) -> dict:
    """返回 { ok, errors, stats }"""
    errors = []
    # description
    d_len = len(d)
    if d_len < 60 or d_len > 100:
        errors.append(f"desc 长度 {d_len} 不在 60-100")
    if "\n" in d:
        errors.append("desc 含换行")
    # assessment
    a_len = len(a)
    if a_len < 150 or a_len > 220:
        errors.append(f"ass 长度 {a_len} 不在 150-220")
    name_n = a.count("{{name}}")
    if name_n != 3:
        errors.append(f"ass {{name}} 出现 {name_n} 次 (应=3)")
    # \n count
    bs_n = a.count("\\n")
    real_n = a.count("\n")
    if bs_n < 2:
        errors.append(f"ass \\\\n 出现 {bs_n} 次 (应≥2)")
    if real_n > 0:
        errors.append(f"ass 含真换行 {real_n} 次")
    # banned
    bh = has_banned(d) + has_banned(a)
    if bh:
        errors.append(f"禁词命中: {bh}")
    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "stats": {
            "desc_len": d_len,
            "ass_len": a_len,
            "name_n": name_n,
            "bs_n": bs_n,
        },
    }


def split_by_name(a: str) -> list[str]:
    """按 {{name}} 切分, 每个 {{name}} 是一问的开头. 返回 3 段 (期望)."""
    positions = []
    i = 0
    needle = "{{name}}"
    while True:
        j = a.find(needle, i)
        if j < 0:
            break
        positions.append(j)
        i = j + len(needle)
    if len(positions) != 3:
        return []
    chunks = []
    # 第一段: 从 0 到 第二个 {{name}} 起点
    chunks.append(a[0:positions[1]])
    # 第二段: 从 第二个 {{name}} 起点 到 第三个 {{name}} 起点
    chunks.append(a[positions[1]:positions[2]])
    # 第三段: 从 第三个 {{name}} 起点 到 结尾
    chunks.append(a[positions[2]:])
    return chunks


def normalize_newlines(a: str) -> str:
    """把各种分隔形式归一为字面 \\n (2 字符: 反斜杠+n).

    LLM 经常不按预期输出分隔符. 这里做宽容处理:
    1. 真换行 -> \\n (2 字符)
    2. {{name}} 出现 3 次时, 按 {{name}} 切分成 3 段, 用 \\n 连接 (这是最稳的)
    3. 如果 {{name}} 不是 3 次, 退化为找 ?后空白+{{name}} 模式插 \n
    """
    # 先归一真换行为 2 字符 \n
    a = a.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
    # 多个 \n 合并
    a = re.sub(r"(?:\\n)+", "\\n", a)
    # 如果 {{name}} 恰好 3 次, 按它切分
    if a.count("{{name}}") == 3:
        chunks = split_by_name(a)
        if len(chunks) == 3:
            return "\\n".join(chunks)
    # 否则: 找 ?后空白+{{name}} 模式
    a = re.sub(r"([?？])\s+(?=\{\{name\}\})", r"\1\\n", a)
    a = re.sub(r"(?:\\n)+", "\\n", a)
    return a


SYSTEM = """你是 V3.3.1 内容 LLM 化工程师, 给物理概念写 description 和 assessment_prompt.

# description 规则
- 长度严格 60-100 字 (含标点), 1 段, 中间可用「」, 不允许换行
- 用具体场景代替抽象定义 (例: "用刻度尺量课本短边, 能不能读出 18.4 cm?" 而非 "理解长度测量")
- 不用绝对化承诺 (一定/必然/肯定)
- 反直觉 + 画面感, 优于课标原文

# assessment_prompt 规则
- 长度严格 150-220 字 (含标点)
- 正好 3 个评估问题, 每问 1 行
- 每问必须含字面占位符 {{name}} 1 次 (两个花括号包 name, 不能用"小明""孩子"等替代)
- 3 问难度递进: 第 1 问直接识别, 第 2 问操作/反例/计算, 第 3 问解释/迁移/设计
- 物理要"实验/具体现象" (例: "用尺子量课本短边, {{name}} 能不能读出 25.4 cm?"), 避免"理解物理量"
- 场景要具体: 含具体数字/具体物品/具体动作/具体对话

# 禁词 (BANNED, 任何位置命中都算违规)
理解 / 培养 / 掌握 / 运用 / 知识点 / 课标 / 教学目标 / 含义 / 定义 / 本概念 / 该概念 / 本节 / 本文 / 通过本 / 课标要求 / 具体含义

# 禁模板句 (禁止使用)
- "在 X 课上, {name} 能否..."
- "用自己的话解释 X 的含义"
- "独立完成相关题目"
- "举出一个生活中的例子"

# 输出格式
- 严格 JSON 数组, 每个元素: {"id": "...", "description": "...", "assessment_prompt": "..."}
- 不要 markdown 包裹, 不要解释
- description 不要换行
- assessment_prompt 3 问之间必须用字面 \\n (反斜杠加 n, 2 个字符) 隔开, 不能用真换行
- {{name}} 必须原样保留 3 次, 不能改成具体人名
- 单条 description 控制在 60-100 字, 单条 assessment_prompt 控制在 150-220 字
"""


def build_batch_prompt(concepts: list[dict]) -> str:
    """为一批概念构建 user prompt"""
    parts = ["为下列物理概念生成 description 和 assessment_prompt, 返回 JSON 数组:\n"]
    for c in concepts:
        parts.append(
            f"- id: {c['id']}\n"
            f"  title: {c['title']}\n"
            f"  summary: {c['summary']}\n"
            f"  type: {c['type']}, grade: {c['grade_start']}\n"
        )
    parts.append(
        "\n返回格式 (示例, 一个元素):\n"
        '{"id":"P_XX_XX","description":"具体场景描述 60-100 字, 不换行","assessment_prompt":"{{name}}能不能...？\\n{{name}}能不能...？\\n{{name}}能不能...？"}\n'
    )
    return "\n".join(parts)


def build_rewrite_prompt(c: dict, errs: list[str]) -> str:
    """为单个失败概念构建重写 prompt, 把具体违规列出来"""
    parts = [
        f"为下面这个物理概念重写 description 和 assessment_prompt, 之前版本不达标:\n",
        f"- id: {c['id']}",
        f"- title: {c['title']}",
        f"- summary: {c['summary']}",
        f"- type: {c['type']}, grade: {c['grade_start']}",
        f"\n上一版问题: {'; '.join(errs)}",
        f"\n请严格按长度和禁词要求重写, 返回 JSON: {{\"id\":\"{c['id']}\",\"description\":\"...\",\"assessment_prompt\":\"...\"}}",
    ]
    return "\n".join(parts)


def generate_batch(concepts: list[dict], retry: int = 0) -> list[dict]:
    """调一次 LLM 生成一批, 返回 [{id, description, assessment_prompt}]"""
    user = build_batch_prompt(concepts)
    raw = call_llm(SYSTEM, user, max_tokens=4000)
    data = extract_json(raw)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise RuntimeError(f"返回不是 list: {type(data)}")
    out = []
    for item in data:
        if "id" not in item or "description" not in item or "assessment_prompt" not in item:
            continue
        d = item["description"].strip()
        a = item["assessment_prompt"].strip()
        # 强制转 \n
        a = normalize_newlines(a)
        out.append({
            "id": item["id"],
            "description": d,
            "assessment_prompt": a,
        })
    return out


def generate_single(c: dict, errs: list[str]) -> dict:
    user = build_rewrite_prompt(c, errs)
    raw = call_llm(SYSTEM, user, max_tokens=800)
    data = extract_json(raw)
    if isinstance(data, list):
        data = data[0] if data else {}
    d = data.get("description", "").strip()
    a = data.get("assessment_prompt", "").strip()
    a = normalize_newlines(a)
    return {"id": c["id"], "description": d, "assessment_prompt": a}


def main():
    with open(IN, encoding="utf-8") as f:
        concepts = json.load(f)
    print(f"读入 {len(concepts)} 个概念")

    # Step 1: 分批生成
    BATCH = 10
    batches = [concepts[i:i + BATCH] for i in range(0, len(concepts), BATCH)]
    print(f"分 {len(batches)} 批, 每批 {BATCH} 个")

    results: dict[str, dict] = {}
    raw_rounds: dict[str, list[dict]] = {}  # id -> all generated versions

    for bi, batch in enumerate(batches):
        print(f"\n=== 批 {bi+1}/{len(batches)} ===")
        for r in batch:
            raw_rounds.setdefault(r["id"], [])
        attempts = 0
        ok_in_batch: set[str] = set()
        while attempts < 2 and len(ok_in_batch) < len(batch):
            attempts += 1
            try:
                out = generate_batch(batch)
            except Exception as e:
                print(f"  批 {bi+1} 第 {attempts} 次解析失败: {e}")
                time.sleep(2)
                continue
            # validate each
            for item in out:
                cid = item["id"]
                if cid in ok_in_batch:
                    continue
                v = validate(item["description"], item["assessment_prompt"])
                raw_rounds[cid].append({"version": attempts, **item, "validate": v})
                if v["ok"]:
                    results[cid] = item
                    ok_in_batch.add(cid)
        print(f"  批 {bi+1} 一次成功率: {len(ok_in_batch)}/{len(batch)}")

    # Step 2: 失败的逐条重写
    failed_ids = [c["id"] for c in concepts if c["id"] not in results]
    print(f"\n=== 重写阶段: {len(failed_ids)} 条待重写 ===")
    for cid in failed_ids:
        c = next(cc for cc in concepts if cc["id"] == cid)
        last = raw_rounds[cid][-1] if raw_rounds.get(cid) else None
        errs = last["validate"]["errors"] if last else ["未生成"]
        # 最多重写 3 次
        for attempt in range(1, 4):
            try:
                item = generate_single(c, errs)
            except Exception as e:
                print(f"  {cid} 重写第 {attempt} 次异常: {e}")
                time.sleep(1)
                continue
            v = validate(item["description"], item["assessment_prompt"])
            raw_rounds[cid].append({"version": f"rewrite-{attempt}", **item, "validate": v})
            if v["ok"]:
                results[cid] = item
                print(f"  {cid} 重写第 {attempt} 次通过")
                break
            errs = v["errors"]
            print(f"  {cid} 重写第 {attempt} 次仍不达标: {errs}")
        else:
            print(f"  {cid} 3 次重写均失败, 保留最佳")

    # Step 3: 最终拼装
    final = []
    final_stats = {"ok": 0, "fail": 0, "desc_lens": [], "ass_lens": [], "banned": []}
    for c in concepts:
        cid = c["id"]
        if cid not in results:
            # use last attempt (even if invalid)
            last = raw_rounds[cid][-1] if raw_rounds.get(cid) else None
            if last:
                results[cid] = {"id": cid, "description": last["description"], "assessment_prompt": last["assessment_prompt"]}
            else:
                results[cid] = {"id": cid, "description": "占位" * 30, "assessment_prompt": "{{name}}问1?\n{{name}}问2?\n{{name}}问3?"}
            final_stats["fail"] += 1
        else:
            final_stats["ok"] += 1
        item = results[cid]
        d = item["description"]
        a = item["assessment_prompt"]
        final_stats["desc_lens"].append(len(d))
        final_stats["ass_lens"].append(len(a))
        for w in has_banned(d) + has_banned(a):
            final_stats["banned"].append((cid, w))
        # 拼接输出: 原 input 字段 + description + assessment_prompt
        merged = dict(c)  # copy all original fields
        merged["description"] = d
        merged["assessment_prompt"] = a
        final.append(merged)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"\n写入 {OUT}: {len(final)} 条")

    # Step 4: 最终验证
    print("\n=== 最终验证 ===")
    err_count = 0
    for item in final:
        d = item["description"]
        a = item["assessment_prompt"]
        v = validate(d, a)
        if not v["ok"]:
            err_count += 1
            print(f"  {item['id']} 仍不达标: {v['errors']}")
    print(f"最终不达标数: {err_count}")

    # 统计
    desc_lens = [len(it["description"]) for it in final]
    ass_lens = [len(it["assessment_prompt"]) for it in final]
    print(f"成功 {final_stats['ok']}/{len(final)}")
    print(f"description 平均 {sum(desc_lens)/len(desc_lens):.1f} 字, min {min(desc_lens)}, max {max(desc_lens)}")
    print(f"assessment  平均 {sum(ass_lens)/len(ass_lens):.1f} 字, min {min(ass_lens)}, max {max(ass_lens)}")
    print(f"禁词命中 {len(final_stats['banned'])}")
    print(f"最终不达标 {err_count}")


if __name__ == "__main__":
    main()
