"""整数多项式实根清单的验收测试。

每个计分测试只检查一个难点；期望根和重数由显式因子构造并在研究记录中复算。
候选进程统一以 runner 身份、干净环境变量和独立进程组运行。
"""

from fractions import Fraction
import json
from math import lcm
import os
import signal
import subprocess
import tempfile
from pathlib import Path

ENTRY = "/app/main.py"
PYTHON = "/usr/local/bin/python3"
CANDIDATE_USER = "runner"
CANDIDATE_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/home/runner",
    "LANG": "C.UTF-8",
    "TZ": "UTC",
}
CALL_TIMEOUT_SEC = 30


def run_candidate(*args, timeout=CALL_TIMEOUT_SEC):
    """以 runner 身份运行候选入口；超时结束整个进程组并抛出 TimeoutError。"""
    as_root = os.getuid() == 0
    proc = subprocess.Popen(
        [PYTHON, ENTRY, *[str(a) for a in args]],
        cwd="/app",
        env=CANDIDATE_ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        user=CANDIDATE_USER if as_root else None,
        group=CANDIDATE_USER if as_root else None,
        extra_groups=[] if as_root else None,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise TimeoutError(f"{ENTRY} 超过 {timeout}s")
    return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)


def multiply(left, right):
    result = [Fraction(0)] * (len(left) + len(right) - 1)
    for i, a_value in enumerate(left):
        for j, b_value in enumerate(right):
            result[i + j] += a_value * b_value
    return result


def integer_polynomial(*factors):
    result = [Fraction(1)]
    for root, multiplicity in factors:
        factor = [-Fraction(root), Fraction(1)]
        for _ in range(multiplicity):
            result = multiply(result, factor)
    denominator = 1
    for coefficient in result:
        denominator = lcm(denominator, coefficient.denominator)
    return [int(coefficient * denominator) for coefficient in result]


def candidate_report(payload):
    folder = Path(tempfile.mkdtemp(prefix="polynomial-"))
    folder.chmod(0o755)
    case = folder / "input.json"
    case.write_text(json.dumps(payload), encoding="utf-8")
    case.chmod(0o644)
    proc = run_candidate(case)
    assert proc.returncode == 0, f"exit={proc.returncode} stderr={proc.stderr[-500:]}"
    return json.loads(proc.stdout)


def canonical_fraction(text):
    value = Fraction(text)
    expected = str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
    assert text == expected
    return value


def assert_profile(report, search_interval, expected):
    assert set(report) == {"roots", "distinct_count", "multiplicity_sum"}
    roots = report["roots"]
    assert isinstance(roots, list)
    assert report["distinct_count"] == len(roots)
    parsed = []
    for item in roots:
        assert set(item) == {"lower", "upper", "multiplicity"}
        lower = canonical_fraction(item["lower"])
        upper = canonical_fraction(item["upper"])
        assert lower <= upper
        assert Fraction(search_interval[0]) <= lower <= upper <= Fraction(search_interval[1])
        assert isinstance(item["multiplicity"], int) and item["multiplicity"] >= 1
        parsed.append((lower, upper, item["multiplicity"]))
    assert parsed == sorted(parsed, key=lambda item: (item[0], item[1]))
    for left, right in zip(parsed, parsed[1:]):
        assert left[1] <= right[0]
    expected_roots = [Fraction(root) for root, _ in expected]
    for lower, upper, _ in parsed:
        assert sum(lower <= root <= upper for root in expected_roots) == 1
    for root, multiplicity in expected:
        root = Fraction(root)
        matches = [item for item in parsed if item[0] <= root <= item[1]]
        assert len(matches) == 1
        assert matches[0][2] == multiplicity
    assert report["multiplicity_sum"] == sum(multiplicity for _, multiplicity in expected)


# ---------- gate：入口与契约，不计分 ----------

def test_output_has_exact_schema():
    """「程序向标准输出写一个 JSON 对象」「`roots` 的每一项只含三个字段」「每个 `[lower, upper]` 都必须落在 `[L, R]` 内，并且恰好包含一个不同的实根；相邻区间可以首尾相接，但不能交叠」"""
    report = candidate_report({"coefficients": [-3, 0, 1], "interval": [-2, 2]})
    assert set(report) == {"roots", "distinct_count", "multiplicity_sum"}
    assert all(set(item) == {"lower", "upper", "multiplicity"} for item in report["roots"])


def test_wrong_argument_count_exits_2():
    """「参数个数不对时退出码为 2，不输出 JSON」「输入文件打不开、JSON 结构不对或数值不合法时，也以退出码 2 结束，不向标准输出写内容」"""
    proc = run_candidate()
    assert proc.returncode == 2
    assert proc.stdout.strip() == ""


# ---------- 难点 1：重数分组 ----------

def test_cubic_root_multiplicity():
    """「同一实根出现多次时只列一次，并给出它的重数」「区间端点用最简有理数表示：分母为正，整数不写 `/1`」"""
    factors = [(Fraction(-7, 3), 3)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [-4, 4]})
    assert_profile(report, [-4, 4], factors)


def test_quartic_root_multiplicity():
    """「同一实根出现多次时只列一次，并给出它的重数」"""
    factors = [(Fraction(7, 5), 4)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [-2, 2]})
    assert_profile(report, [-2, 2], factors)


def test_fifth_root_multiplicity():
    """「同一实根出现多次时只列一次，并给出它的重数」"""
    factors = [(Fraction(-5, 3), 5)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [-4, 3]})
    assert_profile(report, [-4, 3], factors)


# ---------- 难点 2：闭区间端点 ----------

def test_lower_endpoint_root_is_included():
    """「搜索区间是闭区间，落在左端点或右端点的根也要列出」「同一个输入跑两次，输出要一模一样」"""
    factors = [(Fraction(1), 1), (Fraction(3), 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [1, 4]})
    assert_profile(report, [1, 4], factors)


def test_upper_endpoint_root_is_included():
    """「搜索区间是闭区间，落在左端点或右端点的根也要列出」"""
    factors = [(Fraction(-2), 1), (Fraction(1), 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [-3, 1]})
    assert_profile(report, [-3, 1], factors)


def test_both_endpoint_roots_are_included():
    """「搜索区间是闭区间，落在左端点或右端点的根也要列出」"""
    factors = [(Fraction(-1), 1), (Fraction(1), 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [-1, 1]})
    assert_profile(report, [-1, 1], factors)


# ---------- 难点 3：极近根隔离 ----------

def test_symmetric_roots_one_trillionth_apart():
    """「即使两个根非常接近，也必须分别列出」"""
    epsilon = Fraction(1, 10**12)
    factors = [(-epsilon, 1), (epsilon, 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [-1, 1]})
    assert_profile(report, [-1, 1], factors)


def test_clustered_roots_near_one():
    """「即使两个根非常接近，也必须分别列出」"""
    epsilon = Fraction(1, 10**9)
    factors = [(1 - epsilon, 1), (1 + epsilon, 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [0, 2]})
    assert_profile(report, [0, 2], factors)


def test_three_roots_in_narrow_cluster():
    """「即使两个根非常接近，也必须分别列出」"""
    epsilon = Fraction(1, 10**12)
    center = Fraction(1, 3)
    factors = [(center - epsilon, 1), (center, 1), (center + epsilon, 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [0, 1]})
    assert_profile(report, [0, 1], factors)
