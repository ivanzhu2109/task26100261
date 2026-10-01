"""学分归属审计的自动化测试。"""
import unittest

from credit_audit import AuditResult, CategoryRequirement as Req, Course, audit


def make_course(cid, credits, cats):
    return Course(cid, credits, frozenset(cats))


class RequiredCasesTest(unittest.TestCase):
    def test_case_two_flexible_courses_same_category(self):
        """A、B 各需 6；X、Y 各 3 均可入 A/B。

        最优：总缺口 6、达标 1；两门课候选均为 {A, B}，
        但返回的分配必须把两门课放在同一类。
        """
        res = audit(
            [Req("A", 6), Req("B", 6)],
            [make_course("X", 3, {"A", "B"}), make_course("Y", 3, {"A", "B"})],
        )
        self.assertEqual(res.total_shortfall, 6)
        self.assertEqual(res.satisfied_categories, 1)
        self.assertEqual(res.possible_attributions["X"], {"A", "B"})
        self.assertEqual(res.possible_attributions["Y"], {"A", "B"})
        # 分配必须一致：两门课同处一类
        self.assertIsNotNone(res.assignment["X"])
        self.assertEqual(res.assignment["X"], res.assignment["Y"])

    def test_case_unique_slot_not_stolen(self):
        """A、B 各需 4；X=4 可入 A/B；Y=3、Z=1、W=1 只能入 A。

        最优：总缺口 0、达标 2；X 候选只有 B，Y 候选只有 A，
        Z、W 候选为 {A, None}。返回的分配必须真正满足两类。
        """
        res = audit(
            [Req("A", 4), Req("B", 4)],
            [
                make_course("X", 4, {"A", "B"}),
                make_course("Y", 3, {"A"}),
                make_course("Z", 1, {"A"}),
                make_course("W", 1, {"A"}),
            ],
        )
        self.assertEqual(res.total_shortfall, 0)
        self.assertEqual(res.satisfied_categories, 2)
        self.assertEqual(res.possible_attributions["X"], {"B"})
        self.assertEqual(res.possible_attributions["Y"], {"A"})
        self.assertEqual(res.possible_attributions["Z"], {"A", None})
        self.assertEqual(res.possible_attributions["W"], {"A", None})
        # 完整分配必须真正满足两类要求
        self.assertGreaterEqual(res.category_credits["A"], 4)
        self.assertGreaterEqual(res.category_credits["B"], 4)
        self.assertEqual(res.assignment["X"], "B")


class FixedAssignmentTest(unittest.TestCase):
    def test_fixed_is_hard_constraint(self):
        """固定归属即使使结果变差也必须遵守。"""
        courses = [
            make_course("X", 4, {"A", "B"}),
            make_course("Y", 4, {"A"}),
        ]
        free_res = audit([Req("A", 4), Req("B", 4)], courses)
        self.assertEqual(free_res.total_shortfall, 0)

        fixed_res = audit(
            [Req("A", 4), Req("B", 4)], courses, fixed={"X": "A"}
        )
        self.assertEqual(fixed_res.assignment["X"], "A")
        self.assertEqual(fixed_res.total_shortfall, 4)
        self.assertEqual(fixed_res.satisfied_categories, 1)
        # 固定课程的候选只有被固定的类别
        self.assertEqual(fixed_res.possible_attributions["X"], {"A"})
        # Y 计入 A 或不计入都不影响最优目标值
        self.assertEqual(fixed_res.possible_attributions["Y"], {"A", None})

    def test_fixed_validation(self):
        courses = [make_course("X", 4, {"A"})]
        with self.assertRaises(ValueError):
            audit([Req("A", 4)], courses, fixed={"X": "B"})  # 不允许的类别
        with self.assertRaises(ValueError):
            audit([Req("A", 4)], courses, fixed={"ZZ": "A"})  # 未知课程
        with self.assertRaises(ValueError):
            audit([Req("A", 4)], courses, fixed={"X": "ZZ"})  # 未知类别


class OptimalityTest(unittest.TestCase):
    def test_shortfall_priority_over_satisfied_count(self):
        """不得为了增加达标类别数而接受更大的总缺口。

        A、B 各需 2、C 需 4；只有一门 4 学分课可入 A/B/C。
        放 C：缺口 4、达标 1；放 A 或 B：缺口 6、达标 1。必须选前者。
        """
        res = audit(
            [Req("A", 2), Req("B", 2), Req("C", 4)],
            [make_course("X", 4, {"A", "B", "C"})],
        )
        self.assertEqual(res.total_shortfall, 4)
        self.assertEqual(res.satisfied_categories, 1)
        self.assertEqual(res.assignment["X"], "C")
        self.assertEqual(res.possible_attributions["X"], {"C"})

    def test_no_double_counting(self):
        """一门课只能计入一个类别，不能重复抵扣。"""
        res = audit(
            [Req("A", 4), Req("B", 4)],
            [make_course("X", 4, {"A", "B"})],
        )
        self.assertEqual(res.total_shortfall, 4)
        self.assertEqual(res.satisfied_categories, 1)

    def test_excess_credits_do_not_offset_other_categories(self):
        """超额学分不能抵扣其他类别的缺口。"""
        res = audit(
            [Req("A", 2), Req("B", 4)],
            [make_course("X", 6, {"A"})],
        )
        self.assertEqual(res.total_shortfall, 4)
        self.assertEqual(res.category_credits["A"], 6)
        self.assertEqual(res.category_credits["B"], 0)

    def test_none_attribution_is_possible_choice(self):
        """不计入任何类别也是一种归属。"""
        res = audit(
            [Req("A", 1)],
            [make_course("X", 1, {"A"}), make_course("Y", 1, {"A"})],
        )
        self.assertEqual(res.total_shortfall, 0)
        self.assertEqual(res.possible_attributions["X"], {"A", None})
        self.assertEqual(res.possible_attributions["Y"], {"A", None})
        # 但同一份分配里只能有一门计入 A 之外的课程不计入
        assigned = [v for v in res.assignment.values() if v == "A"]
        self.assertEqual(len(assigned), 1)

    def test_empty_courses(self):
        res = audit([Req("A", 3)], [])
        self.assertEqual(res.total_shortfall, 3)
        self.assertEqual(res.satisfied_categories, 0)
        self.assertEqual(res.assignment, {})

    def test_zero_requirement_category_is_satisfied(self):
        res = audit([Req("A", 0), Req("B", 2)], [make_course("X", 2, {"B"})])
        self.assertEqual(res.total_shortfall, 0)
        self.assertEqual(res.satisfied_categories, 2)


class ConsistencyTest(unittest.TestCase):
    def test_assignment_respects_allowed_categories(self):
        """返回的分配中每门课只能进入其允许的类别或 None。"""
        courses = [
            make_course("X", 3, {"A", "B"}),
            make_course("Y", 2, {"B"}),
            make_course("Z", 5, {"A", "C"}),
        ]
        res = audit([Req("A", 3), Req("B", 2), Req("C", 5)], courses)
        by_id = {c.course_id: c for c in courses}
        for cid, cat in res.assignment.items():
            if cat is not None:
                self.assertIn(cat, by_id[cid].allowed_categories)

    def test_possible_attributions_subset_of_allowed(self):
        courses = [
            make_course("X", 3, {"A", "B"}),
            make_course("Y", 3, {"A"}),
        ]
        res = audit([Req("A", 3), Req("B", 3)], courses)
        by_id = {c.course_id: c for c in courses}
        for cid, options in res.possible_attributions.items():
            for opt in options:
                if opt is not None:
                    self.assertIn(opt, by_id[cid].allowed_categories)
            self.assertTrue(options, "候选归属集合不能为空")


if __name__ == "__main__":
    unittest.main()
