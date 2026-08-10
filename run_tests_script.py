import subprocess
import sys

try:
    result = subprocess.run(["./venv/bin/pytest", "--cov=teaql", "tests/"], capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    sys.exit(result.returncode)
except Exception as e:
    print(e)
