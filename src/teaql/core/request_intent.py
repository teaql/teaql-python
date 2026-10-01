"""Validated, request-owned intent shared by all execution adapters."""
from dataclasses import dataclass, field
from typing import Optional


class RequestIntentError(ValueError):
    def __init__(self, code: str, field_name: str, request_kind: str):
        self.code = code
        self.field = field_name
        self.request_kind = request_kind
        super().__init__(
            f'{code}: {request_kind} request requires non-blank {field_name}; '
            f'supply {field_name} at the request entry point')


def _white_space(character: str) -> bool:
    # Unicode White_Space, identical to Rust str::trim. Python str.isspace()
    # additionally accepts U+001C..U+001F, which are NOT contract whitespace.
    value = ord(character)
    return (0x09 <= value <= 0x0D or value in (
        0x20, 0x85, 0xA0, 0x1680, 0x2028, 0x2029, 0x202F, 0x205F, 0x3000)
        or 0x2000 <= value <= 0x200A)


def require_intent(value: Optional[str], field_name: str, request_kind: str) -> str:
    if not isinstance(value, str) or not value or all(_white_space(c) for c in value):
        code = 'QUERY_PURPOSE_REQUIRED' if field_name == 'purpose' else 'REQUEST_COMMENT_REQUIRED'
        raise RequestIntentError(code, field_name, request_kind)
    return value  # Preserve text verbatim; validation must not rewrite evidence.


@dataclass(frozen=True, slots=True)
class QueryIntent:
    comment: str = field(repr=False)
    purpose: str = field(repr=False)

    def __post_init__(self):
        require_intent(self.comment, 'comment', 'query')
        require_intent(self.purpose, 'purpose', 'query')

    @classmethod
    def from_query(cls, query):
        return cls(getattr(query, 'comment_text', None), getattr(query, 'purpose_text', None))


@dataclass(frozen=True, slots=True)
class MutationIntent:
    comment: str = field(repr=False)

    def __post_init__(self):
        require_intent(self.comment, 'comment', 'mutation')

    def readback(self) -> QueryIntent:
        return QueryIntent(self.comment, 'verify the persisted mutation result')
