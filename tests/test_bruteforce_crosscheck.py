"""与暴力枚举对照的随机化测试：验证全局最优与候选归属集合。"""
import itertools
import random
import unittest

from credit_audit import Category, Course, audit


def brute_force(cats, courses, fixed):
    """枚举全部归属组合，返回 (最优目标, 最优分配集合)。"""
    cat_index = {c.category_id: i for i, c in enumerate(cats)}
    caps = [c.min_credits for c in cats]
    choices = []
    for course in courses:
        if course.course_id in fixed:
            choices.append([fixed[course.course_id]])
        else:
            choices.append(sorted(course.allowed_categories) + [None])

    best_key = None
    best_assigns = []
    for combo in itertools.product(*choices):
        got = [0] * len(cats)
        for course, target in zip(courses, combo):
            if target is not None:
                got[cat_index[target]] += course.credits
        deficit = sum(max(0, cap - g) for cap, g in zip(caps, got))
        satisfied = sum(1 for cap, g in zip(caps, got) if g >= cap)
        key = (deficit, -satisfied)
        if best_key is None or key < best_key:
            best_key = key
            best_assigns = [combo]
        elif key == best_key:
            best_assigns.append(combo)
    return best_key, best_assigns


class TestBruteForceCrossCheck(unittest.TestCase):
    def test_random_instances(self):
        rng = random.Random(20261002)
        for trial in range(300):
            n_cats = rng.randint(1, 3)
            cat_ids = [f"C{i}" for i in range(n_cats)]
            cats = [Category(cid, rng.randint(0, 6)) for cid in cat_ids]
            n_courses = rng.randint(0, 6)
            courses = []
            for i in range(n_courses):
                allowed = frozenset(
                    cid for cid in cat_ids if rng.random() < 0.6
                )
                courses.append(
                    Course(f"K{i}", rng.randint(1, 6), allowed)
                )
            fixed = {}
            for course in courses:
                if course.allowed_categories and rng.random() < 0.25:
                    fixed[course.course_id] = rng.choice(
                        sorted(course.allowed_categories)
                    )

            result = audit(cats, courses, fixed=fixed)
            (best_deficit, neg_sat), best_assigns = brute_force(
                cats, courses, fixed
            )

            # 1) 目标值一致。
            self.assertEqual(result.total_deficit, best_deficit, trial)
            self.assertEqual(result.satisfied_count, -neg_sat, trial)

            # 2) 返回的具体分配本身是最优分配之一。
            course_ids = [c.course_id for c in courses]
            mine = tuple(result.assignment[cid] for cid in course_ids)
            self.assertIn(mine, best_assigns, trial)

            # 3) 候选归属集合与暴力枚举完全一致。
            for idx, course in enumerate(courses):
                expected = {a[idx] for a in best_assigns}
                self.assertEqual(
                    result.attainable[course.course_id], expected,
                    (trial, course.course_id),
                )


if __name__ == "__main__":
    unittest.main()
