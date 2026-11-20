"""Verify generated query intent survives execution in the conformance app."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ConformanceSqlLogIntentTest(unittest.TestCase):
    def test_generated_queries_retain_intent_at_sql_sink(self):
        repo = Path(__file__).resolve().parents[3]
        env = dict(os.environ)
        env.pop("TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS", None)
        env.pop("TEAQL_LOG_FORMAT", None)
        env["TEAQL_LOG_ENDPOINT"] = "stdout"
        env["PYTHONPATH"] = os.pathsep.join((str(repo / "examples/conformance/python-lib-core"), str(repo / "examples/conformance/python-app-console"), str(repo / "src")))
        with tempfile.TemporaryDirectory(prefix="teaql-conformance-log-test-") as directory:
            env["TEAQL_CONFORMANCE_DB"] = str(Path(directory) / "conformance.sqlite")
            result = subprocess.run([sys.executable, "-m", "app.main"], cwd=repo,
                                    env=env, capture_output=True, text=True, timeout=90)
        output = result.stdout + result.stderr
        self.assertEqual(0, result.returncode, output)
        generated_flow = output.split("PASS Mutation ledger identity", 1)[-1]
        records = [json.loads(line) for line in generated_flow.splitlines() if line.startswith("{")]
        queries = [row for row in records if row.get("event") == "sql.select"]
        self.assertGreater(len(queries), 0, output)
        for row in queries:
            self.assertTrue(row.get("comment") and row["comment"].strip(), row)
            self.assertTrue(row.get("purpose") and row["purpose"].strip(), row)
        self.assertIn("PASS Python minimum runtime conformance: 8/8", output)


if __name__ == "__main__":
    unittest.main()
