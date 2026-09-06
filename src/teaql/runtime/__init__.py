from .context import (
    ContextEntityRef, ContextRootError, DiagnosticSqlLogSink, UserContext,
    TeaqlRuntime, SqlLogEntry, SqlLogOperation, TextDiagnosticSqlLogSink,
)
from .tools import (
    ContextTools, ExecutableHttpTool, HTTP_TOOL, HttpIntentPhase, HttpTool,
    HttpToolProvider, ToolDeniedError, ToolError, ToolPolicy, ToolRisk,
    Tools, ToolToken, ToolUnavailableError,
)
from .module import RuntimeModule, DefaultEntityDataServiceBehavior
from .store import DataStore
from .audit import RawAuditEvent, SafeAuditEvent, MutationAuditKind
from .i18n import CheckException, CheckResult, I18nCatalog, JsonFieldNamingProfile, Locale, ObjectLocation, UnsupportedLocaleError
from .wire_fields import NormalizedWireInput, WireEntityMetadata, WireFieldMetadata, WireInputError, create_wire_entity_metadata, encode_wire_output, normalize_wire_input, retain_submitted_paths
from teaql.core.entity import EntityKey, EntityChangeSet, EntityRoot

__all__ = ["WireFieldMetadata", "WireEntityMetadata", "NormalizedWireInput", "WireInputError", "create_wire_entity_metadata", "normalize_wire_input", "encode_wire_output", "retain_submitted_paths", "EntityKey", "EntityChangeSet", "EntityRoot", "ContextEntityRef", "ContextRootError", "CheckException", "CheckResult", "I18nCatalog", "JsonFieldNamingProfile", "Locale", "ObjectLocation", "UnsupportedLocaleError", "UserContext", "TeaqlRuntime", "SqlLogEntry", "SqlLogOperation", "DiagnosticSqlLogSink", "TextDiagnosticSqlLogSink", "ServiceRuntimeFromEnv", "RuntimeModule", "DataStore", "RawAuditEvent", "SafeAuditEvent", "MutationAuditKind", "ContextTools", "ExecutableHttpTool", "HTTP_TOOL", "HttpIntentPhase", "HttpTool", "HttpToolProvider", "ToolDeniedError", "ToolError", "ToolPolicy", "ToolRisk", "Tools", "ToolToken", "ToolUnavailableError"]


def __getattr__(name):
    # Keep provider construction lazy: importing a SQL provider loads runtime
    # telemetry, which must not recursively import the provider through env.
    if name == "ServiceRuntimeFromEnv":
        from .env import ServiceRuntimeFromEnv
        return ServiceRuntimeFromEnv
    raise AttributeError(name)
