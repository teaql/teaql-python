#!/usr/bin/env python3
"""Fail closed if any exact TeaQL Python release version is already on PyPI."""

from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import tomllib
except ImportError:  # Local Python 3.10; release CI uses Python 3.12.
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = (
    ROOT / "pyproject.toml",
    ROOT / "packages/teaql-blob-reference/pyproject.toml",
    ROOT / "packages/teaql-secure-document-reference/pyproject.toml",
)


def release_identities(project_files=PROJECTS):
    identities = []
    for project_file in project_files:
        project = tomllib.loads(project_file.read_text())["project"]
        name, version = project["name"], project["version"]
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version)):
            raise ValueError(f"Invalid release identity in {project_file}")
        identities.append((name, version))
    if len({name for name, _ in identities}) != 3 or len({version for _, version in identities}) != 1:
        raise ValueError("Expected three distinct TeaQL projects with one release version")
    return identities


def require_exact_distribution_names(dist, identities):
    if not dist.is_dir():
        raise ValueError(f"Missing distribution directory: {dist}")
    names = [path.name for path in dist.iterdir()
             if path.is_file() and not path.is_symlink()]
    if len(names) != 6 or len(list(dist.iterdir())) != 6:
        raise ValueError("Expected exactly three wheels and three source distributions")
    for name, version in identities:
        wheel = name.replace("-", "_") + f"-{version}-py3-none-any.whl"
        sdist = {f"{name}-{version}.tar.gz", f"{name.replace('-', '_')}-{version}.tar.gz"}
        if names.count(wheel) != 1 or sum(names.count(item) for item in sdist) != 1:
            raise ValueError(f"Missing exact distribution filenames for {name} {version}")


def require_absent(identities, opener=urlopen):
    for name, version in identities:
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        request = Request(url, headers={"Accept": "application/json",
                                        "User-Agent": "teaql-release-preflight/1"})
        try:
            with opener(request, timeout=15) as response:
                status = response.status
        except HTTPError as exc:
            if exc.code == 404:
                exc.close()
                continue
            raise RuntimeError(f"Could not prove {name} {version} absent on PyPI: HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"Could not prove {name} {version} absent on PyPI") from exc
        if status == 200:
            raise RuntimeError(f"PyPI version already exists: {name} {version}")
        raise RuntimeError(f"Could not prove {name} {version} absent on PyPI: HTTP {status}")


def main(argv):
    if len(argv) != 2:
        raise SystemExit("Usage: verify_public_release_absence.py <distribution-directory>")
    identities = release_identities()
    require_exact_distribution_names(Path(argv[1]), identities)
    require_absent(identities)
    print("PASS all three TeaQL Python release versions are absent on PyPI")


if __name__ == "__main__":
    try:
        main(sys.argv)
    except (OSError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
