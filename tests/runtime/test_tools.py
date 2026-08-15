import pytest

from teaql.runtime import (
    ContextTools, HTTP_TOOL, HttpToolProvider, ToolDeniedError, ToolError,
    ToolPolicy, ToolRisk, ToolToken, ToolUnavailableError, UserContext,
)


async def transport(method: str, url: str, body: bytes | None) -> tuple[int, bytes]:
    del body
    return 200, f"{method}:{url}".encode()


@pytest.mark.asyncio
async def test_policy_gated_native_http_response():
    tools = (ContextTools.builder(UserContext.new())
             .policy(ToolPolicy.allowing(HTTP_TOOL))
             .provider(HttpToolProvider(transport)).build())
    value: str = await tools.get(HTTP_TOOL).get("https://example.com").purpose("status").execute()
    assert value == "GET:https://example.com"


@pytest.mark.asyncio
async def test_tool_negatives_are_explicit():
    denied = (ContextTools.builder(UserContext.new())
              .provider(HttpToolProvider(transport)).build())
    with pytest.raises(ToolDeniedError):
        denied.get(HTTP_TOOL)
    with pytest.raises(ToolUnavailableError):
        denied.get(ToolToken("unknown", ToolRisk.MEMORY_ONLY))

    allowed = (ContextTools.builder(UserContext.new())
               .policy(ToolPolicy.allowing(HTTP_TOOL))
               .provider(HttpToolProvider(transport)).build())
    with pytest.raises(ToolError, match="non-empty intent"):
        await allowed.get(HTTP_TOOL).get("https://example.com").purpose(" ").execute()
