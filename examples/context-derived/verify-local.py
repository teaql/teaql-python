"""Run the immutable generated Context Fix example twice with local source."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

EXAMPLE = Path(__file__).resolve().parent
REPO = EXAMPLE.parents[1]
FIXTURE = EXAMPLE / "fixture"


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def fingerprint():
    files = json.loads((FIXTURE / "generated-files.json").read_text())
    actual = []
    for file in FIXTURE.rglob("*"):
        assert not file.is_symlink(), "fixture symlink is forbidden"
        if file.is_file():
            actual.append(str(file.relative_to(FIXTURE)))
    assert sorted(actual) == sorted([*files, "model.xml", "generated-files.json"])
    for name, expected in files.items():
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert sha(FIXTURE / name) == expected, name
    return dict(files=files, manifestSha256=sha(FIXTURE / "generated-files.json"), modelSha256=sha(FIXTURE / "model.xml"))


def source_hash():
    digest = hashlib.sha256()
    for file in sorted((REPO / "src").rglob("*")):
        if file.is_file() and file.suffix != ".pyc":
            assert not file.is_symlink()
            digest.update(str(file.relative_to(REPO)).encode() + b"\0")
            digest.update(file.read_bytes())
    digest.update((REPO / "pyproject.toml").read_bytes())
    return digest.hexdigest()


def run_owned(command, log, env):
    """Only this subprocess group is stopped/reaped; services are never targets."""
    with log.open("x") as output:
        process = subprocess.Popen(command, cwd=REPO, env=env, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return process.wait(timeout=120)
        finally:
            # Interruptions/timeouts must not leave our verifier child running.
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


def main():
    requested = os.environ.get("TEAQL_CONTEXT_FIX_EVIDENCE_DIR")
    output = Path(requested) if requested else Path(tempfile.mkdtemp(prefix="teaql-python-context-evidence-"))
    if requested:
        assert output.is_absolute() and not output.exists(), "use a new absolute evidence directory"
        output.mkdir(parents=True)
    report = dict(schema="teaql.python-context-derived-mutation/v1", passed=False, rounds=[],
                  publicPublication=False, buildOutputsCreated=False, databaseRetained=True)
    status = 1
    try:
        report["fixture"] = fingerprint()
        report["sourceSha256"] = source_hash()
        report["sourceCommit"] = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
        report["applicationSha256"] = sha(EXAMPLE / "verify.py")
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=os.pathsep.join((str(REPO / "src"), str(FIXTURE))),
                           TEAQL_CONTEXT_FIX_SOURCE=str(REPO), TEAQL_CONTEXT_FIX_DB=str(output / "fixture.sqlite"))
        for index in (1, 2):
            command, log = [sys.executable, str(EXAMPLE / "verify.py")], output / f"round-{index}.log"
            code = run_owned(command, log, environment)
            report["rounds"].append(dict(round=index, command=command, exitCode=code, logSha256=sha(log)))
            assert code == 0, log.read_text()[-8000:]
            rows = [json.loads(line.split("=", 1)[1]) for line in log.read_text().splitlines()
                    if line.startswith("PYTHON_CONTEXT_FIX_SQLITE=")]
            assert len(rows) == 1 and rows[0]["passed"]
            for name in ("typedQ", "typedE", "objectLocation", "graphRollback", "fixOnce"):
                assert rows[0][name] is True, name
            assert rows[0]["noOpProviderCalls"] == rows[0]["failedCheckProviderCalls"] == 0
            assert rows[0]["updateAudits"] == 1
            report["rounds"][-1]["observations"] = rows[0]
            assert fingerprint() == report["fixture"] and source_hash() == report["sourceSha256"]
        report.update(passed=True, sameDatabase=True, databaseSha256=sha(output / "fixture.sqlite"))
        status = 0
    except BaseException as error:
        report["error"] = str(error)
        print(str(error), file=sys.stderr)
    finally:
        # No compiler/cache/venv is created; retain only compact evidence and DB.
        (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(dict(passed=report["passed"], rounds=len(report["rounds"]), evidence=str(output))))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
