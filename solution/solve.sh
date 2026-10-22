#!/usr/bin/env bash
# 参考解：安装完整实现；HTB_SKIP 将指定难点的修复退回初始写法。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
install -m 0644 "$HERE/app/main.py" /app/main.py

SKIP="${HTB_SKIP:-}" /usr/local/bin/python3 - /app/main.py <<'PY'
import os
import sys
from pathlib import Path

REVERT = {
    "difficulty_1": (
        "for root in rational_roots_of_factor(factor):",
        "for root in []:",
    ),
    "difficulty_2": (
        "factors = square_free_factors(poly)",
        "factors = legacy_factors(poly)",
    ),
    "difficulty_3": (
        "intervals = collect_intervals(radical, lower, upper, isolate_by_sturm)\n    for left, right in intervals:\n        cell = dyadic_cell(radical, left, right)",
        "intervals = collect_intervals(radical, lower, upper, isolate_by_signs)\n    for left, right in intervals:\n        cell = (left, right)",
    ),
}
skip = [item for item in os.environ.get("SKIP", "").split(",") if item]
unknown = sorted(set(skip) - set(REVERT))
if unknown:
    sys.exit(f"HTB_SKIP 里有未知难点：{unknown}")
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
for key in skip:
    fixed, original = REVERT[key]
    if text.count(fixed) != 1:
        sys.exit(f"{key} 的修复片段在参考实现里出现 {text.count(fixed)} 次，应为 1")
    text = text.replace(fixed, original)
    print(f"留一法：{key} 退回原写法", file=sys.stderr)
path.write_text(text, encoding="utf-8")
PY
chown runner:runner /app/main.py 2>/dev/null || true
