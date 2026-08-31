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
from .i18n import CheckException, CheckResult, I18nCatalog, Locale, ObjectLocation, UnsupportedLocaleError
from teaql.core.entity import EntityKey, EntityChangeSet, EntityRoot

__all__ = ["EntityKey", "EntityChangeSet", "EntityRoot", "ContextEntityRef", "ContextRootError", "CheckException", "CheckResult", "I18nCatalog", "Locale", "ObjectLocation", "UnsupportedLocaleError", "UserContext", "TeaqlRuntime", "SqlLogEntry", "SqlLogOperation", "DiagnosticSqlLogSink", "TextDiagnosticSqlLogSink", "ServiceRuntimeFromEnv", "RuntimeModule", "DataStore", "RawAuditEvent", "SafeAuditEvent", "MutationAuditKind", "ContextTools", "ExecutableHttpTool", "HTTP_TOOL", "HttpIntentPhase", "HttpTool", "HttpToolProvider", "ToolDeniedError", "ToolError", "ToolPolicy", "ToolRisk", "Tools", "ToolToken", "ToolUnavailableError"]


def __getattr__(name):
    # Keep provider construction lazy: importing a SQL provider loads runtime
    # telemetry, which must not recursively import the provider through env.
    if name == "ServiceRuntimeFromEnv":
        from .env import ServiceRuntimeFromEnv
        return ServiceRuntimeFromEnv
    raise AttributeError(name)
