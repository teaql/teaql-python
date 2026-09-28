"""Exercise the regenerated School library through its real application flow."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class SchoolSqlLogIntentTest(unittest.TestCase):
    def test_generated_queries_retain_intent_at_sql_sink(self):
        repo = Path(__file__).resolve().parents[2]
        env = dict(os.environ)
        env.pop("TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS", None)
        env["PYTHONPATH"] = os.pathsep.join((str(repo / "examples" / "school-management"), str(repo / "src")))
        with tempfile.TemporaryDirectory(prefix="teaql-school-log-test-") as directory:
            env["TEAQL_SCHOOL_MANAGEMENT_DB"] = str(Path(directory) / "school.sqlite")
            result = subprocess.run([sys.executable, "-m", "app.main"], cwd=repo,
                                    env=env, capture_output=True, text=True, timeout=90)
        output = result.stdout + result.stderr
        self.assertEqual(0, result.returncode, output)
        queries = [line for line in output.splitlines()
                   if line.startswith("[TeaQL SQL]") and "[select]" in line]
        self.assertGreater(len(queries), 0, output)
        for line in queries:
            self.assertNotIn("comment=None", line)
            self.assertNotIn("purpose=None", line)
        self.assertIn("PASS Python School Management", output)


if __name__ == "__main__":
    unittest.main()
