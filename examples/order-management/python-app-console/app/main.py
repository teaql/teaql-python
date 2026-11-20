"""Native workspace entry for the retained Order business program."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.py"), run_name="__main__")
