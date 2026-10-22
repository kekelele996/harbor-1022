# 参考解说明

## 三个难点

| 编号 | 错误认知 | 正确知识 | 对应测试（tests/scoring.json） |
|---|---|---|---|
| difficulty_1 | 一次 `gcd(p,p')` 只能给出一个统一的“重根”标记 | 逐层剥离无平方因子，才能把 3、4、5 等重数分别归组 | `test_cubic_root_multiplicity`、`test_quartic_root_multiplicity`、`test_fifth_root_multiplicity` |
| difficulty_2 | 只在区间内部找变号，端点根可以先忽略 | 闭区间端点要单独判根、写点区间，并从内部计数多项式中除去对应因子 | `test_lower_endpoint_root_is_included`、`test_upper_endpoint_root_is_included`、`test_both_endpoint_roots_are_included` |
| difficulty_3 | 固定 epsilon 的符号二分足以分开所有根 | 用精确 Sturm 变号差统计子区间根数，计数大于 1 就继续分割 | `test_symmetric_roots_one_trillionth_apart`、`test_clustered_roots_near_one`、`test_three_roots_in_narrow_cluster` |

## 参考解文件

- `solution/app/main.py`：完整实现，使用 `Fraction`、无平方分解和 Sturm 序列。
- `solution/solve.sh`：安装参考实现，并用 `HTB_SKIP` 的精确片段把对应难点退回初始写法。

## 关键步骤

1. 把升序整数系数转成有理系数多项式并去掉末尾零。
2. 用逐层 gcd 得到按重数分组的无平方因子。
3. 将各因子相乘，得到只保留不同根的多项式。
4. 先检查搜索区间两个端点，端点根写成点区间并从内部计数多项式中除去。
5. 为剩余多项式构造 Sturm 链；用两端的符号变号数差判断子区间根数。
6. 根数大于 1 时取有理中点继续分割；中点恰为根时记录点区间并降次。
7. 对每个隔离区间反查唯一对应的无平方因子，得到重数。
8. 按根值排序，输出最简有理数端点和计数。

## 核心公式与独立复算

- 解析推导：`research/derivations.md` 第 1-3 节。
- 独立复核：`~/.local/share/codex-harbor/0.24.0/bin/python -I research/verify_claims.py`。
- 结果文件：`research/verification-output.json`，9 组 `failures=[]`。
- 两条路径差异为 0；所有测试根都是显式有理根或显式因子乘积给出的根。

## 容差依据

- 本题不设数值容差，所有判定使用整数和 `Fraction` 精确计算。
- 输出区间端点必须是约分后的有理数字符串；测试用 `Fraction` 精确解析后再判断显式根是否落在区间内。
- 最窄根距为 `10^-12`，远小于固定 `10^-9` epsilon 扫描的可分辨范围，因此能稳定区分正确实现与固定 epsilon 二分。

## 权重依据

- gate 测试不计分：输出 schema、参数错误退出码。
- difficulty_1 合计 0.40：重数决定清单的业务含义，三项分别为 0.14、0.13、0.13。
- difficulty_2 合计 0.30：闭区间端点是输入契约的一部分，三项各 0.10。
- difficulty_3 合计 0.30：极近根隔离是主要算法难点，三项各 0.10。
- 只修一个难点时约得 0.30-0.40；三个都修才得到 1.0，`scoring.json` 权重和为 1。

## 数据来源

- 无真实业务数据；9 组基准全部由显式因子构造，因子和整数系数见 `research/verification-output.json`。
- 独立复算脚本：`research/verify_claims.py`；来源记录：`research/sources.md`。
- 研究材料不在镜像内，`environment/` 不含测试、参考解或答案提示。

## 答案隔离

- [x] 镜像内没有 `tests/`、`solution/`、`.git/`、缓存和备份。
- [x] 注释、文件名、变量名、输入样例没有直接给出修复片段。
- [x] Dockerfile 没有先复制正确版本再改坏。
- [x] 参考实现位于 `solution/`，不进入 Agent 可见的 `/app`。
