from datetime import time
from types import SimpleNamespace

import pytest

from teaql.core.value import DataType, Value
from teaql.provider.postgres.dialect import PostgresDialect
from teaql.provider.mysql.dialect import MysqlDialect
from teaql.provider.sqlite.dialect import SqliteDialect
from teaql.provider.sqlite.transport import SqliteTransport
from teaql.sql.executor import SqlDataServiceExecutor
from teaql.sql.types import DatabaseKind, _sql_literal


def test_time_scalar_has_portable_schema_and_sql_bindings():
    value = Value.Time(time(9, 30, 15))
    assert SqliteDialect().schema_type_sql(DataType.Time, None) == "TEXT"
    assert PostgresDialect().schema_type_sql(DataType.Time, None) == "TIME"
    assert MysqlDialect().schema_type_sql(DataType.Time, None) == "TIME"
    assert SqliteTransport(":memory:")._bind_values([value]) == ("09:30:15",)
    assert _sql_literal(value, DatabaseKind.Sqlite) == "'09:30:15'"
    assert _sql_literal(value, DatabaseKind.PostgreSql) == "TIME '09:30:15'"


def test_only_declared_time_columns_are_normalized():
    prop = SimpleNamespace(name="required_time", column_name_val="required_time", property_type=DataType.Time)
    descriptor = SimpleNamespace(_name="ScalarTypeProbe", properties=[prop])
    rows = [{"required_time": "09:30:15", "computed": "09:30:15"}]
    SqlDataServiceExecutor._normalize_loaded_dates(rows, descriptor)
    assert rows == [{"required_time": time(9, 30, 15), "computed": "09:30:15"}]
    with pytest.raises(ValueError, match="invalid loaded Time field"):
        SqlDataServiceExecutor._normalize_loaded_dates([{"required_time": "25:30:15"}], descriptor)
