"""Verify generated query intent survives execution in the conformance app."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ConformanceSqlLogIntentTest(unittest.TestCase):
    def test_generated_queries_retain_intent_at_sql_sink(self):
        repo = Path(__file__).resolve().parents[2]
        env = dict(os.environ)
        env.pop("TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS", None)
        env["PYTHONPATH"] = os.pathsep.join((str(repo / "examples" / "conformance"), str(repo / "src")))
        with tempfile.TemporaryDirectory(prefix="teaql-conformance-log-test-") as directory:
            env["TEAQL_CONFORMANCE_DB"] = str(Path(directory) / "conformance.sqlite")
            result = subprocess.run([sys.executable, "-m", "app.main"], cwd=repo,
                                    env=env, capture_output=True, text=True, timeout=90)
        output = result.stdout + result.stderr
        self.assertEqual(0, result.returncode, output)
        generated_flow = output.split("PASS Mutation ledger identity", 1)[-1]
        queries = [line for line in generated_flow.splitlines()
                   if line.startswith("[TeaQL SQL]") and "[select]" in line]
        self.assertGreater(len(queries), 0, output)
        for line in queries:
            self.assertNotIn("comment=None", line)
            self.assertNotIn("purpose=None", line)
        self.assertIn("PASS Python minimum runtime conformance: 8/8", output)


if __name__ == "__main__":
    unittest.main()
