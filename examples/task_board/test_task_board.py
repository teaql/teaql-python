"""Run the real example; do not infer governance from process exit zero alone."""
import json
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
        env.pop("TEAQL_LOG_FORMAT", None)
        env["TEAQL_LOG_ENDPOINT"] = "stdout"
        env["PYTHONPATH"] = str(repo / "src")
        with tempfile.TemporaryDirectory(prefix="teaql-task-board-test-") as temporary:
            env["TEAQL_TASK_BOARD_DB"] = str(Path(temporary) / "task-board.db")
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("main.py"))],
                                    env=env, capture_output=True, text=True, timeout=90)
        output = result.stdout + result.stderr
        self.assertEqual(0, result.returncode, output)
        records = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
        queries = writes = 0
        for row in records:
            if row.get("category") != "SQL":
                continue
            if row.get("event") in ("sql.select", "sql.query"):
                queries += 1
                self.assertTrue(row.get("comment") and row["comment"].strip(), row)
                self.assertTrue(row.get("purpose") and row["purpose"].strip(), row)
            elif row.get("event") in ("sql.insert", "sql.update", "sql.delete"):
                writes += 1
                self.assertTrue(row.get("audit_reason") and row["audit_reason"].strip(), row)
        self.assertGreater(queries, 0, output)
        self.assertGreater(writes, 0, output)
        self.assertIn("PASS task board: governed Q/E/mutation and masked detail", output)
        self.assertNotIn("PRIVATE-TASK-DETAIL", output)
        self.assertIn("'PR***************IL' /* masked */", output)
        self.assertIn("'RENAME'", output)
        self.assertTrue(any(row.get("comment") == "page renamed task" and
                            row.get("purpose") == "verify paginated task intent" for row in records))
        self.assertTrue(any(row.get("comment") == "stream renamed task" and
                            row.get("purpose") == "verify streamed task intent" for row in records))


if __name__ == "__main__":
    unittest.main()
