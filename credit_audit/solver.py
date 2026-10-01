"""学分归属求解器。

算法：按课程做动态规划，状态为各类别“已获配学分（按各自最低要求截断）”
的向量。截断不影响目标值，因为缺口与达标数只取决于 min(获配, 要求)。

- 前向 DP 求出每个前缀可达的状态集合；
- 在最终状态上按 (总缺口最小, 达标类别数最多) 的字典序选出最优终态集合；
- 反向 DP 求出每个位置能到达最优终态的状态集合；
- 正反向集合相交即得：一份具体最优分配（回溯），以及每门课在至少一个
  最优分配中可取得的全部归属（含 None 表示不计入任何类别）。
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .models import AuditResult, Category, Course

State = Tuple[int, ...]


def _choices_for(course: Course, fixed: Dict[str, str]) -> Tuple[Optional[str], ...]:
    """返回课程允许的决策：固定课程只有固定类别，否则为允许类别加不计入。"""
    if course.course_id in fixed:
        return (fixed[course.course_id],)
    return tuple(sorted(course.allowed_categories)) + (None,)


def _transition(
    state: State, choice: Optional[str], credits: int, caps: Sequence[int],
    cat_index: Dict[str, int],
) -> State:
    if choice is None:
        return state
    idx = cat_index[choice]
    new_val = min(state[idx] + credits, caps[idx])
    if new_val == state[idx]:
        return state
    return state[:idx] + (new_val,) + state[idx + 1:]


def _objective(state: State, caps: Sequence[int]) -> Tuple[int, int]:
    """返回 (总缺口, 达标类别数)。"""
    deficit = sum(cap - val for cap, val in zip(caps, state))
    satisfied = sum(1 for cap, val in zip(caps, state) if val >= cap)
    return deficit, satisfied


def audit(
    categories: Iterable[Category],
    courses: Iterable[Course],
    fixed: Optional[Dict[str, str]] = None,
) -> AuditResult:
    """对一组课程在给定培养方案下做全局最优归属审计。

    最优标准：先使全部类别缺口之和最小，再在此前提下使达标类别数最多。
    fixed 为导师固定归属（course_id -> category_id），属于硬约束。
    """
    cats = list(categories)
    course_list = list(courses)
    fixed = dict(fixed or {})

    cat_ids = [c.category_id for c in cats]
    if len(set(cat_ids)) != len(cat_ids):
        raise ValueError("类别标识必须唯一")
    course_ids = [c.course_id for c in course_list]
    if len(set(course_ids)) != len(course_ids):
        raise ValueError("课程标识必须唯一")

    cat_index = {cid: i for i, cid in enumerate(cat_ids)}
    by_id = {c.course_id: c for c in course_list}
    for cid, target in fixed.items():
        if cid not in by_id:
            raise ValueError(f"固定归属引用了未知课程: {cid}")
        if target not in cat_index:
            raise ValueError(f"固定归属引用了未知类别: {target}")
        if target not in by_id[cid].allowed_categories:
            raise ValueError(f"课程 {cid} 不允许归入类别 {target}")

    caps: Tuple[int, ...] = tuple(c.min_credits for c in cats)
    choices: List[Tuple[Optional[str], ...]] = [
        _choices_for(c, fixed) for c in course_list
    ]
    n = len(course_list)

    # 前向可达状态集合。
    forward: List[Set[State]] = [{(0,) * len(caps)}]
    for i, course in enumerate(course_list):
        nxt: Set[State] = set()
        for state in forward[i]:
            for choice in choices[i]:
                nxt.add(
                    _transition(state, choice, course.credits, caps, cat_index)
                )
        forward.append(nxt)

    # 最优终态集合：先总缺口最小，再达标类别数最多。
    best: Optional[Tuple[int, int]] = None
    optimal_final: Set[State] = set()
    for state in forward[n]:
        obj = _objective(state, caps)
        key = (obj[0], -obj[1])
        if best is None or key < best:
            best = key
            optimal_final = {state}
        elif key == best:
            optimal_final.add(state)

    # 反向：每个位置能到达最优终态的状态集合。
    backward: List[Set[State]] = [set() for _ in range(n + 1)]
    backward[n] = optimal_final
    for i in range(n - 1, -1, -1):
        course = course_list[i]
        for state in forward[i]:
            for choice in choices[i]:
                if _transition(
                    state, choice, course.credits, caps, cat_index
                ) in backward[i + 1]:
                    backward[i].add(state)
                    break

    # 回溯出一份具体的最优分配。
    assignment: Dict[str, Optional[str]] = {}
    state = (0,) * len(caps)
    for i, course in enumerate(course_list):
        for choice in choices[i]:
            nxt = _transition(state, choice, course.credits, caps, cat_index)
            if nxt in backward[i + 1]:
                assignment[course.course_id] = choice
                state = nxt
                break

    # 每门课在至少一个最优分配中可取得的全部归属。
    attainable: Dict[str, Set[Optional[str]]] = {}
    for i, course in enumerate(course_list):
        can: Set[Optional[str]] = set()
        for s in forward[i]:
            if s not in backward[i]:
                continue
            for choice in choices[i]:
                if _transition(
                    s, choice, course.credits, caps, cat_index
                ) in backward[i + 1]:
                    can.add(choice)
        attainable[course.course_id] = can

    total_deficit, satisfied_count = _objective(state, caps)
    category_credits = {cid: 0 for cid in cat_ids}
    for course in course_list:
        target = assignment[course.course_id]
        if target is not None:
            category_credits[target] += course.credits
    category_deficit = {
        cid: max(0, caps[cat_index[cid]] - category_credits[cid])
        for cid in cat_ids
    }

    return AuditResult(
        total_deficit=total_deficit,
        satisfied_count=satisfied_count,
        assignment=assignment,
        attainable=attainable,
        category_credits=category_credits,
        category_deficit=category_deficit,
    )
