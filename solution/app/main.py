"""整数多项式实根清单的参考实现。

用法：python3 /app/main.py <input.json>
"""

from fractions import Fraction
from math import ceil, gcd, isqrt, lcm
import json
import sys

RATIONAL_DENOMINATOR_LIMIT = 10**12
D1_ENABLED = True


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


def multiply(left, right):
    result = [Fraction(0)] * (len(left) + len(right) - 1)
    for i, a_value in enumerate(left):
        for j, b_value in enumerate(right):
            result[i + j] += a_value * b_value
    return trim(result)


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


def integer_primitive(poly):
    common_denominator = 1
    for value in poly:
        common_denominator = lcm(common_denominator, value.denominator)
    integers = [int(value * common_denominator) for value in poly]
    common = 0
    for value in integers:
        common = gcd(common, abs(value))
    if common:
        integers = [value // common for value in integers]
    return trim([Fraction(value) for value in integers])


def divisors_up_to(value, limit):
    value = abs(value)
    if value == 0:
        return [1]
    result = set()
    root = min(isqrt(value), limit)
    for divisor in range(1, root + 1):
        if value % divisor == 0:
            result.add(divisor)
            partner = value // divisor
            if partner <= limit:
                result.add(partner)
    return sorted(result)


def rational_roots_of_factor(poly):
    """返回分母有界的有理根；分母更大的点根留给区间隔离。"""
    roots = []
    work = trim(poly)
    if degree(work) >= 1 and evaluate(work, 0) == 0:
        roots.append(Fraction(0))
        work = divide_linear(work, 0)
    if degree(work) < 1:
        return roots
    primitive = integer_primitive(work)
    constant = int(primitive[0])
    leading = int(primitive[-1])
    if constant == 0 or leading == 0:
        return roots
    numerators = divisors_up_to(constant, 10**12)
    denominators = divisors_up_to(leading, RATIONAL_DENOMINATOR_LIMIT)
    candidates = {Fraction(sign * numerator, denominator)
                  for numerator in numerators
                  for denominator in denominators
                  for sign in (-1, 1)}
    for candidate in sorted(candidates):
        if evaluate(work, candidate) == 0 and candidate not in roots:
            roots.append(candidate)
    return sorted(roots)


def legacy_factors(poly):
    common = gcd_poly(poly, derivative(poly))
    radical = div_exact(poly, common)
    multiplier = 2 if degree(common) > 0 else 1
    return [(radical, multiplier)]


def square_free_factors(poly):
    common = gcd_poly(poly, derivative(poly))
    radical = div_exact(poly, common)
    remaining = monic(radical)
    groups = []
    multiplicity = 1
    while degree(remaining) >= 1:
        shared = gcd_poly(common, remaining)
        current = div_exact(remaining, shared)
        if degree(current) >= 1:
            groups.append((monic(current), multiplicity))
        remaining = monic(shared)
        common = div_exact(common, shared)
        multiplicity += 1
    return groups


def scale_positive(poly):
    poly = trim(poly)
    if poly == [Fraction(0)]:
        return poly
    scale = abs(poly[-1])
    return [value / scale for value in poly]


def sturm_chain(poly):
    first = scale_positive(poly)
    if degree(first) < 1:
        return [first]
    chain = [first, scale_positive(derivative(first))]
    while degree(chain[-1]) >= 1:
        _, remainder = divmod_poly(chain[-2], chain[-1])
        if remainder == [Fraction(0)]:
            break
        chain.append(scale_positive([-value for value in remainder]))
    return chain


def variations(chain, point):
    signs = []
    for poly in chain:
        value = evaluate(poly, point)
        if value < 0:
            signs.append(-1)
        elif value > 0:
            signs.append(1)
    return sum(1 for left, right in zip(signs, signs[1:]) if left != right)


def root_count(chain, lower, upper):
    return variations(chain, lower) - variations(chain, upper)


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


def isolate_by_sturm(poly, lower, upper):
    lower = Fraction(lower)
    upper = Fraction(upper)
    if degree(poly) < 1:
        return []
    chain = sturm_chain(poly)
    count = root_count(chain, lower, upper)
    if count <= 0:
        return []
    if count == 1:
        return [(lower, upper)]
    middle = (lower + upper) / 2
    if evaluate(poly, middle) == 0:
        reduced = divide_linear(poly, middle)
        return sorted(
            [(middle, middle)]
            + isolate_by_sturm(reduced, lower, middle)
            + isolate_by_sturm(reduced, middle, upper)
        )
    return sorted(
        isolate_by_sturm(poly, lower, middle)
        + isolate_by_sturm(poly, middle, upper)
    )


def peel_endpoints(poly, lower, upper):
    boundary = []
    work = poly
    for point in (Fraction(lower), Fraction(upper)):
        if degree(work) >= 1 and evaluate(work, point) == 0:
            boundary.append((point, point))
            work = divide_linear(work, point)
    return work, boundary


def shrink_open_bounds(poly, lower, upper):
    chain = sturm_chain(poly)
    total = root_count(chain, lower, upper)
    if total <= 0:
        return lower, upper
    span = upper - lower
    step = span / 2
    new_lower = lower + step
    while root_count(chain, new_lower, upper) < total:
        step /= 2
        new_lower = lower + step
    step = span / 2
    new_upper = upper - step
    while root_count(chain, lower, new_upper) < total:
        step /= 2
        new_upper = upper - step
    return new_lower, new_upper


FAREY_ORDER = 64


def farey_sequence(lower, upper, order=FAREY_ORDER):
    values = set()
    for denominator in range(1, order + 1):
        start = ceil(lower * denominator)
        end = (upper * denominator).numerator // (upper * denominator).denominator
        for numerator in range(start, end + 1):
            if numerator and gcd(abs(numerator), denominator) != 1:
                continue
            values.add(Fraction(numerator, denominator))
    values.add(Fraction(lower))
    values.add(Fraction(upper))
    return sorted(values)


def farey_bracket(poly, left, right, sequence):
    """返回 64 阶 Farey 序列中包含该根的一对相邻分数。"""
    chain = sturm_chain(poly)
    below = None
    above = None
    for candidate in sequence:
        if candidate <= left:
            below = candidate
            continue
        if candidate >= right:
            above = candidate
            break
        if evaluate(poly, candidate) == 0:
            return candidate, candidate
        if root_count(chain, left, candidate) == 0:
            below = candidate
        else:
            above = candidate
            break
    if below is None:
        below = left
    if above is None:
        above = right
    return below, above


GRID_BITS = 40


def dyadic_cell(poly, left, right):
    """把一个单一实根区间收紧到固定的 2^-40 网格单元。"""
    scale = 1 << GRID_BITS
    chain = sturm_chain(poly)
    left_scaled = Fraction(left) * scale
    right_scaled = Fraction(right) * scale
    low = left_scaled.numerator // left_scaled.denominator
    high = right_scaled.numerator // right_scaled.denominator + 1
    while high - low > 1:
        middle = (low + high) // 2
        point = Fraction(middle, scale)
        if evaluate(poly, point) == 0:
            return point, point
        if root_count(chain, Fraction(left), point) == 0:
            low = middle
        else:
            high = middle
    for index in (low, low + 1):
        point = Fraction(index, scale)
        if evaluate(poly, point) == 0:
            return point, point
    return Fraction(low, scale), Fraction(low + 1, scale)


def collect_intervals(poly, lower, upper, isolator):
    lower = Fraction(lower)
    upper = Fraction(upper)
    if D1_ENABLED:
        work, boundary = peel_endpoints(poly, lower, upper)
    else:
        work, boundary = poly, []
    if degree(work) < 1:
        return sorted(boundary)
    if boundary:
        lower, upper = shrink_open_bounds(work, lower, upper)
    return sorted(boundary + isolator(work, lower, upper))


def multiplicity_for(factors, lower, upper):
    if lower == upper:
        hits = [mult for factor, mult in factors if evaluate(factor, lower) == 0]
    else:
        hits = []
        for factor, mult in factors:
            if evaluate(factor, lower) * evaluate(factor, upper) < 0:
                hits.append(mult)
    if len(hits) != 1:
        raise ArithmeticError("root interval does not identify one multiplicity")
    return hits[0]


def fraction_text(value):
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def build_report(poly, lower, upper):
    factors = square_free_factors(poly)
    radical = [Fraction(1)]
    for factor, _ in factors:
        radical = multiply(radical, factor)
    roots = []
    seen = set()
    if D1_ENABLED:
        for factor, multiplicity in factors:
            for root in rational_roots_of_factor(factor):
                if not (lower <= root <= upper) or root in seen:
                    continue
                seen.add(root)
                roots.append((root, root, multiplicity))
                radical = divide_linear(radical, root)
    intervals = collect_intervals(radical, lower, upper, isolate_by_sturm)
    point_roots = [root for root, _, _ in roots]
    for left, right in intervals:
        order = FAREY_ORDER
        while True:
            cell = farey_bracket(radical, left, right, farey_sequence(lower, upper, order))
            chain = sturm_chain(radical)
            isolated = root_count(chain, cell[0], cell[1]) == 1
            shares_point = any(cell[0] <= point <= cell[1] for point in point_roots)
            if isolated and not shares_point:
                break
            order *= 2
        roots.append((cell[0], cell[1], multiplicity_for(factors, cell[0], cell[1])))
    roots.sort(key=lambda item: (item[0], item[1]))
    output = [
        {
            "lower": fraction_text(left),
            "upper": fraction_text(right),
            "multiplicity": multiplicity,
        }
        for left, right, multiplicity in roots
    ]
    return {
        "roots": output,
        "distinct_count": len(output),
        "multiplicity_sum": sum(item["multiplicity"] for item in output),
    }


def main(argv):
    if len(argv) != 2:
        print("usage: python3 /app/main.py <input.json>", file=sys.stderr)
        return 2
    try:
        with open(argv[1], "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        coefficients = trim([Fraction(value) for value in payload["coefficients"]])
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
