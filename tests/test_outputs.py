"""整数多项式实根清单的验收测试。

每个计分测试只检查一个难点；期望根和重数由显式因子构造并在研究记录中复算。
候选进程统一以 runner 身份、干净环境变量和独立进程组运行。
"""

from decimal import Decimal, getcontext
from fractions import Fraction
import json
from math import ceil, gcd, isqrt, lcm
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


def assert_profile(report, search_interval, expected, require_exact_rational=False):
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
        if require_exact_rational:
            assert matches[0][0] == root and matches[0][1] == root
    assert report["multiplicity_sum"] == sum(multiplicity for _, multiplicity in expected)


FAREY_ORDER = 64
getcontext().prec = 80


def integer_from_factors(*factors):
    result = [Fraction(1)]
    for factor in factors:
        result = multiply(result, factor)
    denominator = 1
    for coefficient in result:
        denominator = lcm(denominator, coefficient.denominator)
    return [int(coefficient * denominator) for coefficient in result]


def farey_fractions(lower=Fraction(1), upper=Fraction(2), order=FAREY_ORDER):
    values = set()
    for denominator in range(1, order + 1):
        start = ceil(lower * denominator)
        end = (upper * denominator).numerator // (upper * denominator).denominator
        for numerator in range(start, end + 1):
            if numerator and gcd(abs(numerator), denominator) != 1:
                continue
            values.add(Fraction(numerator, denominator))
    values.add(lower)
    values.add(upper)
    return sorted(values)


def farey_bracket_for_value(value, lower=Fraction(1), upper=Fraction(2), order=FAREY_ORDER):
    decimals = [(fraction, Decimal(fraction.numerator) / Decimal(fraction.denominator))
                for fraction in farey_fractions(lower, upper, order)]
    below = max((item for item in decimals if item[1] <= value), key=lambda item: item[1])
    above = min((item for item in decimals if item[1] >= value), key=lambda item: item[1])
    return below[0], above[0]


def assert_farey_cell(report, value, multiplicity=1):
    roots = report["roots"]
    assert len(roots) == 1
    item = roots[0]
    expected_lower, expected_upper = farey_bracket_for_value(value)
    assert canonical_fraction(item["lower"]) == expected_lower
    assert canonical_fraction(item["upper"]) == expected_upper
    assert item["multiplicity"] == multiplicity


def assert_farey_profile(report, values):
    roots = report["roots"]
    assert len(roots) == len(values)
    expected = sorted((value, *farey_bracket_for_value(value)) for value in values)
    parsed = sorted(
        (canonical_fraction(item["lower"]), canonical_fraction(item["upper"]), item["multiplicity"])
        for item in roots
    )
    for (value, lower, upper), (actual_lower, actual_upper, multiplicity) in zip(expected, parsed):
        assert actual_lower == lower and actual_upper == upper
        assert multiplicity == 1
        assert Decimal(lower.numerator) / Decimal(lower.denominator) <= value <= Decimal(upper.numerator) / Decimal(upper.denominator)


def adaptive_farey_bracket(value, point_roots, lower=Fraction(1), upper=Fraction(2)):
    order = FAREY_ORDER
    while True:
        low, high = farey_bracket_for_value(value, lower, upper, order)
        if not any(low <= point <= high for point in point_roots):
            return low, high, order
        order *= 2


def assert_adaptive_farey_profile(report, values, point_roots, lower=Fraction(1), upper=Fraction(2), point_multiplicity=1):
    expected = []
    for value in sorted(values):
        if any(value == Decimal(point.numerator) / Decimal(point.denominator) for point in point_roots):
            expected.append((value, value, point_multiplicity, None))
        else:
            low, high, order = adaptive_farey_bracket(value, point_roots, lower, upper)
            expected.append((value, low, high, 1, order))
    roots = report["roots"]
    assert len(roots) == len(expected)
    for item, expected_item in zip(roots, expected):
        value = expected_item[0]
        if len(expected_item) == 4:
            assert canonical_fraction(item["lower"]) == value
            assert canonical_fraction(item["upper"]) == value
            assert item["multiplicity"] == point_multiplicity
        else:
            assert canonical_fraction(item["lower"]) == expected_item[1]
            assert canonical_fraction(item["upper"]) == expected_item[2]
            assert item["multiplicity"] == 1


# ---------- gate：入口与契约，不计分 ----------

def test_output_has_exact_schema():
    """「程序往标准输出写一个 JSON 对象」「`roots` 的每一项也只有三个字段」「每个 `[lower, upper]` 都必须落在 `[L, R]` 内，并且恰好包含一个不同的实根；相邻区间可以首尾相接，但不能交叠」"""
    report = candidate_report({"coefficients": [-3, 0, 1], "interval": [-2, 2]})
    assert set(report) == {"roots", "distinct_count", "multiplicity_sum"}
    assert all(set(item) == {"lower", "upper", "multiplicity"} for item in report["roots"])


def test_wrong_argument_count_exits_2():
    """「参数个数不对时退出码为 2，不输出 JSON」「输入文件打不开、JSON 结构不对或数值不合法时，也以退出码 2 结束，不向标准输出写内容」"""
    proc = run_candidate()
    assert proc.returncode == 2
    assert proc.stdout.strip() == ""


# ---------- 难点 1：重数分组 ----------

def test_rational_root_one_ninety_seventh_is_point():
    """「只要根是有理数，就必须输出精确点区间，即 `lower == upper`」"""
    factors = [(Fraction(1, 97), 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [0, 1]})
    assert_profile(report, [0, 1], factors, require_exact_rational=True)


def test_rational_root_five_one_hundred_first_is_point():
    """「只要根是有理数，就必须输出精确点区间，即 `lower == upper`」"""
    factors = [(Fraction(5, 101), 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [0, 1]})
    assert_profile(report, [0, 2], factors, require_exact_rational=True)


def test_rational_root_negative_thirteen_one_hundred_third_is_point():
    """「只要根是有理数，就必须输出精确点区间，即 `lower == upper`」"""
    factors = [(Fraction(-13, 103), 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [-1, 0]})
    assert_profile(report, [-2, 0], factors, require_exact_rational=True)


# ---------- 难点 2：闭区间端点 ----------

def test_rational_root_above_old_denominator_limit_is_point():
    """「只要根是有理数，就必须输出精确点区间，即 `lower == upper`」"""
    factors = [(Fraction(1000001, 1000003), 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [0, 2]})
    assert_profile(report, [0, 2], factors, require_exact_rational=True)


def test_lower_endpoint_root_is_included():
    """「搜索区间是闭区间，落在左端点或右端点的根也要列出」「同一个输入跑两次，输出要一模一样」"""
    factors = [(Fraction(1), 1), (Fraction(3), 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [1, 4]})
    assert_profile(report, [1, 4], factors, require_exact_rational=True)


def test_upper_endpoint_root_is_included():
    """「搜索区间是闭区间，落在左端点或右端点的根也要列出」"""
    factors = [(Fraction(-2), 1), (Fraction(1), 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [-3, 1]})
    assert_profile(report, [-3, 1], factors, require_exact_rational=True)


def test_both_endpoint_roots_are_included():
    """「搜索区间是闭区间，落在左端点或右端点的根也要列出」"""
    factors = [(Fraction(-1), 1), (Fraction(1), 1)]
    report = candidate_report({"coefficients": integer_polynomial(*factors), "interval": [-1, 1]})
    assert_profile(report, [-1, 1], factors, require_exact_rational=True)


# ---------- 难点 3：极近根隔离 ----------

def test_cubic_root_multiplicity():
    """「同一实根出现多次时只列一次，并给出它的重数」"""
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


def test_two_nearby_irrational_roots_use_farey():
    """「无理根使用 64 阶 Farey 序列：`lower` 和 `upper` 必须是该序列中包含根的一对相邻分数」"""
    root_shift = Fraction(1, 100)
    coefficient = [root_shift * root_shift - 2, -2 * root_shift, 1]
    report = candidate_report({"coefficients": integer_from_factors([-2, 0, 1], coefficient), "interval": [1, 2]})
    sqrt_two = Decimal(2).sqrt()
    assert_farey_profile(report, [sqrt_two, sqrt_two + Decimal("0.01")])


def test_clustered_irrational_roots_use_farey():
    """「无理根使用 64 阶 Farey 序列：`lower` 和 `upper` 必须是该序列中包含根的一对相邻分数」"""
    root_shift = Fraction(1, 200)
    coefficient = [root_shift * root_shift - 2, -2 * root_shift, 1]
    report = candidate_report({"coefficients": integer_from_factors([-2, 0, 1], coefficient), "interval": [1, 2]})
    sqrt_two = Decimal(2).sqrt()
    assert_farey_profile(report, [sqrt_two, sqrt_two + Decimal("0.005")])


def test_farey_refines_past_point_root():
    """「如果一个 Farey 单元还包含别的根，就继续提高阶数，直到每个单元只含一个根」"""
    quadratic = [Fraction(-41, 25), Fraction(-6, 5), Fraction(1)]
    factors = [[-2, 1], quadratic]
    report = candidate_report({"coefficients": integer_from_factors(*factors), "interval": [-8, 3]})
    three_fifths = Decimal(3) / Decimal(5)
    sqrt_two = Decimal(2).sqrt()
    assert_adaptive_farey_profile(
        report,
        [Decimal(2), three_fifths - sqrt_two, three_fifths + sqrt_two],
        [Fraction(2)],
        lower=Fraction(-8),
        upper=Fraction(3),
    )


def test_sqrt_two_uses_farey_bracket():
    """「无理根使用 64 阶 Farey 序列：`lower` 和 `upper` 必须是该序列中包含根的一对相邻分数」"""
    report = candidate_report({"coefficients": [-2, 0, 1], "interval": [1, 2]})
    assert_farey_cell(report, Decimal(2).sqrt())


def test_sqrt_three_uses_farey_bracket():
    """「无理根使用 64 阶 Farey 序列：`lower` 和 `upper` 必须是该序列中包含根的一对相邻分数」"""
    report = candidate_report({"coefficients": [-3, 0, 1], "interval": [1, 2]})
    assert_farey_cell(report, Decimal(3).sqrt())


def test_three_irrational_roots_in_narrow_cluster():
    """「无理根使用 64 阶 Farey 序列：`lower` 和 `upper` 必须是该序列中包含根的一对相邻分数」"""
    first = Fraction(1, 100)
    second = Fraction(2, 100)
    factor_one = [first * first - 2, -2 * first, 1]
    factor_two = [second * second - 2, -2 * second, 1]
    report = candidate_report({"coefficients": integer_from_factors([-2, 0, 1], factor_one, factor_two), "interval": [1, 2]})
    sqrt_two = Decimal(2).sqrt()
    assert_farey_profile(report, [sqrt_two, sqrt_two + Decimal("0.01"), sqrt_two + Decimal("0.02")])
