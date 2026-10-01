"""数据模型：培养方案、已修课程、固定归属与审计结果。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional, Set


@dataclass(frozen=True)
class Course:
    """一门已通过的课程。

    - course_id: 唯一标识
    - credits: 1 至 6 的整数学分
    - allowed_categories: 允许归属的类别集合（可为空，表示只能不计入）
    """

    course_id: str
    credits: int
    allowed_categories: FrozenSet[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.credits, int) or not 1 <= self.credits <= 6:
            raise ValueError("credits 必须是 1 至 6 的整数")


@dataclass(frozen=True)
class CategoryRequirement:
    """一个类别的最低学分要求（无上限）。"""

    category: str
    min_credits: int

    def __post_init__(self) -> None:
        if self.min_credits < 0:
            raise ValueError("min_credits 不能为负")


@dataclass
class AuditResult:
    """审计结果。

    - assignment: 一份完整的最优分配，course_id -> 类别或 None（不计入）
    - total_shortfall: 全部类别缺口之和（负数按零计）
    - satisfied_categories: 达标类别数
    - category_credits: 该分配下各类别实际获配学分
    - possible_attributions: 每门课在至少一个最优分配中可取得的全部归属
      （None 表示“不计入任何类别”）
    """

    assignment: Dict[str, Optional[str]]
    total_shortfall: int
    satisfied_categories: int
    category_credits: Dict[str, int]
    possible_attributions: Dict[str, Set[Optional[str]]] = field(
        default_factory=dict
    )
