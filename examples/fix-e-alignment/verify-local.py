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
        boundary_directory = evidence / "checker-boundaries"
        boundary_directory.mkdir()
        boundary_command = [sys.executable, str(EXAMPLE / "checker_boundaries.py"),
                            "--source", str(REPO), "--output", str(boundary_directory)]
        boundary_log = evidence / "checker-boundaries.log"
        with boundary_log.open("w") as output:
            boundary_result = subprocess.run(boundary_command, cwd=REPO, env=environment, stdout=output,
                                             stderr=subprocess.STDOUT, check=False, timeout=180)
        report["checkerBoundaries"] = {"command": boundary_command, "exitCode": boundary_result.returncode,
                                      "applicationSha256": hashlib.sha256((EXAMPLE / "checker_boundaries.py").read_bytes()).hexdigest(),
                                      "logSha256": hashlib.sha256(boundary_log.read_bytes()).hexdigest()}
        assert boundary_result.returncode == 0, boundary_log.read_text()[-12000:]
        boundary_rows = [json.loads(line[len("PYTHON_CHECKER_BOUNDARY_RESULT="):])
                         for line in boundary_log.read_text().splitlines() if line.startswith("PYTHON_CHECKER_BOUNDARY_RESULT=")]
        assert len(boundary_rows) == 1 and boundary_rows[0]["passed"] is True
        assert boundary_rows[0]["observedCases"] == 63 and boundary_rows[0]["rounds"] == 2
        assert boundary_rows[0]["sameDatabase"] and boundary_rows[0]["requiredAndRangeObserveActualFix"]
        assert not boundary_rows[0]["schemaFreeDatabaseCreated"]
        report["checkerBoundaries"]["observedCases"] = 63
        report["checkerBoundaries"]["databaseSha256"] = hashlib.sha256((boundary_directory / "fixture.sqlite").read_bytes()).hexdigest()
        assert not (boundary_directory / "never-created.sqlite").exists()
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
        report["partialRootLoading"] = []
        report["partialRootApplicationSha256"] = hashlib.sha256((EXAMPLE / "partial_root_loading.py").read_bytes()).hexdigest()
        for index in (1, 2):
            command = [sys.executable, str(EXAMPLE / "partial_root_loading.py"),
                       "--database", str(evidence / "partial-root.sqlite"), "--round", str(index)]
            log = evidence / f"partial-root-round-{index}.log"
            with log.open("w") as output:
                result = subprocess.run(command, cwd=REPO, env=environment, stdout=output,
                                        stderr=subprocess.STDOUT, check=False, timeout=120)
            report["partialRootLoading"].append({"command": command, "exitCode": result.returncode,
                                                "logSha256": hashlib.sha256(log.read_bytes()).hexdigest()})
            assert result.returncode == 0, log.read_text()[-12000:]
            frames = [json.loads(line[len("PYTHON_PARTIAL_ROOT_RESULT="):]) for line in log.read_text().splitlines()
                      if line.startswith("PYTHON_PARTIAL_ROOT_RESULT=")]
            assert len(frames) == 1 and frames[0]["passed"] and frames[0]["round"] == index
        report["partialRootDatabaseSha256"] = hashlib.sha256((evidence / "partial-root.sqlite").read_bytes()).hexdigest()
        report["independentProjectionViews"] = []
        report["projectionApplicationSha256"] = hashlib.sha256((EXAMPLE / "projection_views.py").read_bytes()).hexdigest()
        for index in (1, 2):
            command = [sys.executable, str(EXAMPLE / "projection_views.py"),
                       "--database", str(evidence / "projection-views.sqlite"), "--round", str(index)]
            log = evidence / f"projection-views-round-{index}.log"
            with log.open("w") as output:
                result = subprocess.run(command, cwd=REPO, env=environment, stdout=output,
                                        stderr=subprocess.STDOUT, check=False, timeout=120)
            report["independentProjectionViews"].append({"command": command, "exitCode": result.returncode,
                                                        "logSha256": hashlib.sha256(log.read_bytes()).hexdigest()})
            assert result.returncode == 0, log.read_text()[-12000:]
            frames = [json.loads(line[len("PYTHON_PROJECTION_VIEW_COMPLETE="):])
                      for line in log.read_text().splitlines() if line.startswith("PYTHON_PROJECTION_VIEW_COMPLETE=")]
            assert len(frames) == 1 and frames[0]["passed"] and frames[0]["round"] == index and frames[0]["cases"] == 3
        report["projectionDatabaseSha256"] = hashlib.sha256((evidence / "projection-views.sqlite").read_bytes()).hexdigest()
        report["unchangedViews"] = []
        report["unchangedViewApplicationSha256"] = hashlib.sha256((EXAMPLE / "unchanged_views.py").read_bytes()).hexdigest()
        expected_cases = ["sparse-restored-values-null-properties-and-edge", "repeat-clean-sparse-save",
                          "other-row-pending-intent-and-values-retained", "row-owned-properties-and-loaded-null-retained",
                          "rejected-property-selection-retains-prior-view"]
        for index in (1, 2):
            command = [sys.executable, str(EXAMPLE / "unchanged_views.py"),
                       "--database", str(evidence / "unchanged-views.sqlite"), "--round", str(index)]
            log = evidence / f"unchanged-views-round-{index}.log"
            with log.open("w") as output:
                result = subprocess.run(command, cwd=REPO, env=environment, stdout=output,
                                        stderr=subprocess.STDOUT, check=False, timeout=120)
            report["unchangedViews"].append({"command": command, "exitCode": result.returncode,
                                            "logSha256": hashlib.sha256(log.read_bytes()).hexdigest()})
            assert result.returncode == 0, log.read_text()[-12000:]
            frames = [json.loads(line[len("PYTHON_UNCHANGED_VIEW_CASE="):])
                      for line in log.read_text().splitlines() if line.startswith("PYTHON_UNCHANGED_VIEW_CASE=")]
            assert [frame["case"] for frame in frames] == expected_cases
            assert all(frame["passed"] and frame["round"] == index and not frame["pending"]
                       and all(count == 0 for count in frame["effects"].values()) for frame in frames)
            for marker in ("PYTHON_UNCHANGED_VIEW_WRITE=", "PYTHON_UNCHANGED_VIEW_PHYSICAL=", "PYTHON_UNCHANGED_VIEW_COMPLETE="):
                rows = [json.loads(line[len(marker):]) for line in log.read_text().splitlines() if line.startswith(marker)]
                assert len(rows) == 1 and rows[0]["passed"] and rows[0]["round"] == index
        report["unchangedViewDatabaseSha256"] = hashlib.sha256((evidence / "unchanged-views.sqlite").read_bytes()).hexdigest()
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
