"""Run this repository's generated Q/E/Fix/loading/mutation example twice.

Usage: python examples/fix-e-alignment/verify-local.py
TEAQL_FIX_E_EVIDENCE_DIR may select an unused absolute output directory. Compact
logs, receipts and the synthetic database are retained; no builds/venvs are made.
The fixture is validated generation output, not an embedded runtime snapshot.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


EXAMPLE = Path(__file__).resolve().parent
REPO = EXAMPLE.parents[1]


def fingerprint():
    manifest = json.loads((EXAMPLE / "fixture-manifest.json").read_text())
    assert manifest["language"] == "python" and manifest["evaluationErrors"] == 0
    assert hashlib.sha256((EXAMPLE / "model.xml").read_bytes()).hexdigest() == manifest["modelSha256"]
    generated = EXAMPLE / "generated"
    actual = sorted(str(p.relative_to(generated)) for p in generated.rglob("*")
                    if p.is_file() and p.suffix != ".pyc")
    assert actual == sorted(manifest["files"]), "generated fixture inventory changed"
    for name, expected in manifest["files"].items():
        original = generated / name
        assert not original.is_symlink()
        assert hashlib.sha256(original.read_bytes()).hexdigest() == expected, name
    return manifest


def main():
    destination = os.environ.get("TEAQL_FIX_E_EVIDENCE_DIR")
    if destination:
        evidence = Path(destination)
        assert evidence.is_absolute() and not evidence.exists(), "use an unused absolute evidence path"
        evidence.mkdir(parents=True)
    else:
        evidence = Path(tempfile.mkdtemp(prefix="teaql-python-fix-e-evidence-"))
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(REPO / "src"))
    manifest = fingerprint()
    report = {"schema": "teaql.python-fix-e-example/v1", "passed": False, "rounds": [],
              "sameDatabase": True, "runtimeSource": str(REPO / "src"),
              "modelSha256": manifest["modelSha256"], "generatedFiles": len(manifest["files"]),
              "buildOutputsCreated": False, "databaseRetained": True}
    status = 1
    try:
        provenance = subprocess.run([sys.executable, "-c",
            "import pathlib, teaql; assert pathlib.Path(teaql.__file__).resolve().is_relative_to(pathlib.Path(" + repr(str(REPO / "src")) + ")), 'not the repository runtime'"],
            cwd=REPO, env=environment, check=False, timeout=30)
        assert provenance.returncode == 0
        for index in (1, 2):
            command = [sys.executable, str(EXAMPLE / "verify.py"), "--generated", str(EXAMPLE / "generated"),
                       "--database", str(evidence / "fixture.sqlite")]
            if index == 2:
                command.append("--reuse-database")
            log = evidence / f"round-{index}.log"
            with log.open("w") as output:
                result = subprocess.run(command, cwd=REPO, env=environment, stdout=output,
                                        stderr=subprocess.STDOUT, check=False, timeout=120)
            report["rounds"].append({"command": command, "exitCode": result.returncode,
                                    "logSha256": hashlib.sha256(log.read_bytes()).hexdigest()})
            if result.returncode:
                print(log.read_text()[-12000:], file=sys.stderr)
                status = result.returncode
                return status
            lines = log.read_text().splitlines()
            for marker in ("FIX_E_EXAMPLE=", "CORE_LOAD_EXAMPLE=", "CORE_MUTATION_OWNERSHIP=", "CORE_MUTATION_PAGING="):
                values = [json.loads(line[len(marker):]) for line in lines if line.startswith(marker)]
                assert len(values) == 1 and values[0]["passed"] is True, marker
            assert fingerprint() == manifest
        checker_command = [sys.executable, str(EXAMPLE / "checker_diagnostics.py"),
                           "--database", str(evidence / "checker.sqlite")]
        checker_log = evidence / "checker.log"
        with checker_log.open("w") as output:
            checker_result = subprocess.run(checker_command, cwd=REPO, env=environment, stdout=output,
                                            stderr=subprocess.STDOUT, check=False, timeout=120)
        report["checkerMetadata"] = {"command": checker_command, "exitCode": checker_result.returncode,
                                     "logSha256": hashlib.sha256(checker_log.read_bytes()).hexdigest()}
        assert checker_result.returncode == 0, checker_log.read_text()[-12000:]
        checker_rows = [json.loads(line[len("CHECKER_METADATA="):])
                        for line in checker_log.read_text().splitlines() if line.startswith("CHECKER_METADATA=")]
        assert len(checker_rows) == 1 and checker_rows[0]["passed"] is True
        assert checker_rows[0]["invalidSaves"] == 16 and checker_rows[0]["rounds"] == 2
        report["checkerMetadata"]["invalidSaves"] = 16
        report["checkerMetadata"]["databaseSha256"] = hashlib.sha256((evidence / "checker.sqlite").read_bytes()).hexdigest()
        report["partialGraphLoading"] = []
        for index in (1, 2):
            command = [sys.executable, str(EXAMPLE / "partial_graph_loading.py"),
                       "--database", str(evidence / "partial-graph.sqlite"), "--round", str(index)]
            log = evidence / f"partial-graph-round-{index}.log"
            with log.open("w") as output:
                result = subprocess.run(command, cwd=REPO, env=environment, stdout=output,
                                        stderr=subprocess.STDOUT, check=False, timeout=120)
            report["partialGraphLoading"].append({"command": command, "exitCode": result.returncode,
                                                 "logSha256": hashlib.sha256(log.read_bytes()).hexdigest()})
            assert result.returncode == 0, log.read_text()[-12000:]
            frames = [json.loads(line[len("PARTIAL_GRAPH_LOAD="):]) for line in log.read_text().splitlines()
                      if line.startswith("PARTIAL_GRAPH_LOAD=")]
            assert len(frames) == 1 and frames[0]["passed"] and frames[0]["round"] == index
        report["partialGraphDatabaseSha256"] = hashlib.sha256((evidence / "partial-graph.sqlite").read_bytes()).hexdigest()
        assert fingerprint() == manifest
        report["databaseSha256"] = hashlib.sha256((evidence / "fixture.sqlite").read_bytes()).hexdigest()
        report["passed"] = True
        status = 0
        print("PASS Python retained Fix/E/loading/ownership example twice on one database")
        return status
    finally:
        report["exitCode"] = status
        (evidence / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
        print("Retained compact example evidence: " + str(evidence))


if __name__ == "__main__":
    sys.exit(main())
