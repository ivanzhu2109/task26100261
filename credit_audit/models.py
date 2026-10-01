"""数据模型：培养方案、课程、类别与审计结果。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional, Set, Tuple

#: 表示“不计入任何类别”的归属取值。
UNASSIGNED: Optional[str] = None


@dataclass(frozen=True)
class Category:
    """培养方案中的一个课程类别。

    category_id: 类别唯一标识。
    min_credits: 该类别最低学分要求（无上限）。
    """

    category_id: str
    min_credits: int

    def __post_init__(self) -> None:
        if not self.category_id:
            raise ValueError("category_id 不能为空")
        if self.min_credits < 0:
            raise ValueError("min_credits 不能为负")


@dataclass(frozen=True)
class Course:
    """一门已修并通过的课程。

    course_id: 课程唯一标识。
    credits: 整数学分，取值 1 至 6。
    allowed_categories: 允许归属的类别标识集合。
    """

    course_id: str
    credits: int
    allowed_categories: FrozenSet[str]

    def __post_init__(self) -> None:
        if not self.course_id:
            raise ValueError("course_id 不能为空")
        if not 1 <= self.credits <= 6:
            raise ValueError("credits 必须是 1 至 6 的整数")
        object.__setattr__(
            self, "allowed_categories", frozenset(self.allowed_categories)
        )


@dataclass(frozen=True)
class Program:
    """培养方案：一次审计处理一个。"""

    categories: Tuple[Category, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "categories", tuple(self.categories))
        ids = [c.category_id for c in self.categories]
        if len(set(ids)) != len(ids):
            raise ValueError("类别标识必须唯一")


@dataclass
class AuditResult:
    """审计结果。

    total_deficit: 全部类别缺口之和（最优值）。
    satisfied_count: 达标类别数（在总缺口最小的前提下最多）。
    assignment: 一份完整的最优分配，course_id -> 类别标识或 None（不计入）。
    attainable: 每门课在至少一个最优分配中能够取得的全部归属
        （含 None，表示存在某个最优分配中该课不计入任何类别）。
    category_credits: 该份最优分配下各类别实际获配学分。
    category_deficit: 各类别缺口（最低要求减去获配学分，负数按零计）。
    """

    total_deficit: int = 0
    satisfied_count: int = 0
    assignment: Dict[str, Optional[str]] = field(default_factory=dict)
    attainable: Dict[str, Set[Optional[str]]] = field(default_factory=dict)
    category_credits: Dict[str, int] = field(default_factory=dict)
    category_deficit: Dict[str, int] = field(default_factory=dict)
