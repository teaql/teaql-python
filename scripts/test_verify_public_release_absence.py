#!/usr/bin/env python3
"""Exercise PyPI release-absence decisions without external network access."""

import importlib.util
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError, URLError


SCRIPT = Path(__file__).with_name("verify_public_release_absence.py")
SPEC = importlib.util.spec_from_file_location("teaql_pypi_absence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
IDENTITIES = (("teaql", "9.8.7"), ("teaql-blob-reference", "9.8.7"),
              ("teaql-secure-document-reference", "9.8.7"))


class Response(BytesIO):
    def __init__(self, status, body=b""):
        super().__init__(body)
        self.status = status


class PyPIAbsenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="teaql-pypi-absence-")
        self.dist = Path(self.temporary.name)
        for name, version in IDENTITIES:
            (self.dist / f"{name.replace('-', '_')}-{version}-py3-none-any.whl").write_bytes(b"wheel")
            (self.dist / f"{name}-{version}.tar.gz").write_bytes(b"sdist")

    def tearDown(self):
        self.temporary.cleanup()

    def mock_opener(self, statuses, observed):
        def open_request(request, timeout):
            self.assertEqual(timeout, 15)
            observed.append(request.full_url)
            status = statuses.get(request.full_url, 404)
            if isinstance(status, Exception):
                raise status
            if status >= 400:
                raise HTTPError(request.full_url, status, "mock", None, None)
            return Response(status)
        return open_request

    def release_payload(self, name, version):
        files = [path for path in self.dist.iterdir()
                 if path.name.startswith(name.replace("-", "_") + f"-{version}-")
                 or path.name in (f"{name}-{version}.tar.gz",
                                  f"{name.replace('-', '_')}-{version}.tar.gz")]
        return {"info": {"name": name, "version": version},
                "urls": [{"filename": path.name,
                          "digests": {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}
                         for path in files]}

    def published_opener(self, observed, replacements=None):
        replacements = replacements or {}
        def open_request(request, timeout):
            self.assertEqual(timeout, 15)
            observed.append(request.full_url)
            parts = request.full_url.removeprefix("https://pypi.org/pypi/").split("/")
            name, version = parts[0], parts[1]
            value = replacements.get(request.full_url)
            if isinstance(value, list):
                value = value[min(observed.count(request.full_url) - 1, len(value) - 1)]
            if isinstance(value, Exception):
                raise value
            if value is None:
                value = self.release_payload(name, version)
            return Response(200, json.dumps(value).encode())
        return open_request

    def test_all_three_absent(self):
        MODULE.require_exact_distribution_names(self.dist, IDENTITIES)
        observed = []
        MODULE.require_absent(IDENTITIES, self.mock_opener({}, observed))
        self.assertEqual(observed, [f"https://pypi.org/pypi/{name}/{version}/json"
                                    for name, version in IDENTITIES])

    def test_occupied_non_base_project_blocks_publication(self):
        observed = []
        url = "https://pypi.org/pypi/teaql-blob-reference/9.8.7/json"
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            MODULE.require_absent(IDENTITIES, self.mock_opener({url: 200}, observed))
        self.assertEqual(observed[-1], url)
        self.assertEqual(len(observed), 2)

    def test_registry_failure_fails_closed(self):
        url = "https://pypi.org/pypi/teaql/9.8.7/json"
        with self.assertRaisesRegex(RuntimeError, "Could not prove"):
            MODULE.require_absent(IDENTITIES, self.mock_opener({url: 503}, []))

    def test_network_failure_fails_closed(self):
        url = "https://pypi.org/pypi/teaql/9.8.7/json"
        with self.assertRaisesRegex(RuntimeError, "Could not prove"):
            MODULE.require_absent(IDENTITIES, self.mock_opener({url: URLError("offline")}, []))

    def test_unexpected_success_status_fails_closed(self):
        url = "https://pypi.org/pypi/teaql/9.8.7/json"
        with self.assertRaisesRegex(RuntimeError, "HTTP 204"):
            MODULE.require_absent(IDENTITIES, self.mock_opener({url: 204}, []))

    def test_exact_six_distributions_required(self):
        (self.dist / "teaql-blob-reference-9.8.7.tar.gz").unlink()
        with self.assertRaisesRegex(ValueError, "exactly three wheels"):
            MODULE.require_exact_distribution_names(self.dist, IDENTITIES)

    def test_current_source_identifies_three_matching_projects(self):
        identities = MODULE.release_identities()
        self.assertEqual([name for name, _ in identities],
                         [name for name, _ in IDENTITIES])
        self.assertEqual(len({version for _, version in identities}), 1)

    def test_exact_three_published_release_file_sets(self):
        observed = []
        MODULE.require_published_exact(self.dist, IDENTITIES,
                                       self.published_opener(observed), lambda _: None)
        self.assertEqual(len(observed), 3)

    def test_eventually_visible_release_files(self):
        observed = []
        name, version = IDENTITIES[0]
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        partial = self.release_payload(name, version)
        partial["urls"] = partial["urls"][:1]
        MODULE.require_published_exact(self.dist, IDENTITIES,
            self.published_opener(observed, {url: [partial, self.release_payload(name, version)]}),
            lambda _: None)
        self.assertEqual(observed.count(url), 2)

    def test_published_digest_mismatch_rejected(self):
        observed = []
        name, version = IDENTITIES[0]
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        wrong = self.release_payload(name, version)
        wrong["urls"][0]["digests"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "digest mismatch"):
            MODULE.require_published_exact(self.dist, IDENTITIES,
                                           self.published_opener(observed, {url: wrong}), lambda _: None)

    def test_unexpected_published_file_rejected(self):
        observed = []
        name, version = IDENTITIES[0]
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        extra = self.release_payload(name, version)
        extra["urls"].append({"filename": "unrecognized.whl", "digests": {"sha256": "0" * 64}})
        with self.assertRaisesRegex(RuntimeError, "Unexpected extra"):
            MODULE.require_published_exact(self.dist, IDENTITIES,
                                           self.published_opener(observed, {url: extra}), lambda _: None)

    def test_duplicate_published_filename_rejected(self):
        observed = []
        name, version = IDENTITIES[0]
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        duplicate = self.release_payload(name, version)
        duplicate["urls"].append(dict(duplicate["urls"][0]))
        with self.assertRaisesRegex(RuntimeError, "Duplicate"):
            MODULE.require_published_exact(self.dist, IDENTITIES,
                                           self.published_opener(observed, {url: duplicate}), lambda _: None)

    def test_published_release_never_appears_fails_closed(self):
        observed = []
        name, version = IDENTITIES[0]
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        absent = HTTPError(url, 404, "mock", None, None)
        with self.assertRaisesRegex(RuntimeError, "incomplete after retries"):
            MODULE.require_published_exact(self.dist, IDENTITIES,
                                           self.published_opener(observed, {url: absent}), lambda _: None)
        self.assertEqual(observed.count(url), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
