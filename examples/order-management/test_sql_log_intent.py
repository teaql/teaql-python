"""Check the regenerated order library's SQL intent through its real app."""
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
        env["PYTHONPATH"] = os.pathsep.join((str(repo / "examples" / "order-management" / "python-lib-core"), str(repo / "src")))
        with tempfile.TemporaryDirectory(prefix="teaql-order-log-test-") as directory:
            env["TEAQL_ORDER_MANAGEMENT_DB"] = str(Path(directory) / "order.sqlite")
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("python-app-console") / "app.py")],
                                    cwd=repo, env=env, capture_output=True, text=True, timeout=90)
        output = result.stdout + result.stderr
        self.assertEqual(0, result.returncode, output)
        queries = [line for line in output.splitlines()
                   if line.startswith("[TeaQL SQL]") and "[select]" in line]
        self.assertGreater(len(queries), 0, output)
        for line in queries:
            self.assertNotIn("comment=None", line)
            self.assertNotIn("purpose=None", line)
        self.assertNotIn("masked-in-quick-start", output)
        customer_sql = next((line for line in output.splitlines()
                             if "INSERT INTO customer_data" in line), "")
        self.assertIn("/* masked */", customer_sql)
        self.assertIn("'Acme Retail'", customer_sql)
        self.assertIn("[schema] ensured 7 generated entity tables", output)


if __name__ == "__main__":
    unittest.main()
