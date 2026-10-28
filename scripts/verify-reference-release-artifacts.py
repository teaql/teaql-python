#!/usr/bin/env python3
"""Check the exact three-module wheel/sdist set before artifact upload."""

from email.parser import Parser
from pathlib import Path
import sys
import tarfile
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
if len(sys.argv) != 2 or not Path(sys.argv[1]).is_dir():
    raise SystemExit("Usage: verify-reference-release-artifacts.py <distribution-directory>")
DIST = Path(sys.argv[1]).resolve()

try:
    import tomllib
except ImportError:  # Local Python 3.10; release CI uses Python 3.12.
    import tomli as tomllib

projects = {
    "teaql": (ROOT, "teaql"),
    "teaql-blob-reference": (ROOT / "packages/teaql-blob-reference", "teaql_blob_reference"),
    "teaql-secure-document-reference": (
        ROOT / "packages/teaql-secure-document-reference", "teaql_secure_document_reference"
    ),
}
versions = {}
for name, (source, _) in projects.items():
    metadata = tomllib.loads((source / "pyproject.toml").read_text())['project']
    if metadata['name'] != name:
        raise SystemExit(f"Unexpected project name in {source}")
    versions[name] = metadata['version']
if len(set(versions.values())) != 1:
    raise SystemExit("Reference module versions differ from the base package")

artifacts = sorted(DIST.iterdir())
wheels = [p for p in artifacts if p.name.endswith(".whl")]
sdists = [p for p in artifacts if p.name.endswith(".tar.gz")]
if len(artifacts) != 6 or len(wheels) != 3 or len(sdists) != 3:
    raise SystemExit("Expected exactly three wheels and three source distributions")


def identity(raw: bytes) -> tuple[str, str]:
    data = Parser().parsestr(raw.decode("utf-8"))
    return data.get("Name", ""), data.get("Version", "")


def source_files(source: Path, package: str) -> dict[str, bytes]:
    root = source / "src" / package
    return {
        str(path.relative_to(source / "src")): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


seen_wheels = set()
for wheel in wheels:
    with ZipFile(wheel) as archive:
        metadata_files = [entry for entry in archive.namelist()
                          if entry.endswith(".dist-info/METADATA")]
        if len(metadata_files) != 1:
            raise SystemExit(f"Unexpected wheel metadata in {wheel.name}")
        name, version = identity(archive.read(metadata_files[0]))
        if name not in projects or version != versions[name] or name in seen_wheels:
            raise SystemExit(f"Unexpected wheel identity in {wheel.name}: {name} {version}")
        expected_name = name.replace("-", "_") + f"-{version}-py3-none-any.whl"
        if wheel.name != expected_name:
            raise SystemExit(f"Unexpected wheel filename: {wheel.name}")
        source, package = projects[name]
        entries = set(archive.namelist())
        for other in {item[1] for item in projects.values()} - {package}:
            if any(entry.startswith(other + "/") for entry in entries):
                raise SystemExit(f"Other module leaked into {wheel.name}: {other}")
        files = source_files(source, package)
        if not files or any(path not in entries or archive.read(path) != data
                            for path, data in files.items()):
            raise SystemExit(f"Source bytes missing or changed in {wheel.name}")
        seen_wheels.add(name)
        print(f"PASS exact {name} {version} wheel, {len(files)} source files")

seen_sdists = set()
for sdist in sdists:
    with tarfile.open(sdist, "r:gz") as archive:
        entries = {entry.name: entry for entry in archive.getmembers() if entry.isfile()}
        metadata_files = [path for path in entries if path.endswith("/PKG-INFO")
                          and path.count("/") == 1]
        if len(metadata_files) != 1:
            raise SystemExit(f"Unexpected sdist metadata in {sdist.name}")
        extracted = archive.extractfile(entries[metadata_files[0]])
        if extracted is None:
            raise SystemExit(f"Missing sdist metadata bytes in {sdist.name}")
        name, version = identity(extracted.read())
        if name not in projects or version != versions[name] or name in seen_sdists:
            raise SystemExit(f"Unexpected sdist identity in {sdist.name}: {name} {version}")
        source, package = projects[name]
        root = metadata_files[0].split("/", 1)[0]
        if sdist.name not in (f"{name}-{version}.tar.gz",
                              f"{name.replace('-', '_')}-{version}.tar.gz"):
            raise SystemExit(f"Unexpected sdist filename: {sdist.name}")
        for other in {item[1] for item in projects.values()} - {package}:
            if any(path.startswith(f"{root}/src/{other}/") for path in entries):
                raise SystemExit(f"Other module leaked into {sdist.name}: {other}")
        files = source_files(source, package)
        for path, data in files.items():
            member = entries.get(f"{root}/src/{path}")
            content = None if member is None else archive.extractfile(member)
            if content is None or content.read() != data:
                raise SystemExit(f"Source bytes missing or changed in {sdist.name}: {path}")
        seen_sdists.add(name)
        print(f"PASS exact {name} {version} sdist, {len(files)} source files")

if seen_wheels != set(projects) or seen_sdists != set(projects):
    raise SystemExit("Missing reference module distribution")
print("PASS exact three-package Python release set: 3 wheels and 3 sdists")
