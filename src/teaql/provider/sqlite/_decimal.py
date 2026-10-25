"""Connection-local exact Decimal storage, ordering and SUM for SQLite."""

import re
import sqlite3
from decimal import Decimal, InvalidOperation, localcontext


MAX_PLAIN_CHARS = 10_000
_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")


def parse_decimal(value):
    # Bound the plain representation before any expansion or arithmetic. The
    # bound also prevents an exponent supplied by a remote caller from causing
    # an enormous allocation in an otherwise small aggregate.
    if not isinstance(value, (str, Decimal)):
        raise ValueError("SQLite exact Decimal requires text or Decimal")
    text = str(value)
    if len(text) > MAX_PLAIN_CHARS or not _DECIMAL.fullmatch(text):
        raise ValueError("invalid SQLite exact Decimal")
    try:
        result = Decimal(text)
    except InvalidOperation:
        raise ValueError("invalid SQLite exact Decimal") from None
    if not result.is_finite():
        raise ValueError("invalid SQLite exact Decimal")
    sign, digits, exponent = result.as_tuple()
    plain_chars = (len(digits) + exponent if exponent >= 0 else
                   max(len(digits) + 1, 2 - exponent)) + sign
    if plain_chars > MAX_PLAIN_CHARS:
        raise ValueError("SQLite exact Decimal exceeds bounded precision domain")
    return result


def decimal_text(value):
    return str(parse_decimal(value))


def _valid(value):
    if not isinstance(value, str):
        return 0
    try:
        parse_decimal(value)
    except ValueError:
        return 0
    return 1


def _compare(left, right):
    first, second = parse_decimal(left), parse_decimal(right)
    return (first > second) - (first < second)


class _DecimalSum:
    def __init__(self):
        self.total = None

    def step(self, value):
        if value is None:
            return
        amount = parse_decimal(value)
        if self.total is None:
            self.total = amount
            return
        lowest_exponent = min(self.total.as_tuple().exponent, amount.as_tuple().exponent)
        highest_digit = max(self.total.adjusted(), amount.adjusted())
        with localcontext() as context:
            context.prec = max(1, highest_digit - lowest_exponent + 2)
            context.Emax = MAX_PLAIN_CHARS * 2
            context.Emin = -MAX_PLAIN_CHARS * 2
            self.total = parse_decimal(self.total + amount)

    def finalize(self):
        return None if self.total is None else str(self.total)


class DecimalConnection(sqlite3.Connection):
    """Installed by aiosqlite's public connection factory on its worker thread."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_collation("TEAQL_DECIMAL", _compare)
        self.create_function("teaql_decimal_valid", 1, _valid, deterministic=True)
        self.create_aggregate("teaql_decimal_sum", 1, _DecimalSum)
