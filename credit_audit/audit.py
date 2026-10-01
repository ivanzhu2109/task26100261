"""审计核心：求全局最优的学分归属分配。

算法：把各类别剩余需求（按最低要求截断）作为 DP 状态，
对每门未固定课程枚举“计入某允许类别 / 不计入”，
最终在所有可达状态上按 (总缺口最小, 达标类别数最多) 的字典序取最优。
每门课的候选归属通过“额外固定该选项后重算最优值是否不变”判定。
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .models import AuditResult, CategoryRequirement, Course

# 目标值：(-总缺口, 达标类别数)，按元组字典序越大越优
_Objective = Tuple[int, int]
_State = Tuple[int, ...]


def _evaluate(state: _State, needs: Sequence[int]) -> _Objective:
    shortfall = sum(n - s for n, s in zip(needs, state))
    satisfied = sum(1 for n, s in zip(needs, state) if s >= n)
    return (-shortfall, satisfied)


def _transitions(
    state: _State, course_credits: int, cat_indices: Sequence[int],
    needs: Sequence[int],
) -> Iterable[_State]:
    yield state  # 不计入任何类别
    for idx in cat_indices:
        nxt = list(state)
        nxt[idx] = min(needs[idx], nxt[idx] + course_credits)
        yield tuple(nxt)


def _best_objective(
    needs: Sequence[int],
    courses: Sequence[Tuple[int, Sequence[int]]],
) -> _Objective:
    """只求最优目标值（不记录路径）。"""
    states: Set[_State] = {(0,) * len(needs)}
    for credits, cat_indices in courses:
        nxt: Set[_State] = set()
        for state in states:
            nxt.update(_transitions(state, credits, cat_indices, needs))
        states = nxt
    return max(_evaluate(s, needs) for s in states)


def _best_assignment(
    needs: Sequence[int],
    courses: Sequence[Tuple[int, Sequence[int]]],
) -> Tuple[_Objective, List[Optional[int]]]:
    """求最优目标值，并回溯出一份完整分配（每门课 -> 类别索引或 None）。"""
    # states: 状态 -> (前一状态, 该课程的选择)；第 0 层为初始状态
    layers: List[Dict[_State, Optional[Tuple[_State, Optional[int]]]]] = [
        {(0,) * len(needs): None}
    ]
    for credits, cat_indices in courses:
        prev_layer = layers[-1]
        layer: Dict[_State, Optional[Tuple[_State, Optional[int]]]] = {}
        for state in prev_layer:
            for choice, nxt in zip(
                (None, *cat_indices),
                _transitions(state, credits, cat_indices, needs),
            ):
                if nxt not in layer:
                    layer[nxt] = (state, choice)
        layers.append(layer)

    best_state = max(layers[-1], key=lambda s: _evaluate(s, needs))
    best_obj = _evaluate(best_state, needs)

    choices: List[Optional[int]] = [None] * len(courses)
    state = best_state
    for i in range(len(courses) - 1, -1, -1):
        entry = layers[i + 1][state]
        assert entry is not None
        state, choices[i] = entry
    return best_obj, choices


def audit(
    requirements: Iterable[CategoryRequirement],
    courses: Iterable[Course],
    fixed: Optional[Dict[str, str]] = None,
) -> AuditResult:
    """对一个培养方案执行一次学分归属审计。

    参数:
        requirements: 各类别的最低学分要求。
        courses: 已通过的课程列表。
        fixed: 导师固定归属，course_id -> 类别（硬约束）。

    返回:
        AuditResult，包含一份完整最优分配、缺口、达标类别数，
        以及每门课在所有最优分配中可取得的全部归属。
    """
    reqs = list(requirements)
    course_list = list(courses)
    fixed = dict(fixed or {})

    categories = [r.category for r in reqs]
    if len(set(categories)) != len(categories):
        raise ValueError("类别存在重复")
    cat_index = {c: i for i, c in enumerate(categories)}

    ids = [c.course_id for c in course_list]
    if len(set(ids)) != len(ids):
        raise ValueError("课程标识存在重复")
    by_id = {c.course_id: c for c in course_list}

    for cid, cat in fixed.items():
        if cid not in by_id:
            raise ValueError(f"固定归属引用了未知课程: {cid}")
        if cat not in cat_index:
            raise ValueError(f"固定归属引用了未知类别: {cat}")
        if cat not in by_id[cid].allowed_categories:
            raise ValueError(f"课程 {cid} 不允许归入类别 {cat}")

    # 固定归属先计入各类别，剩余需求作为 DP 的截断上限
    fixed_credits = [0] * len(categories)
    for cid, cat in fixed.items():
        fixed_credits[cat_index[cat]] += by_id[cid].credits
    needs = [
        max(0, r.min_credits - fixed_credits[i]) for i, r in enumerate(reqs)
    ]

    free_courses = [c for c in course_list if c.course_id not in fixed]

    def to_indices(course: Course) -> List[int]:
        return sorted(cat_index[c] for c in course.allowed_categories)

    free_data = [(c.credits, to_indices(c)) for c in free_courses]

    best_obj, choices = _best_assignment(needs, free_data)

    # 还原一份完整分配
    assignment: Dict[str, Optional[str]] = {cid: cat for cid, cat in fixed.items()}
    for course, choice in zip(free_courses, choices):
        assignment[course.course_id] = (
            None if choice is None else categories[choice]
        )

    category_credits = {
        cat: fixed_credits[i] for i, cat in enumerate(categories)
    }
    for course, choice in zip(free_courses, choices):
        if choice is not None:
            category_credits[categories[choice]] += course.credits

    total_shortfall = -best_obj[0]
    satisfied = best_obj[1]

    # 每门课在所有最优分配中可取得的全部归属
    possible: Dict[str, Set[Optional[str]]] = {}
    for course in course_list:
        if course.course_id in fixed:
            possible[course.course_id] = {fixed[course.course_id]}
            continue
        options: Set[Optional[str]] = set()
        for option in [None, *sorted(course.allowed_categories)]:
            extra = [0] * len(categories)
            if option is not None:
                extra[cat_index[option]] = course.credits
            trial_needs = [
                max(0, needs[i] - extra[i]) for i in range(len(categories))
            ]
            others = [
                (c.credits, to_indices(c))
                for c in free_courses
                if c.course_id != course.course_id
            ]
            if _best_objective(trial_needs, others) == best_obj:
                options.add(option)
        possible[course.course_id] = options

    return AuditResult(
        assignment=assignment,
        total_shortfall=total_shortfall,
        satisfied_categories=satisfied,
        category_credits=category_credits,
        possible_attributions=possible,
    )
