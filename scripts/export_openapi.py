"""Export the deterministic FastAPI contract without starting a server."""

import json
import os
import sys
from pathlib import Path


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/financial-agent-openapi.json")

    # Keep export reproducible and independent of external providers/LLMs.
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["LANGFUSE_ENABLED"] = "false"
    os.environ["DATA_PROVIDER"] = "json"

    from app.main import app

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
