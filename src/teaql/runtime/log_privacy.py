"""Log-only projections. Never modify execution parameters or stored values."""

import logging
import os
import re
import weakref
from copy import deepcopy
from dataclasses import fields, is_dataclass, replace
from functools import lru_cache

PLAINTEXT_ENV = "TEAQL_ALLOW_SENSITIVE_PLAINTEXT_LOGS"
PLAINTEXT_ACK = "I_UNDERSTAND_SENSITIVE_DATA_MAY_BE_WRITTEN_TO_DISK"
REDACTED = "[REDACTED]"
SQL_REDACTED = "[REDACTED SQL; NOT REPLAYABLE]"
DEBUG_LABEL = "-- TeaQL DEBUG PLAINTEXT; EXPLICIT OPT-IN\n"


def label_debug_sql(sql):
    return sql if not sql or sql.startswith(DEBUG_LABEL) else DEBUG_LABEL + sql


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


def scrub(value, secrets, hide_all=False):
    """Copy annotations, removing known values even when embedded in intent."""
    if isinstance(value, str):
        if hide_all:
            return REDACTED if value else value
        for secret in sorted(set(secrets), key=len, reverse=True):
            value = value.replace(secret, REDACTED)
        return value
    if isinstance(value, list):
        return [scrub(v, secrets, hide_all) for v in value]
    if isinstance(value, tuple):
        return tuple(scrub(v, secrets, hide_all) for v in value)
    if isinstance(value, dict):
        return {k: scrub(v, secrets, hide_all) for k, v in value.items()}
    if is_dataclass(value):
        return replace(value, **{f.name: scrub(getattr(value, f.name), secrets, hide_all)
                                 for f in fields(value) if f.init})
    return value


_projections = {}

def _remember_projection(projected, allow, alternative=None):
    key = id(projected)
    _projections[key] = (weakref.ref(projected, lambda _: _projections.pop(key, None)),
                         allow, deepcopy(projected), alternative)
    return projected

def _business_mask(value):
    from .audit import _mask
    value = getattr(value, 'val', value)
    if value is None:
        return None
    if isinstance(value, (tuple, list)):
        return [_business_mask(child) for child in value]
    if isinstance(value, dict):
        return REDACTED
    return _mask(str(value))

def _binding_policies(source):
    supplied = source.parameter_log_policies
    valid = supplied is not None and len(supplied) == len(source.params)
    credentials = credential_name(source.sql) and (source.sql_origin != 'generated' or not valid)
    policies = []
    for index, value in enumerate(source.params):
        policy = supplied[index] if valid else 'unknown'
        if credentials or payload_has_credentials(value):
            policy = 'credential'
        policies.append(policy if policy in ('plain', 'masked', 'credential') else 'unknown')
    return policies


def _is_masked(policy, allow):
    return policy in ('credential', 'unknown') or (not allow and policy != 'plain')


def sql_log_projection(entry, *, _intent_source=None, _intent_values=()):
    """Source bindings are call-local runtime plumbing, never stored on a log entry."""
    allow = plaintext_enabled() and entry.log_mode != 'masked'
    prior = _projections.get(id(entry))
    # Log entries are mutable: reuse only an unchanged projection. Weak references
    # keep this idempotence bookkeeping from retaining a long-running log history.
    if prior and prior[0]() is entry and prior[2] == entry:
        if not prior[1] or allow:
            return entry
        # Entries are mutable. Do not expose the cached safe alternative itself.
        if prior[3] is not None:
            return _remember_projection(deepcopy(prior[3]), False)
    projected = _project_with_policy(entry, allow, _intent_source, _intent_values)
    alternative = _project_with_policy(entry, False, _intent_source, _intent_values) if allow else None
    return _remember_projection(projected, allow, alternative)


def _project_with_policy(entry, allow, intent_source, intent_values):
    from teaql.sql.types import DatabaseKind, render_log_sql, _sql_literal
    from teaql.core.value import Value
    supplied = entry.parameter_log_policies
    valid = supplied is None or len(supplied) == len(entry.params)
    # Compiler-owned bindings already identify individual credential fields. A
    # credential column elsewhere in the projection must not hide ordinary binds.
    # Unclassified/custom statements retain the conservative whole-SQL fallback.
    credentials = credential_name(entry.sql) and (
        entry.sql_origin != 'generated' or supplied is None or not valid)
    policies = _binding_policies(entry)
    masked = [_is_masked(policy, allow) for policy in policies]
    safe_values = [(_business_mask(value) if policies[index] == 'masked' else REDACTED)
                   if masked[index] else deepcopy(value) for index, value in enumerate(entry.params)]
    secrets = [text for index, value in enumerate(entry.params) if masked[index]
               for text in value_strings(value)]
    if intent_source is not None:
        source_policies = _binding_policies(intent_source)
        secrets.extend(text for index, value in enumerate(intent_source.params)
                       if _is_masked(source_policies[index], allow) for text in value_strings(value))
    intent_secrets = secrets + [text for value in intent_values for text in value_strings(value)]
    # A copied/changed debug record has lost its reliable private alternative.
    # Its inherited intent may mention values absent from its own SQL bindings.
    unknown_debug_intent = not allow and entry.log_mode == 'debug-plaintext' and intent_source is None
    def intent(value):
        return scrub(value, intent_secrets, hide_all=unknown_debug_intent)
    bare = re.sub(r'\$[0-9]+', '?', entry.sql)
    unsafe = ((not allow or credentials) and entry.sql_origin != 'generated' and
              bool(re.search(r"['\"`$]|--|/\*|\b\d+\b|:[A-Za-z_]", bare)))
    reason = 'untrusted-literal-sql' if unsafe else 'policy-count-mismatch' if not valid else None
    rendered = SQL_REDACTED
    kind = entry.database_kind or (DatabaseKind.PostgreSql if re.search(r'\$[0-9]+', entry.sql)
                                  else DatabaseKind.MySql if '%s' in entry.sql else DatabaseKind.Sqlite)
    if reason is None:
        try:
            def literal(index):
                value = safe_values[index]
                value = value if isinstance(value, Value) else Value.from_any(value)
                return _sql_literal(value, kind) + (' /* masked */' if masked[index] else '')
            rendered = render_log_sql(entry.sql, safe_values, kind, literal)
            prefix = (('-- TeaQL DEBUG PLAINTEXT; EXPLICIT OPT-IN; PARTIALLY MASKED; NOT REPLAYABLE\n'
                       if any(masked) else DEBUG_LABEL) if allow else '-- TeaQL MASKED; NOT REPLAYABLE\n')
            rendered = prefix + rendered
        except Exception:
            # Renderer failures must not echo source SQL, values, or exception text.
            rendered = SQL_REDACTED
            reason = 'unsupported-or-mismatched-bindings'
    projected = replace(entry, sql=SQL_REDACTED if unsafe else entry.sql
                        if entry.sql_origin == 'generated' else scrub(entry.sql, secrets),
                        params=safe_values, parameter_log_policies=policies, masked_parameters=masked,
                        debug_sql=rendered, pretty_sql=rendered, omission_reason=reason,
                        log_mode='debug-plaintext' if allow else 'masked',
                        comment=intent(entry.comment), purpose=intent(entry.purpose),
                        audit_reason=intent(entry.audit_reason),
                        result_summary=(f'{entry.result_count} rows returned' if entry.result_count is not None
                            else f'{entry.affected_rows} rows affected' if entry.affected_rows is not None
                            else scrub(entry.result_summary, secrets, hide_all=unknown_debug_intent)),
                        trace_path=intent(entry.trace_path))
    return projected
