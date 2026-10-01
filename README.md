# task26100261

# credit_audit：学位审计学分归属库

纯 Python 内存库，无第三方依赖、无外部服务。一次 `audit()` 调用处理一个
培养方案，返回全局最优的学分归属结果。

## 模型

- `Category(category_id, min_credits)`：类别，只有最低学分要求，无上限。
- `Course(course_id, credits, allowed_categories)`：已修通过的课程，
  `credits` 为 1–6 的整数，`allowed_categories` 为允许归属的类别集合。
- 每门课只能整体计入一个允许类别，或不计入任何类别（归属值为 `None`），
  不拆分学分、不重复抵扣；超额学分不能转移到其他类别。

## 调用方式

```python
from credit_audit import audit, Category, Course

result = audit(
    categories=[Category("A", 4), Category("B", 4)],
    courses=[
        Course("X", 4, {"A", "B"}),
        Course("Y", 3, {"A"}),
        Course("Z", 1, {"A"}),
        Course("W", 1, {"A"}),
    ],
    fixed={"X": "B"},  # 导师固定归属，硬约束；可省略
)

result.total_deficit      # 全部类别缺口之和（最优）
result.satisfied_count    # 达标类别数（总缺口最小时最多）
result.assignment         # 一份完整最优分配：course_id -> 类别或 None
result.attainable         # 每门课在至少一个最优分配中可取得的全部归属（含 None）
result.category_credits   # 该分配下各类别实际获配学分
result.category_deficit   # 各类别缺口（负数按零计）
```

## 最优性定义

先使全部类别缺口之和最小，再在此前提下使达标类别数最多；不会为增加
达标类别数而接受更大的总缺口。固定归属是硬约束，即使使结果变差也遵守；
未固定课程由求解器重新分配。

`assignment` 与 `attainable` 的区分：`assignment` 是一份自洽的完整最优
分配（可直接采用）；`attainable` 回答“课程允许放进某类，且放进去后仍能
保持最优审计结果”，供导师手工调整时参考，避免挤占其他课程唯一可用位置。
两者都基于同一组（同时满足两项目标且遵守固定归属的）最优分配计算。

## 算法

按课程做动态规划，状态为各类别“已获配学分（按各自最低要求截断）”的向量。
前向 DP 求可达状态，按 `(总缺口, -达标数)` 字典序选出最优终态，再反向 DP
标出能到达最优终态的状态；正反向集合相交即得一份具体分配与每门课的全部
可取得归属。状态数上界为各类别 `(要求+1)` 的乘积，适合培养方案规模的审计。

## 测试

```bash
python3 -m unittest discover -s tests -v
```

包含题目要求的两个案例、固定归属、最优性语义（缺口优先、不重复抵扣、
超额不转移等）、输入校验，以及与暴力枚举对照的 300 组随机化测试。
