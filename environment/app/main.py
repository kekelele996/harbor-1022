"""整数多项式实根清单生成器。

用法：python3 /app/main.py <input.json>
"""

from fractions import Fraction
import json
import sys


def trim(poly):
    poly = list(poly)
    while len(poly) > 1 and poly[-1] == 0:
        poly.pop()
    return poly


def degree(poly):
    poly = trim(poly)
    return len(poly) - 1 if poly != [Fraction(0)] else -1


def derivative(poly):
    if len(poly) <= 1:
        return [Fraction(0)]
    return trim([Fraction(i) * poly[i] for i in range(1, len(poly))])


def divmod_poly(numerator, denominator):
    numerator = trim(numerator)
    denominator = trim(denominator)
    if denominator == [Fraction(0)]:
        raise ValueError("zero divisor")
    quotient = [Fraction(0)] * max(0, len(numerator) - len(denominator) + 1)
    while numerator != [Fraction(0)] and len(numerator) >= len(denominator):
        shift = len(numerator) - len(denominator)
        factor = numerator[-1] / denominator[-1]
        quotient[shift] += factor
        for index, value in enumerate(denominator):
            numerator[index + shift] -= factor * value
        numerator = trim(numerator)
    return trim(quotient), numerator


def div_exact(numerator, denominator):
    quotient, remainder = divmod_poly(numerator, denominator)
    if remainder != [Fraction(0)]:
        raise ArithmeticError("non-exact polynomial division")
    return quotient


def monic(poly):
    poly = trim(poly)
    if poly == [Fraction(0)]:
        return poly
    lead = poly[-1]
    return [value / lead for value in poly]


def gcd_poly(left, right):
    left = trim(left)
    right = trim(right)
    while right != [Fraction(0)]:
        _, remainder = divmod_poly(left, right)
        left, right = right, remainder
    return monic(left)


def evaluate(poly, value):
    result = Fraction(0)
    for coefficient in reversed(poly):
        result = result * value + coefficient
    return result


def divide_linear(poly, root):
    return div_exact(poly, [-root, Fraction(1)])


def factor_profile(poly):
    common = gcd_poly(poly, derivative(poly))
    radical = div_exact(poly, common)
    multiplier = 2 if degree(common) > 0 else 1
    return radical, multiplier


def isolate_by_signs(poly, lower, upper):
    intervals = []
    epsilon = Fraction(1, 1_000_000_000)

    def walk(current, left, right):
        left_value = evaluate(current, left)
        right_value = evaluate(current, right)
        if left_value == 0 or right_value == 0:
            return
        if left_value * right_value > 0:
            return
        if right - left <= epsilon:
            intervals.append((left, right))
            return
        middle = (left + right) / 2
        middle_value = evaluate(current, middle)
        if middle_value == 0:
            intervals.append((middle, middle))
            reduced = divide_linear(current, middle)
            walk(reduced, left, middle)
            walk(reduced, middle, right)
            return
        walk(current, left, middle)
        walk(current, middle, right)

    if degree(poly) >= 1:
        walk(poly, Fraction(lower), Fraction(upper))
    return sorted(intervals)


def fraction_text(value):
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def build_report(poly, lower, upper):
    radical, multiplier = factor_profile(poly)
    intervals = isolate_by_signs(radical, lower, upper)
    roots = [
        {
            "lower": fraction_text(left),
            "upper": fraction_text(right),
            "multiplicity": multiplier,
        }
        for left, right in intervals
    ]
    return {
        "roots": roots,
        "distinct_count": len(roots),
        "multiplicity_sum": sum(item["multiplicity"] for item in roots),
    }


def main(argv):
    if len(argv) != 2:
        print("usage: python3 /app/main.py <input.json>", file=sys.stderr)
        return 2
    try:
        with open(argv[1], "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        coefficients = [Fraction(value) for value in payload["coefficients"]]
        coefficients = trim(coefficients)
        lower, upper = payload["interval"]
        if len(coefficients) < 2 or coefficients[-1] == 0 or Fraction(lower) >= Fraction(upper):
            return 2
        report = build_report(coefficients, Fraction(lower), Fraction(upper))
    except (OSError, ValueError, TypeError, KeyError, ArithmeticError):
        return 2
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
