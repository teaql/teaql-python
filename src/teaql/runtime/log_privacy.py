"""Log-only projections. Never modify execution parameters or stored values."""

import logging
import os
import re
from dataclasses import fields, is_dataclass, replace
from functools import lru_cache

PLAINTEXT_ENV = "TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS"
PLAINTEXT_ACK = "I_UNDERSTAND_SENSITIVE_DATA_MAY_BE_WRITTEN_TO_DISK"
REDACTED = "[REDACTED]"
SQL_REDACTED = "[REDACTED SQL; NOT REPLAYABLE]"


@lru_cache(maxsize=1)
def _warn_plaintext():
    logging.getLogger("teaql.runtime").warning(
        "Sensitive plaintext logging enabled: application data may be written to disk. "
        "Authentication secrets remain redacted."
    )


def plaintext_enabled():
    enabled = os.environ.get(PLAINTEXT_ENV) == PLAINTEXT_ACK
    if enabled:
        _warn_plaintext()
    return enabled


def credential_name(name):
    normalized = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return any(word in normalized for word in (
        "password", "passwd", "passphrase", "privatekey", "secret", "accesstoken",
        "refreshtoken", "idtoken", "apikey", "authorization", "credential",
        "sessiontoken", "magiclinktoken",
    ))


def payload_has_credentials(value):
    value = getattr(value, "val", value)
    if isinstance(value, dict):
        return any(credential_name(k) or payload_has_credentials(v) for k, v in value.items())
    if isinstance(value, (tuple, list)):
        return any(payload_has_credentials(v) for v in value)
    return False


def value_strings(value):
    value = getattr(value, "val", value)
    if isinstance(value, dict):
        return [s for v in value.values() for s in value_strings(v)]
    if isinstance(value, (tuple, list)):
        return [s for v in value for s in value_strings(v)]
    return [] if value is None or value == "" else [str(value)]


def scrub(value, secrets):
    """Copy annotations, removing known values even when embedded in intent."""
    if isinstance(value, str):
        for secret in sorted(set(secrets), key=len, reverse=True):
            value = value.replace(secret, REDACTED)
        return value
    if isinstance(value, list):
        return [scrub(v, secrets) for v in value]
    if isinstance(value, tuple):
        return tuple(scrub(v, secrets) for v in value)
    if isinstance(value, dict):
        return {k: scrub(v, secrets) for k, v in value.items()}
    if is_dataclass(value):
        return replace(value, **{f.name: scrub(getattr(value, f.name), secrets)
                                 for f in fields(value) if f.init})
    return value


def sql_log_projection(entry):
    # SQL has no per-parameter field provenance. A credential-bearing query
    # therefore suppresses its whole payload, including on debug opt-in.
    credentials = (credential_name(entry.sql) or credential_name(entry.debug_sql)
                   or payload_has_credentials(entry.params))
    allow = plaintext_enabled() and not credentials
    if allow:
        return replace(entry, params=list(entry.params), trace_path=list(entry.trace_path))
    secrets = value_strings(entry.params)
    sql = entry.sql
    # Arbitrary literal SQL is not safely redactable across dialects. Preserve
    # parameterized shape only when there are no literals/comments to expose.
    if any(token in sql for token in ("'", '"', "`", "--", "/*", "$")) or re.search(r"\b\d+\b", sql):
        sql = SQL_REDACTED
    return replace(entry, sql=scrub(sql, secrets), params=[None] * len(entry.params),
                   debug_sql=SQL_REDACTED, pretty_sql=SQL_REDACTED,
                   comment=scrub(entry.comment, secrets), purpose=scrub(entry.purpose, secrets),
                   audit_reason=scrub(entry.audit_reason, secrets),
                   trace_path=scrub(entry.trace_path, secrets))
