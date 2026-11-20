"""Catalog and Entry validation through the generated domain library."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "showcase/verify.py"), run_name="__main__")
