"""Run the real example; do not infer governance from process exit zero alone."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class TaskBoardLogContractTest(unittest.TestCase):
    def test_default_logs_have_intent_and_mask_business_values(self):
        repo = Path(__file__).resolve().parents[2]
        env = dict(os.environ)
        env.pop("TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS", None)
        env["PYTHONPATH"] = str(repo / "src")
        with tempfile.TemporaryDirectory(prefix="teaql-task-board-test-") as temporary:
            env["TEAQL_TASK_BOARD_DB"] = str(Path(temporary) / "task-board.db")
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("main.py"))],
                                    env=env, capture_output=True, text=True, timeout=90)
        output = result.stdout + result.stderr
        self.assertEqual(0, result.returncode, output)
        queries = writes = 0
        for line in output.splitlines():
            if not line.startswith("[TeaQL SQL]"):
                continue
            if "[select]" in line or "[query]" in line:
                queries += 1
                self.assertNotIn("comment=None", line)
                self.assertNotIn("purpose=None", line)
                self.assertNotIn("comment= purpose=", line)
                self.assertNotIn("purpose= auditReason=", line)
            elif any(f"[{kind}]" in line for kind in ("insert", "update", "delete")):
                writes += 1
                self.assertNotIn("auditReason=None", line)
                self.assertNotIn("auditReason= tracePath=", line)
        self.assertGreater(queries, 0, output)
        self.assertGreater(writes, 0, output)
        self.assertIn("PASS task board: governed Q/E/mutation and masked detail", output)
        self.assertNotIn("PRIVATE-TASK-DETAIL", output)
        self.assertIn("'PR***************IL' /* masked */", output)
        self.assertIn("'RENAME'", output)
        self.assertIn("comment='page renamed task' purpose='verify paginated task intent'", output)
        self.assertIn("comment='stream renamed task' purpose='verify streamed task intent'", output)


if __name__ == "__main__":
    unittest.main()
