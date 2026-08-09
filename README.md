# TeaQL Python SDK

TeaQL Python SDK is a runtime engine and toolkit for building data-driven business applications. It provides seamless integration with the TeaQL ecosystem, fully aligned with the `teaql-rs` baseline.

## 1. Minimum Version Requirements

*   **Python**: 3.10+ (Recommended 3.12+)
*   **Testing**: `pytest` 7.4+
*   **Dependencies**: `pydantic` >= 2.0, `aiosqlite`, `aiomysql`, `asyncpg`

## 2. Tests Performed

After rigorous AST semantic analysis and manual verification, this SDK has successfully passed the following tests:
*   ✅ **100% API Signature and Logic Parity**: Scanned with Tree-Sitter and implemented all internal methods and logic to match the Rust baseline.
*   ✅ **`teaql.core` Core Tests**: Extensively tested attribute extraction, safe nullability checks, and relationship building for `Value`, `GraphNode`, `Entity`, `Mutation`, `Query`, `Expr`, and `SafeExpression`.
*   ✅ **`teaql.runtime` Runtime Tests**: Verified the context propagation of `UserContext` and the complete lifecycle hooking for `record_sql_log` and `record_metadata_log`.
*   ✅ **`teaql.sql` / `teaql.data_service` Tests**: Tested the SQL AST compilation engine and the underlying command dispatch mechanism.
*   ✅ **Provider & External Integrations**: Includes integration tests for the SQLite driver and FastAPI web endpoints.

## 3. Available Modules

The SDK's organizational architecture strictly mirrors the Rust version:
*   `teaql.core`: Provides core underlying data structures (e.g., `Value`, `GraphNode`, `Entity`, `SelectQuery`, `MutationRequest`).
*   `teaql.data_service`: Defines universal data service abstractions, handling structured inputs and outputs.
*   `teaql.sql`: Provides a cross-dialect SQL compilation executor, translating ASTs into physical queries for various databases.
*   `teaql.runtime`: Contains the pipeline and application context mechanisms (e.g., `UserContext`, environment mounts).
*   `teaql.provider`: Packages for physical database driver implementations (e.g., `sqlite`, `mysql`, `postgres`).
*   `teaql.web`: Web framework integration middleware (e.g., `FastAPI` / `Starlette`).

## 4. Features

*   **Entity & Value Mapping**: Provides type-safe mapping between native Python types and TeaQL core primitives (I64, Text, F64, Null, etc.).
*   **SQL Compilation & AST Building**: A dynamic, secure SQL query builder that generates standardized `INSERT`, `UPDATE`, `DELETE`, and `SELECT` statements while abstracting away dialect differences.
*   **Facet Aggregation & Grouping**: Out-of-the-box support for multi-dimensional facet aggregations, group-bys, and hierarchical data processing.
*   **Provider Support**: Highly extensible asynchronous database connectivity (integrating third-party async drivers like `aiosqlite` through a unified Transport layer).
*   **Context & Logging Management**: Built-in support for lifecycle context passing, end-to-end tracing, and SQL execution log interception and dispatch.

---
To run test validations and business logic simulations locally, simply run `pytest` in the project root.