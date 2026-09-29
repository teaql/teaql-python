"""Behavior contracts: never replace expected output just to match a new implementation."""
from datetime import datetime, timedelta
from dataclasses import replace
from pathlib import Path
import pytest
from teaql.runtime.audit import _mask
from teaql.runtime.context import SqlLogEntry, SqlLogOperation, TextDiagnosticSqlLogSink
from teaql.runtime.log_privacy import PLAINTEXT_ENV, PLAINTEXT_ACK

CASES = [("", ""), ("Ada", "***"), ("12345678", "********"),
         ("ABCDEFGH", "AB****GH"), ("Riverside", "Ri*****de"), ("O'Reilly", "O'****ly")]

GOLDEN = [line.split("\t") for line in
          (Path(__file__).parents[2] / "test-vectors/masking-v1.tsv").read_text().splitlines()[1:]]

@pytest.mark.parametrize("case,raw,expected", GOLDEN)
def test_mask_golden(case, raw, expected, monkeypatch):
    from teaql.runtime.audit import AuditFieldChange, MutationAuditKind, RawAuditEvent
    monkeypatch.delenv(PLAINTEXT_ENV, raising=False)
    assert _mask(raw) == expected, case
    event = RawAuditEvent(MutationAuditKind.UPDATED, "Customer", 1,
                          (AuditFieldChange("name", None, raw),))
    safe = event.safe(["name"], None)
    assert safe.fields[0].masked
    assert safe.fields[0].value == expected, case
    assert event.changes[0].new_value == raw

def entry(value):
    sql = "UPDATE customer SET name = '" + value.replace("'", "''") + "'"
    return SqlLogEntry(SqlLogOperation.Update, "what: edit customer", "why: verify mask contract",
                       None, [], "UPDATE customer SET name = ?", [value], sql, sql,
                       datetime.now(), datetime.now(), timedelta(microseconds=1), None, None, 1, "1 row affected")

@pytest.mark.parametrize("raw,masked", CASES)
def test_mask_contract_legacy_algorithm(raw, masked):
    assert _mask(raw) == masked

@pytest.mark.parametrize("raw,masked", CASES)
def test_mask_contract_expanded_sql(monkeypatch, raw, masked):
    monkeypatch.delenv(PLAINTEXT_ENV, raising=False)
    source = entry(raw)
    output = []
    TextDiagnosticSqlLogSink(output.append).write(source)
    log = "\n".join(output)
    assert source.params == [raw]
    # Unknown parameter provenance must not expose a prefix/suffix.
    assert "name = '" in log
    if len(raw) >= 8 and not masked.startswith("*"):
        assert masked.replace("'", "''") not in log
    assert "masked" in log.lower()
    assert "name = ?" not in log
    assert "[REDACTED SQL" not in log
    if raw:
        assert "'" + raw.replace("'", "''") + "'" not in log

def test_mask_contract_debug_provenance(monkeypatch):
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    output = []
    sink = TextDiagnosticSqlLogSink(output.append)
    sink.write(replace(entry("Riverside"), parameter_log_policies=['masked']))
    sink.write(replace(entry("Riverside"), parameter_log_policies=['masked']))
    assert len(output) == 2
    for log in output:
        assert "'Riverside'" in log
        assert "DEBUG" in log.upper()
        assert "PLAINTEXT" in log.upper()
