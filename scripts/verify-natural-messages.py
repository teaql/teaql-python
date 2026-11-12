"""Local source gate with owned subprocess/scratch cleanup and compact evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
# These three links are already versioned at the source baseline. They are
# fingerprinted as link text, never followed or used to execute the gate.
LEGACY_SOURCE_LINKS = {"venv/bin/python": "python3", "venv/bin/python3": "/usr/bin/python3", "venv/lib64": "lib"}


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def source():
    files = sorted(set(filter(None, subprocess.check_output([
        "git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=REPO).decode().split("\0"))))
    result = {}
    for name in files:
        file = REPO / name
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        if file.is_symlink():
            target = os.readlink(file)
            assert LEGACY_SOURCE_LINKS.get(name) == target, "unapproved source symlink: " + name
            assert subprocess.check_output(["git", "show", "HEAD:" + name], cwd=REPO) == os.fsencode(target)
            result[name] = hashlib.sha256(os.fsencode(target)).hexdigest()
        else:
            assert file.is_file() and file.resolve() == file, "source path escaped or disappeared: " + name
            result[name] = sha(file)
    return result


class OwnedRunner:
    def __init__(self):
        self.safe_to_clean = True

    @staticmethod
    def _alive(pid):
        try:
            os.killpg(pid, 0)
            return True
        except ProcessLookupError:
            return False

    def run(self, command, *, log, cwd, env, timeout=300):
        with Path(log).open("x") as output:
            process = subprocess.Popen(command, cwd=cwd, env=env, stdout=output,
                stderr=subprocess.STDOUT, start_new_session=True)
            try:
                try:
                    return process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    return 124
            finally:
                # Only the process group created by this invocation is a target.
                if self._alive(process.pid):
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    for _ in range(20):
                        if not self._alive(process.pid):
                            break
                        time.sleep(.025)
                    if self._alive(process.pid):
                        os.killpg(process.pid, signal.SIGKILL)
                        for _ in range(20):
                            if not self._alive(process.pid):
                                break
                            time.sleep(.025)
                    self.safe_to_clean = not self._alive(process.pid)
                else:
                    process.wait()


def junit(file):
    root = ET.parse(file).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    return {key: sum(int(s.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}


def generated():
    fixture = REPO / "examples/natural-messages/fixture"
    manifest = fixture / "generated-files.json"
    files = json.loads(manifest.read_text())
    for name, digest in files.items():
        file = fixture / name
        assert not Path(name).is_absolute() and ".." not in Path(name).parts and file.is_file() and not file.is_symlink()
        assert sha(file) == digest, name
    return dict(files=files, manifestSha256=sha(manifest), modelSha256=sha(fixture / "model.xml"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--example", action="store_true")
    parser.add_argument("--example-only", action="store_true")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    assert not output.exists(), "never overwrite retained evidence"
    output.mkdir(parents=True)
    scratch = Path(tempfile.mkdtemp(prefix="teaql-python-natural-build-"))
    runner = OwnedRunner()
    report = dict(scope="local-source", passed=False, commands=[], publicPublication=False, scratch=str(scratch))
    old_term = signal.getsignal(signal.SIGTERM)
    def interrupted(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, interrupted)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=os.pathsep.join((str(REPO / "src"), str(REPO / "examples/natural-messages/fixture"))),
        TEAQL_TELEMETRY_ENABLED="false", TMPDIR=str(scratch))
    for name in list(env):
        if any(token in name for token in ("TOKEN", "PASSWORD", "SECRET", "AUTH", "API_KEY")):
            del env[name]
    def run(name, command, timeout=300, extra=None):
        log = output / (name + ".log")
        code = runner.run(command, log=log, cwd=REPO, env={**env, **(extra or {})}, timeout=timeout)
        report["commands"].append(dict(name=name, command=command, exitCode=code, log=log.name, logSha256=sha(log)))
        assert code == 0, f"{name} failed; see {log}"
        return log.read_text()
    try:
        assert shutil.disk_usage(scratch).free > 1024**3
        report["sourceCommit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
        report["sourceHashes"] = source()
        report["legacySourceSymlinks"] = LEGACY_SOURCE_LINKS
        report["python"] = sys.version
        if args.full:
            # The repository's complete native suite imports the optional S3 SDK
            # at collection time. Install its pinned SDK edges into owned scratch,
            # not the user's interpreter or a committed virtual environment.
            dependencies = scratch / "dependencies"
            run("dependencies", [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                "--no-deps", "--target", str(dependencies), "boto3==1.43.113", "botocore==1.43.127", "s3transfer==0.19.3", "jmespath==1.1.0"], timeout=300)
            env["PYTHONPATH"] += os.pathsep + str(dependencies)
            run("dependency-origins", [sys.executable, "-c", "import boto3,botocore,s3transfer,jmespath,json; print(json.dumps({m.__name__:{'version':getattr(m,'__version__',None),'file':m.__file__} for m in (boto3,botocore,s3transfer,jmespath)}))"])
        if not args.example_only:
            run("focused", [sys.executable, "-m", "pytest", "tests/runtime/test_natural_messages.py", "tests/runtime/test_natural_message_runner.py",
                "-q", "-s", "-p", "no:cacheprovider", "--basetemp=" + str(scratch / "focus"), "--junitxml=" + str(output / "focused.xml")])
            report["focused"] = junit(output / "focused.xml")
            if args.full:
                run("native", [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider",
                    "--basetemp=" + str(scratch / "native"), "--junitxml=" + str(output / "native.xml")], timeout=600)
                report["native"] = junit(output / "native.xml")
        if args.example or args.example_only:
            report["fixture"] = generated()
            report["rounds"] = []
            for round_number in (1, 2):
                log = run("example-" + str(round_number), [sys.executable, str(REPO / "examples/natural-messages/verify.py")],
                    extra={"TEAQL_NATURAL_MESSAGES_DB": str(output / "example.sqlite")})
                responses = [json.loads(line.partition("=")[2]) for line in log.splitlines() if line.startswith("PY_NATURAL_RESPONSE=")]
                frames = [json.loads(line.partition("=")[2]) for line in log.splitlines() if line.startswith("PY_NATURAL_SQLITE_PASS=")]
                assert len(responses) == 4 and len(frames) == 1 and frames[0]["passed"]
                assert frames[0]["automaticMetadata"] and frames[0]["originalGeneratedChecker"]
                assert frames[0]["unchangedParent"] and frames[0]["customerRendererCalls"] == 1
                (output / f"responses-{round_number}.json").write_text(json.dumps(responses, ensure_ascii=False, indent=2) + "\n")
                report["rounds"].append(dict(round=round_number, **frames[0]))
                assert generated() == report["fixture"] and source() == report["sourceHashes"]
            database = output / "example.sqlite"
            with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
                rows = db.execute("SELECT name,version FROM entry_data ORDER BY id").fetchall()
            assert rows == [("first", 1), ("renamed", 2), ("first", 1), ("renamed", 2)]
            report.update(sameDatabase=True, databaseSha256=sha(database), sqliteRows=rows)
        assert source() == report["sourceHashes"], "candidate changed during verification"
        report["passed"] = True
    except Exception as error:
        report["error"] = str(error)
        print(str(error), file=sys.stderr)
    finally:
        report["removedScratchBytes"] = sum(file.stat().st_size for file in scratch.rglob("*") if file.is_file()) if runner.safe_to_clean else 0
        if runner.safe_to_clean:
            shutil.rmtree(scratch)
        else:
            report["unsafeBuildRetention"] = str(scratch)
        report["scratchRemoved"] = not scratch.exists()
        signal.signal(signal.SIGTERM, old_term)
        report["retainedFileHashes"] = {file.name: sha(file) for file in output.iterdir() if file.is_file()}
        (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({key: report.get(key) for key in ("passed", "focused", "native", "scratchRemoved", "removedScratchBytes")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
