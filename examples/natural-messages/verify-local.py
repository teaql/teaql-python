"""Example-only entry into the shared source/cleanup gate."""
import os
from pathlib import Path
import runpy
import sys
import tempfile

if __name__ == "__main__":
    requested = os.environ.get("TEAQL_NATURAL_MESSAGES_EVIDENCE_DIR")
    output = requested or str(Path(tempfile.mkdtemp(prefix="teaql-python-natural-evidence-")) / "run")
    sys.argv += ["--example-only", "--output", output]
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/verify-natural-messages.py"), run_name="__main__")
