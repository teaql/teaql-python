from pathlib import Path
import runpy
import sys

workspace = Path(__file__).resolve().parents[1]
probes = workspace / "showcase"
library = workspace.parent / "python-lib-core"
sys.path[:0] = [str(probes), str(library)]
sys.argv = [str(probes / "verify.py"), "--generated", str(library), *sys.argv[1:]]
runpy.run_path(str(probes / "verify.py"), run_name="__main__")
