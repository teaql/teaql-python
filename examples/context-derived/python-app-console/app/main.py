"""Context-derived business fields through the generated Catalog/Entry model."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[1]/"showcase/verify.py"),run_name="__main__")
