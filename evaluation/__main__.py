"""Print the evaluation report.

python -m evaluation
"""

from __future__ import annotations

import sys

from evaluation.metrics import evaluate


def main() -> int:
    report = evaluate()
    print("\n".join(report.as_lines()))
    # Non-zero when a deterministic measure is not perfect, so this is usable
    # as a check outside pytest too.
    perfect = (
        report.gating_accuracy == 1.0
        and report.citation_coverage == 1.0
        and report.contradiction_recall == 1.0
    )
    return 0 if perfect else 1


if __name__ == "__main__":
    sys.exit(main())
