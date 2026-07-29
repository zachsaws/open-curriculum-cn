"""
V4.0.2 智能诊断 PoC

输入: 概念 + 5 题答题结果 (或自评答对率)
算法: BFS 找先决 + 自适应阈值按难度 + 距离+难度排序复习路径
输出: 薄弱/巩固/已掌握 + 复习顺序 + 人话解释

设计原则 (天祥 2026-07-29 拍板):
- 多入口渐进式: 5 题测试主入口 (强) + 手输答对率副入口 (弱)
- 自适应阈值按概念难度: 1-2 难 80% / 3 难 70% / 4-5 难 50% 算"薄弱"
- 不持久化 (V4.0.3 才做) — 本次纯服务端推理
- PoC 范围: math 5 核心考点 (勾股/一元二次/二次函数/相似/圆)
"""
from collections import deque
from typing import Optional, List, Dict, Any


# 难度 1-5 → 薄弱阈值
# 简单题 80% 才算掌握, 难题 50% 也算"勉强" (因为正常人也大量不会)
DIFFICULTY_THRESHOLDS = {
    1: {"weak": 80, "consolidate": 95},  # 基础: 答错 1 道就是薄弱
    2: {"weak": 80, "consolidate": 95},
    3: {"weak": 70, "consolidate": 90},  # 核心考点: 大部分要会
    4: {"weak": 60, "consolidate": 80},  # 拔高: 答对 3/5 已经 OK
    5: {"weak": 50, "consolidate": 70},  # 压轴: 答对一半算掌握
}


def weak_threshold(difficulty: int) -> int:
    """薄弱阈值: 答对率低于此值算'薄弱'"""
    return DIFFICULTY_THRESHOLDS.get(difficulty, DIFFICULTY_THRESHOLDS[3])["weak"]


def consolidate_threshold(difficulty: int) -> int:
    """巩固阈值: 答对率低于此值算'巩固中' (薄弱但有基础)"""
    return DIFFICULTY_THRESHOLDS.get(difficulty, DIFFICULTY_THRESHOLDS[3])["consolidate"]


def _bfs_prereqs_with_depth(concept_id: str, adj_to: dict) -> Dict[str, int]:
    """BFS 找所有先决 + 距离 (0=直接先决)"""
    visited = {}  # id -> distance
    queue = deque([(concept_id, 0)])
    while queue:
        cur, dist = queue.popleft()
        for pre in adj_to.get(cur, []):
            if pre not in visited and pre != concept_id:
                visited[pre] = dist + 1
                queue.append((pre, dist + 1))
    return visited


def _find_concept_by_id(nodes: list, concept_id: str) -> Optional[dict]:
    for n in nodes:
        if n.get("id") == concept_id:
            return n
    return None


def diagnose(
    concept_id: str,
    nodes: list,
    adj_to: dict,
    score: Optional[float] = None,
    answers: Optional[List[bool]] = None,
) -> Dict[str, Any]:
    """
    智能诊断主函数

    入参二选一:
    - score: float 0-1 (手输答对率副入口)
    - answers: List[bool] 长度 5 (5 题测试主入口)

    返回:
    {
      concept_id, concept_title, subject, difficulty, grade_range,
      score, status,  # "薄弱" / "巩固" / "已掌握"
      weak_concepts,  # BFS 先决链 [{id, title, distance, difficulty}, ...]
      recommend_path,  # 复习顺序 (按距离+难度排序)
      human_explanation,  # 人话解释 (含 action_items)
    }
    """
    concept = _find_concept_by_id(nodes, concept_id)
    if not concept:
        return {"error": f"概念不存在: {concept_id}"}

    # 1. 算 score
    if answers is not None:
        if len(answers) != 5:
            return {"error": f"answers 必须 5 道, 实际 {len(answers)} 道"}
        score = sum(1 for a in answers if a) / 5.0
    elif score is None:
        return {"error": "必须传 score 或 answers"}
    score_pct = round(score * 100)

    # 2. 算 status
    d = concept.get("difficulty") or 3
    weak_t = weak_threshold(d)
    cons_t = consolidate_threshold(d)
    if score_pct < weak_t:
        status = "薄弱"
    elif score_pct < cons_t:
        status = "巩固"
    else:
        status = "已掌握"

    # 3. BFS 找先决链 + 距离
    prereq_dist = _bfs_prereqs_with_depth(concept_id, adj_to)
    prereq_nodes = []
    for pre_id, dist in prereq_dist.items():
        pre = _find_concept_by_id(nodes, pre_id)
        if pre:
            prereq_nodes.append({
                "id": pre["id"],
                "title": pre.get("title", ""),
                "distance": dist,
                "difficulty": pre.get("difficulty"),
                "subject": pre.get("subject"),
            })

    # 4. 复习路径: 距离近 + 难度低的优先 (基础先打牢)
    # sort: (distance ASC, difficulty ASC)
    recommend_path = sorted(prereq_nodes, key=lambda x: (x["distance"], x.get("difficulty") or 3))
    # 只取前 8 个 (UI 不要太长)
    recommend_path = recommend_path[:8]

    # 5. 人话解释
    title = concept.get("title", "")
    grade_range = f"{concept.get('grade_start', '')}-{concept.get('grade_end', '')}年级"
    subject_cn = {
        "math": "数学", "chinese": "语文", "english": "英语", "physics": "物理",
        "chemistry": "化学", "biology": "生物", "history": "历史", "geography": "地理",
        "morality_law": "道德与法治", "science": "科学", "info_tech": "信息科技",
    }.get(concept.get("subject", ""), concept.get("subject", ""))

    human = _build_human_explanation(
        status=status,
        score_pct=score_pct,
        title=title,
        subject_cn=subject_cn,
        grade_range=grade_range,
        d=d,
        recommend_path=recommend_path,
        concept=concept,
    )

    return {
        "concept_id": concept_id,
        "concept_title": title,
        "subject": concept.get("subject"),
        "subject_cn": subject_cn,
        "difficulty": d,
        "grade_range": grade_range,
        "score": score,
        "score_pct": score_pct,
        "status": status,
        "weak_threshold": weak_t,
        "consolidate_threshold": cons_t,
        "weak_concepts_count": len(prereq_nodes),
        "weak_concepts": prereq_nodes[:10],  # 给前 10 个最相关的
        "recommend_path": recommend_path,
        "human_explanation": human,
    }


def _build_human_explanation(
    status: str,
    score_pct: int,
    title: str,
    subject_cn: str,
    grade_range: str,
    d: int,
    recommend_path: list,
    concept: dict,
) -> Dict[str, Any]:
    """构造人话解释: 总结 + 为什么 + 怎么补"""
    summary = ""
    why = ""
    actions = []

    if status == "薄弱":
        summary = f"「{title}」对你来说还有点早，{score_pct}% 的答对率说明基础没打牢。"
        why = (
            f"{title}是{subject_cn}{grade_range}的{'核心' if d <= 3 else '拔高'}考点，"
            f"它通常需要先掌握 {len(recommend_path)} 个前置概念。"
        )
        # 行动建议: 先看前 3 个直接先决
        if recommend_path:
            direct = [r for r in recommend_path if r["distance"] == 1][:3]
            if direct:
                actions.append({
                    "type": "review",
                    "text": f"先回看这 {len(direct)} 个直接基础: " + "、".join(r["title"] for r in direct)
                })
            # 概念卡 / 练习题 入口
            actions.append({
                "type": "concept",
                "text": f"看「{title}」概念卡, 配合下方先决复习"
            })
            actions.append({
                "type": "exercise",
                "text": f"重新做 5 道「{title}」练习题 (客观题自动判分)"
            })
    elif status == "巩固":
        summary = f"「{title}」你掌握了一部分（{score_pct}%），再练练就能稳。"
        why = (
            f"{title}是{subject_cn}{grade_range}的重要概念，"
            f"你已经有基础但细节和综合应用还差点意思。"
        )
        actions.append({
            "type": "exercise",
            "text": f"再做 5 道「{title}」综合题 (T4/T5 应用+压轴)"
        })
        actions.append({
            "type": "review",
            "text": "重点看错题解析, 标记易错点"
        })
    else:  # 已掌握
        summary = f"「{title}」你掌握得不错（{score_pct}%），可以放心往后走。"
        why = (
            f"{title}这层你已经稳了，可以去看它后面解锁的概念，"
            f"或者挑战更高难度的真题。"
        )
        # 找后继
        actions.append({
            "type": "next",
            "text": f"查看「{title}」解锁的后续概念 (会什么 → 学什么)"
        })
        actions.append({
            "type": "challenge",
            "text": f"挑战 5 道「{title}」真题 (is_real_exam=true)"
        })

    return {
        "summary": summary,
        "why": why,
        "actions": actions,
        "status_emoji": {"薄弱": "😟", "巩固": "🙂", "已掌握": "🎉"}.get(status, "🤔"),
    }
