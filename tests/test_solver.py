"""credit_audit 求解器测试。"""
import unittest

from credit_audit import AuditResult, Category, Course, audit


def make_case1():
    cats = [Category("A", 6), Category("B", 6)]
    courses = [Course("X", 3, {"A", "B"}), Course("Y", 3, {"A", "B"})]
    return cats, courses


def make_case2():
    cats = [Category("A", 4), Category("B", 4)]
    courses = [
        Course("X", 4, {"A", "B"}),
        Course("Y", 3, {"A"}),
        Course("Z", 1, {"A"}),
        Course("W", 1, {"A"}),
    ]
    return cats, courses


class TestRequiredCases(unittest.TestCase):
    def test_case1_objectives(self):
        cats, courses = make_case1()
        r = audit(cats, courses)
        self.assertEqual(r.total_deficit, 6)
        self.assertEqual(r.satisfied_count, 1)

    def test_case1_assignment_same_category(self):
        cats, courses = make_case1()
        r = audit(cats, courses)
        placed = {r.assignment["X"], r.assignment["Y"]}
        self.assertEqual(len(placed), 1)
        self.assertIn(placed.pop(), {"A", "B"})

    def test_case1_attainable(self):
        cats, courses = make_case1()
        r = audit(cats, courses)
        self.assertEqual(r.attainable["X"], {"A", "B"})
        self.assertEqual(r.attainable["Y"], {"A", "B"})

    def test_case2_objectives(self):
        cats, courses = make_case2()
        r = audit(cats, courses)
        self.assertEqual(r.total_deficit, 0)
        self.assertEqual(r.satisfied_count, 2)

    def test_case2_assignment_satisfies_both(self):
        cats, courses = make_case2()
        r = audit(cats, courses)
        self.assertEqual(r.category_credits["A"], 4 + 1)  # Y(3)+Z/W 之一(1)
        self.assertEqual(r.category_credits["B"], 4)
        self.assertEqual(r.assignment["X"], "B")
        self.assertEqual(r.assignment["Y"], "A")
        self.assertEqual(r.category_deficit, {"A": 0, "B": 0})

    def test_case2_attainable(self):
        cats, courses = make_case2()
        r = audit(cats, courses)
        self.assertEqual(r.attainable["X"], {"B"})
        self.assertEqual(r.attainable["Y"], {"A"})
        self.assertEqual(r.attainable["Z"], {"A", None})
        self.assertEqual(r.attainable["W"], {"A", None})


class TestFixedAssignments(unittest.TestCase):
    def test_fixed_forces_suboptimal(self):
        # 固定 X->A 后，Y 只能去 B，仍可达标 1 类、缺口 6。
        cats, courses = make_case1()
        r = audit(cats, courses, fixed={"X": "A"})
        self.assertEqual(r.assignment["X"], "A")
        self.assertEqual(r.total_deficit, 6)
        self.assertEqual(r.satisfied_count, 1)
        self.assertEqual(r.attainable["X"], {"A"})

    def test_fixed_makes_result_worse(self):
        # X 固定到 B 时，B 仍缺 1，A 缺 3：总缺口 4。
        cats = [Category("A", 3), Category("B", 4)]
        courses = [Course("X", 3, {"A", "B"})]
        r = audit(cats, courses, fixed={"X": "B"})
        self.assertEqual(r.total_deficit, 4)
        self.assertEqual(r.satisfied_count, 0)
        self.assertEqual(r.assignment, {"X": "B"})

    def test_fixed_unknown_course(self):
        cats, courses = make_case1()
        with self.assertRaises(ValueError):
            audit(cats, courses, fixed={"Q": "A"})

    def test_fixed_unknown_category(self):
        cats, courses = make_case1()
        with self.assertRaises(ValueError):
            audit(cats, courses, fixed={"X": "C"})

    def test_fixed_disallowed_category(self):
        cats = [Category("A", 3)]
        courses = [Course("X", 3, {"A"})]
        with self.assertRaises(ValueError):
            audit(cats, [Course("X", 3, {"A"}), Course("Y", 2, {"A"})],
                  fixed={"Y": "B"})


class TestOptimalitySemantics(unittest.TestCase):
    def test_deficit_priority_over_satisfied_count(self):
        # X->A：总缺口 4、达标 0 类；X->B：总缺口 6、达标 1 类。
        # 必须选总缺口更小的方案，不得为达标数接受更大缺口。
        cats = [Category("A", 6), Category("B", 1)]
        courses = [Course("X", 3, {"A", "B"})]
        r = audit(cats, courses)
        self.assertEqual(r.total_deficit, 4)
        self.assertEqual(r.satisfied_count, 0)
        self.assertEqual(r.assignment["X"], "A")
        self.assertEqual(r.attainable["X"], {"A"})

    def test_tie_break_prefers_more_satisfied(self):
        # 两种放法总缺口相同，应选达标类别数更多的。
        cats = [Category("A", 2), Category("B", 2)]
        courses = [Course("X", 2, {"A", "B"}), Course("Y", 1, {"A"})]
        r = audit(cats, courses)
        # X->B, Y->A：缺口 1，达标 2 类？A 获 1 缺 1，B 获 2 达标 -> 达标 1。
        # X->A, Y->A：A 获 3 达标，B 缺 2 -> 缺口 2。最优是缺口 1、达标 1。
        self.assertEqual(r.total_deficit, 1)
        self.assertEqual(r.satisfied_count, 1)
        self.assertEqual(r.assignment["X"], "B")

    def test_no_double_counting(self):
        # 一门课不能同时抵扣两个类别。
        cats = [Category("A", 3), Category("B", 3)]
        courses = [Course("X", 3, {"A", "B"})]
        r = audit(cats, courses)
        self.assertEqual(r.total_deficit, 3)
        self.assertEqual(r.satisfied_count, 1)

    def test_excess_credits_do_not_transfer(self):
        cats = [Category("A", 2), Category("B", 5)]
        courses = [Course("X", 6, {"A"})]
        r = audit(cats, courses)
        self.assertEqual(r.total_deficit, 5)
        self.assertEqual(r.category_deficit, {"A": 0, "B": 5})

    def test_unassigned_is_an_attainable_option(self):
        cats = [Category("A", 2)]
        courses = [Course("X", 2, {"A"}), Course("Y", 3, {"A"})]
        r = audit(cats, courses)
        # 只需一门课即可达标，另一门计入与否都是最优。
        self.assertEqual(r.attainable["X"], {"A", None})
        self.assertEqual(r.attainable["Y"], {"A", None})
        self.assertEqual(r.total_deficit, 0)

    def test_empty_courses(self):
        r = audit([Category("A", 3)], [])
        self.assertEqual(r.total_deficit, 3)
        self.assertEqual(r.satisfied_count, 0)
        self.assertEqual(r.assignment, {})

    def test_zero_requirement_category_is_satisfied(self):
        r = audit([Category("A", 0)], [])
        self.assertEqual(r.total_deficit, 0)
        self.assertEqual(r.satisfied_count, 1)


class TestValidation(unittest.TestCase):
    def test_duplicate_course_ids(self):
        with self.assertRaises(ValueError):
            audit([Category("A", 1)],
                  [Course("X", 1, {"A"}), Course("X", 1, {"A"})])

    def test_duplicate_category_ids(self):
        with self.assertRaises(ValueError):
            audit([Category("A", 1), Category("A", 2)], [])

    def test_course_credits_range(self):
        with self.assertRaises(ValueError):
            Course("X", 0, {"A"})
        with self.assertRaises(ValueError):
            Course("X", 7, {"A"})


if __name__ == "__main__":
    unittest.main()
