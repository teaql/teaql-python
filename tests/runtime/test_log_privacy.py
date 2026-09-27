from dataclasses import replace
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from teaql.runtime.audit import AuditFieldChange, MutationAuditKind, RawAuditEvent
from teaql.runtime.context import UserContext, SqlLogEntry, SqlLogOperation, TextDiagnosticSqlLogSink
from teaql.runtime.log_privacy import PLAINTEXT_ENV, PLAINTEXT_ACK, REDACTED, sql_log_projection


@pytest.fixture(autouse=True)
def safe_environment(monkeypatch):
    monkeypatch.delenv(PLAINTEXT_ENV, raising=False)


def entry(field="name", value="PRIVATE-CUSTOMER-CANARY"):
    return SqlLogEntry(SqlLogOperation.Update, f"update {value}", "customer edit", None,
                       [f"edit {value}"], f"UPDATE customer SET {field} = ?", [value],
                       f"UPDATE customer SET {field} = '{value}'", "", datetime.now(),
                       datetime.now(), timedelta(microseconds=1), None, None, 1, "1 rows affected")


@pytest.mark.parametrize("setting", [None, "", "true", "1", PLAINTEXT_ACK + " ", PLAINTEXT_ACK.lower()])
def test_default_and_invalid_ack_protect_file_and_copy(monkeypatch, tmp_path, setting):
    if setting is not None:
        monkeypatch.setenv(PLAINTEXT_ENV, setting)
    raw = entry()
    with (tmp_path / "runtime.log").open("w") as output:
        TextDiagnosticSqlLogSink(lambda text: print(text, file=output)).write(raw)
    logged = (tmp_path / "runtime.log").read_text()
    assert raw.params[0] not in logged
    assert "1 rows affected" in logged
    assert "NOT REPLAYABLE" in logged
    assert raw.params == ["PRIVATE-CUSTOMER-CANARY"]
    assert "PRIVATE-CUSTOMER-CANARY" in raw.debug_sql


def test_context_sanitizes_before_custom_sink_and_buffer():
    raw = entry()
    captured = []
    context = UserContext.new()
    context.set_diagnostic_sql_log_sink(SimpleNamespace(write=captured.append))
    metadata = SimpleNamespace(operation="update", parameters=raw.params,
                               parameterized_sql=raw.sql, debug_query=raw.debug_sql,
                               comment=raw.comment, trace_chain=raw.trace_path, affected_rows=1)
    context.record_metadata_log(metadata)
    assert raw.params[0] not in repr(captured)
    assert raw.params[0] not in repr(context.sql_logs())
    assert metadata.parameters == raw.params


def test_exact_opt_in_warns_and_preserves_noncredential_debug(monkeypatch, caplog):
    from teaql.runtime.log_privacy import _warn_plaintext
    _warn_plaintext.cache_clear()
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    raw = entry()
    output = []
    TextDiagnosticSqlLogSink(output.append).write(raw)
    assert raw.params[0] in output[0]
    assert "may be written to disk" in caplog.text
    assert raw.params[0] not in caplog.text


@pytest.mark.parametrize("field", ["password", "accessToken", "private_key", "api_key", "refresh_token"])
def test_credentials_never_reach_sql_sink(monkeypatch, field):
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    raw = entry(field)
    assert raw.params[0] not in repr(sql_log_projection(raw))


@pytest.mark.parametrize("sql", ["SELECT 'UNIQUE-SECRET'", "SELECT 123456", "SELECT 1 -- UNIQUE-SECRET",
                                 "SELECT $$UNIQUE-SECRET$$", 'SELECT "UNIQUE-SECRET"'])
def test_unclassified_literal_sql_is_not_logged(sql):
    safe = sql_log_projection(replace(entry(), sql=sql, params=[], debug_sql=sql))
    assert safe.sql == "[REDACTED SQL; NOT REPLAYABLE]"
    assert safe.debug_sql == safe.sql


@pytest.mark.parametrize("enabled", [False, True])
def test_audit_field_policy_and_credential_override(monkeypatch, enabled):
    if enabled:
        monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    event = RawAuditEvent(MutationAuditKind.UPDATED, "Customer", 1, (
        AuditFieldChange("email", "old-private-email", "new-private-email"),
        AuditFieldChange("password", "old-password-secret", "new-password-secret"),
    ), ("change new-password-secret",))
    safe = event.safe(["email"], None)
    assert safe.fields[0].value == ("new-private-email" if enabled else REDACTED)
    assert safe.fields[1].value == REDACTED
    assert "new-password-secret" not in repr(safe)
    assert event.changes[1].new_value == "new-password-secret"


def test_nested_credentials_stay_masked(monkeypatch):
    monkeypatch.setenv(PLAINTEXT_ENV, PLAINTEXT_ACK)
    event = RawAuditEvent(MutationAuditKind.CREATED, "Account", 1,
                          (AuditFieldChange("settings", None, {"apiKey": "NESTED-SECRET"}),))
    assert "NESTED-SECRET" not in repr(event.safe([], None))
