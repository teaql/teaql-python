"""The gate must reap its own commands without touching unrelated processes."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

SOURCE = Path(__file__).parents[2] / "scripts/verify-natural-messages.py"
spec = importlib.util.spec_from_file_location("natural_message_gate", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_success_preserves_status_and_ends_owned_group(tmp_path):
    runner = module.OwnedRunner()
    code = runner.run([sys.executable, "-c", "print('completed')"], log=tmp_path / "success.log", cwd=tmp_path, env=os.environ)
    assert code == 0 and runner.safe_to_clean
    assert (tmp_path / "success.log").read_text().strip() == "completed"


def test_failure_preserves_original_exit_status(tmp_path):
    runner = module.OwnedRunner()
    code = runner.run([sys.executable, "-c", "raise SystemExit(17)"], log=tmp_path / "failure.log", cwd=tmp_path, env=os.environ)
    assert code == 17 and runner.safe_to_clean


def test_timeout_stops_only_owned_process(tmp_path):
    control = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
    try:
        runner = module.OwnedRunner()
        code = runner.run([sys.executable, "-c", "import time; time.sleep(30)"], log=tmp_path / "timeout.log", cwd=tmp_path, env=os.environ, timeout=.1)
        assert code == 124 and runner.safe_to_clean and control.poll() is None
    finally:
        control.terminate()
        control.wait(timeout=2)
