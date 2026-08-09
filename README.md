# TeaQL Python SDK

TeaQL Python SDK is a runtime engine and toolkit for building data-driven business applications. It provides seamless integration with the TeaQL ecosystem, fully aligned with the `teaql-rs` baseline.

## 1. 最小的版本需求 (Minimum Requirements)

*   **Python**: 3.10+ (Recommended 3.12+)
*   **Testing**: `pytest` 7.4+
*   **Dependencies**: `pydantic` >= 2.0, `aiosqlite`, `aiomysql`, `asyncpg`

## 2. 我们已经做过哪些测试 (Tests Performed)

经过严格的 AST 语义分析与人工核对，本 SDK 已经完成了以下测试与验证：
*   ✅ **API 100% 签名与功能对齐**：使用 Tree-Sitter 扫描并填补了所有与 Rust 基准不一致的内部方法与缺失逻辑。
*   ✅ **`teaql.core` 核心测试**：`Value`, `GraphNode`, `Entity`, `Mutation`, `Query`, `Expr`, `SafeExpression` 的属性提取、扩展判空与关系构建。
*   ✅ **`teaql.runtime` 运行环境测试**：`UserContext` 的上下文传递、`record_sql_log` 和 `record_metadata_log` 的日志钩子闭环。
*   ✅ **`teaql.sql` / `teaql.data_service` 测试**：SQL AST 编译引擎及底层命令分发测试。
*   ✅ **驱动与外部集成**：包含 SQLite 驱动执行、FastAPI Web 端点等集成测试。

## 3. 有哪些模块 (Available Modules)

SDK 的组织架构与 Rust 版本保持绝对一致：
*   `teaql.core`: 提供底层核心数据结构（`Value`, `GraphNode`, `Entity`, `SelectQuery`, `MutationRequest` 等）。
*   `teaql.data_service`: 定义通用的数据服务抽象，处理结构化入参和出参。
*   `teaql.sql`: 提供跨方言的 SQL 编译执行器，将 AST 转换为各个数据库的物理执行语句。
*   `teaql.runtime`: Pipeline 管道与应用上下文（`UserContext`, 环境挂载等）。
*   `teaql.provider`: 物理数据库驱动实现包（如 `sqlite`, `mysql`, `postgres`）。
*   `teaql.web`: Web 框架集成中间件（如 `FastAPI` / `Starlette`）。

## 4. 里面有什么功能 (Features)

*   **Entity & Value Mapping**: 在 Python 原生类型与 TeaQL 核心类型（I64, Text, F64, Null 等）之间提供类型安全的映射。
*   **SQL Compilation & AST Building**: 动态、安全的 SQL 语句构建器，支持生成标准化的 `INSERT`, `UPDATE`, `DELETE`, 和 `SELECT` 语句及方言差异抹平。
*   **Facet Aggregation & Grouping**: 开箱即用的多维度分面聚合、Group-By 和树形结构数据处理支持。
*   **Provider Support**: 高度可扩展的异步数据库连接（通过统一 Transport 层集成 `aiosqlite` 等三方异步驱动）。
*   **Context & Logging Management**: 内置支持生命周期上下文传递、全链路 Trace 和 SQL 执行日志侦听分发。

---
To run test validations and business logic simulations locally, simply run `pytest` in the project root.