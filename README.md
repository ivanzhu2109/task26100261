# 学位审计 · 学分归属模块

纯内存的 Python 库，由上层直接调用。一次 `audit()` 处理一个培养方案。

## 功能

- 每门课整体计入一个允许类别（或不计入），不拆分学分、不重复抵扣。
- 类别只有最低学分要求；缺口 = max(0, 要求 - 获配)，超额不抵扣其他类别。
- 导师固定归属是硬约束，即使使结果变差也遵守；未固定课程重新分配。
- 全局最优：先使全部类别缺口之和最小，再在此前提下使达标类别数最多。
- 返回一份完整的最优分配，并为每门课给出它在**至少一个最优分配**中
  可取得的全部归属（含 `None`，即“不计入任何类别”）。这区分了
  “课程允许放进某类”与“放进去后仍能保持最优审计结果”。

## 安装与运行

无第三方依赖，Python 3.9+。把仓库根目录加入 `PYTHONPATH` 即可：

```bash
python3 -m unittest discover -s tests -v   # 运行自动化测试
```

## 调用示例

```python
from credit_audit import audit, Course, CategoryRequirement

result = audit(
    requirements=[
        CategoryRequirement("专业课", 6),
        CategoryRequirement("通识课", 6),
    ],
    courses=[
        Course("X", 3, frozenset({"专业课", "通识课"})),
        Course("Y", 3, frozenset({"专业课", "通识课"})),
    ],
    fixed={"X": "专业课"},  # 可选：导师固定归属（硬约束）
)

result.assignment             # 一份完整最优分配: {"X": "专业课", "Y": "专业课"}
result.total_shortfall        # 全部类别缺口之和: 6
result.satisfied_categories   # 达标类别数: 1
result.category_credits       # 各类别实际获配学分
result.possible_attributions  # 每门课在所有最优分配中可取得的全部归属
                              # {"X": {"专业课"}, "Y": {"专业课", "通识课"}}
```

## 接口说明

- `Course(course_id, credits, allowed_categories)`
  - `credits` 为 1–6 的整数；`allowed_categories` 为允许归属的类别集合。
- `CategoryRequirement(category, min_credits)`：某类别的最低学分要求。
- `audit(requirements, courses, fixed=None) -> AuditResult`
  - `fixed`：`{course_id: category}`，必须引用已存在的课程、类别，
    且类别在该课程的允许集合内，否则抛 `ValueError`。
  - 课程标识、类别名重复时同样抛 `ValueError`。

## 实现要点

以各类别剩余需求（按最低要求截断）为状态做动态规划，枚举每门未固定
课程的“计入某允许类别 / 不计入”，在全部可达状态上按
`(总缺口最小, 达标类别数最多)` 的字典序取最优并回溯出一份分配。
每门课的候选归属通过“额外固定该选项后重算最优值是否不变”判定，
因此候选集合精确刻画了所有最优分配中该课能取得的归属。
