"""Local generated-model E profile example; retains only compact evidence and databases."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback

EXAMPLE = Path(__file__).resolve().parent
REPO = EXAMPLE.parents[1]
PROFILES = ("camelCase", "snake_case", "PascalCase")
sha = lambda value: hashlib.sha256(value).hexdigest()


def source_hash():
    names = subprocess.check_output(["git", "-C", str(REPO), "ls-files", "-z", "--cached", "--others", "--exclude-standard"])
    digest = hashlib.sha256()
    for name in sorted(set(names.decode().split("\0")) - {""}):
        digest.update((name + "\0").encode())
        file = REPO / name
        if not file.exists():
            digest.update(b"deleted\0")
            continue
        digest.update((str(file.lstat().st_mode) + "\0").encode())
        digest.update(os.readlink(file).encode() if file.is_symlink() else file.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def fixture():
    root = EXAMPLE / "generated"
    manifest = json.loads((root / "manifest.json").read_text())
    provenance = json.loads((EXAMPLE / "provenance.json").read_text())
    assert manifest["language"] == "python" and manifest["localSourceOnly"] is True
    assert sha((root / "manifest.json").read_bytes()) == provenance["manifestSha256"]
    assert set(manifest["profiles"]) == set(PROFILES)
    for profile, value in manifest["profiles"].items():
        assert value["evaluation"]["errors"] == []
        assert sha((root / profile / "model.xml").read_bytes()) == value["modelSha256"]
        for name, expected in value["files"].items():
            file = root / profile / name
            assert file.resolve() == file and file.is_relative_to(root / profile)
            assert sha(file.read_bytes()) == expected
    return {"manifest": manifest, "provenance": provenance, "provenanceSha256": sha((EXAMPLE / "provenance.json").read_bytes())}


def main():
    requested = os.environ.get("TEAQL_GENERATED_E_PROFILE_EVIDENCE_DIR")
    output = Path(requested) if requested else Path(tempfile.mkdtemp(prefix="teaql-python-expression-evidence-"))
    if requested:
        assert output.is_absolute() and not output.exists()
        output.mkdir(parents=True)
    report = {"schema": "teaql.python-generated-e-model-profiles/v1", "passed": False,
              "localSourceOnly": True, "publicPublication": False, "installedArtifactAccepted": False,
              "completeExampleInventoryAccepted": False, "allP0P1Complete": False, "commands": [], "profiles": {}}
    try:
        report["sourceBefore"] = {"commit": subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"]).decode().strip(),
                                  "sourceContentsSha256": source_hash()}
        report["fixture"] = fixture()
        report["applicationSha256"] = sha((EXAMPLE / "main.py").read_bytes())
        report["controllerSha256"] = sha(Path(__file__).read_bytes())
        for profile in PROFILES:
            folder = output / profile
            folder.mkdir()
            rounds = []
            report["profiles"][profile] = {"rounds": rounds, "sameDatabase": True}
            environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                               PYTHONPATH=str(EXAMPLE / "generated" / profile) + os.pathsep + str(REPO / "src"),
                               TEAQL_EXPRESSION_PROFILE=profile, TEAQL_EXPRESSION_DB=str(folder / "fixture.sqlite"))
            for round_number in (1, 2):
                environment["TEAQL_EXPRESSION_ROUND"] = str(round_number)
                command = [sys.executable, "-B", str(EXAMPLE / "main.py")]
                log = folder / f"round-{round_number}.log"
                with log.open("x") as stream:
                    result = subprocess.run(command, cwd=REPO, env=environment, stdout=stream, stderr=subprocess.STDOUT, timeout=60, check=False)
                report["commands"].append({"profile": profile, "round": round_number, "command": command,
                                           "exitCode": result.returncode, "logSha256": sha(log.read_bytes())})
                assert result.returncode == 0, log.read_text()[-6000:]
                values = [json.loads(line.split("=", 1)[1]) for line in log.read_text().splitlines() if line.startswith("GENERATED_E_MODEL_PROFILE=")]
                assert len(values) == 1
                value = values[0]
                assert value["passed"] and value["profile"] == profile and value["round"] == round_number
                assert value["providerEntries"] == 0 and value["queryCalibration"] > 0
                assert Path(value["runtimeOrigin"]).is_relative_to(REPO / "src")
                rounds.append(value)
                assert fixture() == report["fixture"] and source_hash() == report["sourceBefore"]["sourceContentsSha256"]
            report["profiles"][profile]["databaseSha256"] = sha((folder / "fixture.sqlite").read_bytes())
        report["passed"] = True
    except Exception:
        report["error"] = traceback.format_exc()
        print(report["error"], file=sys.stderr)
    finally:
        report["sourceAfter"] = source_hash()
        report["cleanup"] = {"scratchRemoved": True, "disposedOwnedBytes": 0, "buildOrVenvCreated": False,
                             "sharedCachesDeleted": False, "databasesDeleted": False}
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"output": str(output), "passed": report["passed"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
