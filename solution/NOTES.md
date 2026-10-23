# 参考解说明

## 三个难点

| 编号 | 错误认知 | 正确知识 | 对应测试（tests/scoring.json） |
|---|---|---|---|
| difficulty_1 | 只要给出一个包含根的有理区间就够了；分母较大的有理根不需要精确识别 | 先用精确有理根搜索找出所有有理根并输出点区间，端点根也要单独保留 | `test_rational_root_*_is_point`、`test_lower_endpoint_root_is_included`、`test_upper_endpoint_root_is_included`、`test_both_endpoint_roots_are_included` |
| difficulty_2 | 一次 `gcd(p,p')` 只能给出一个统一的“重根”标记 | 逐层无平方分解才能得到每个根的真实重数，尤其是 3、4、5 次重根 | `test_cubic_root_multiplicity`、`test_quartic_root_multiplicity`、`test_fifth_root_multiplicity` |
| difficulty_3 | 固定 epsilon 的符号二分和任意宽度区间足以表达无理根 | 用精确 Sturm 计数隔离根，再用 64 阶 Farey 相邻分数表达；单元含其他根时提高 Farey 阶数 | `test_two_nearby_irrational_roots_use_farey`、`test_clustered_irrational_roots_use_farey`、`test_sqrt_two_uses_farey_bracket`、`test_sqrt_three_uses_farey_bracket`、`test_three_irrational_roots_in_narrow_cluster`、`test_farey_refines_past_point_root` |

## 参考解文件

- `solution/app/main.py`：完整实现，使用 `Fraction`、无平方分解、Sturm 序列和 Farey 证书。
- `solution/solve.sh`：安装参考实现；`HTB_SKIP` 用精确片段把对应难点退回初始写法。

## 关键步骤

1. 把升序整数系数转成有理系数多项式并去掉末尾零。
2. 用逐层 gcd 得到按重数分组的无平方因子。
3. 将各因子相乘，得到只保留不同根的多项式。
4. 对所有无平方因子做有理根搜索；分母不受固定阈值限制，命中的有理根输出点区间并从根多项式里除去。
5. 对剩余根构造 Sturm 链；用两端符号变号数差判断子区间根数。
6. 根数大于 1 时取有理中点继续分割；中点恰为根时记录点区间并降次。
7. 对每个无理根，找 64 阶 Farey 序列中包含它的相邻分数。
8. 如果该 Farey 单元还包含其他根，就把阶数加倍后重新计算，直到每个单元只含一个根。
9. 对每个输出区间反查唯一对应的无平方因子得到重数，并按根值排序。

## 核心公式与独立复算

- 解析推导：`research/derivations.md` 第 1-3 节。
- 独立复核：`~/.local/share/codex-harbor/0.24.0/bin/python -I research/verify_claims.py`。
- 结果文件：`research/verification-output.json`；核心显式因子案例 `failures=[]`。
- 区间输出不设数值容差；有理数用 `Fraction` 精确比较，无理根用 Farey 序列的整数分母比较。

## 容差依据

- 题目没有数值容差；所有根、重数、Farey 端点和边界判断都用整数或有理数精确计算。
- 有理根必须输出 `lower == upper` 的点区间；无理根输出相邻 Farey 分数。
- 极近根、分母 1000003 的有理根和双端点根分别覆盖三种常见漏解路径。

## 权重依据

- gate 测试不计分：输出 schema、参数错误退出码。
- difficulty_1 合计 0.40：精确有理根和端点根，七个计分测试合计 0.40。
- difficulty_2 合计 0.30：三次、四次、五次重根，三项各 0.10。
- difficulty_3 合计 0.30：Farey 分数、窄根簇和自适应阶数，六个计分测试各 0.05。
- 三个难点都修好才得到 1.0，`scoring.json` 的权重和为 1。

## 数据来源

- 无真实业务数据；测试多项式由显式因子构造，核心案例、整数系数和 SymPy 复核见 `research/verification-output.json`。
- 独立复核脚本：`research/verify_claims.py`；来源记录：`research/sources.md`。
- 研究材料不在镜像内，`environment/` 不含测试、参考解或答案提示。

## 答案隔离

- [x] 镜像内没有 `tests/`、`solution/`、`.git/`、缓存和备份。
- [x] 注释、文件名、变量名、输入样例没有直接给出修复片段。
- [x] Dockerfile 没有先复制正确版本再改坏。
- [x] 参考实现位于 `solution/`，不进入 Agent 可见的 `/app`。
