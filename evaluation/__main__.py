"""Print the evaluation report.

python -m evaluation
"""

from __future__ import annotations

import sys
import os


def main() -> int:
    # This command measures fixed, deterministic scenarios. A developer's .env
    # must not silently enable paid generation or telemetry for this check.
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["LANGFUSE_ENABLED"] = "false"
    os.environ["LANGFUSE_REQUIRED"] = "false"
    from app.core.config import get_settings
    from evaluation.metrics import evaluate

    get_settings.cache_clear()
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
