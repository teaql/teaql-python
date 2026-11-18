"""Check the regenerated order library's SQL intent through its real app."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class OrderSqlLogIntentTest(unittest.TestCase):
    def test_generated_queries_retain_intent_at_sql_sink(self):
        repo = Path(__file__).resolve().parents[2]
        env = dict(os.environ)
        env.pop("TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS", None)
        env.pop("TEAQL_LOG_FORMAT", None)
        env["TEAQL_LOG_ENDPOINT"] = "stdout"
        env["PYTHONPATH"] = os.pathsep.join((str(repo / "examples" / "order-management" / "python-lib-core"), str(repo / "src")))
        with tempfile.TemporaryDirectory(prefix="teaql-order-log-test-") as directory:
            env["TEAQL_ORDER_MANAGEMENT_DB"] = str(Path(directory) / "order.sqlite")
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("python-app-console") / "app.py")],
                                    cwd=repo, env=env, capture_output=True, text=True, timeout=90)
        output = result.stdout + result.stderr
        self.assertEqual(0, result.returncode, output)
        records = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
        queries = [row for row in records if row.get("event") == "sql.select"]
        self.assertGreater(len(queries), 0, output)
        for row in queries:
            self.assertTrue(row.get("comment") and row["comment"].strip(), row)
            self.assertTrue(row.get("purpose") and row["purpose"].strip(), row)
        self.assertNotIn("masked-in-quick-start", output)
        customer_sql = next((row.get("sql", "") for row in records
                             if "INSERT INTO customer_data" in row.get("sql", "")), "")
        self.assertIn("/* masked */", customer_sql)
        self.assertIn("'Acme Retail'", customer_sql)
        self.assertIn("[schema] ensured 7 generated entity tables", output)


if __name__ == "__main__":
    unittest.main()
