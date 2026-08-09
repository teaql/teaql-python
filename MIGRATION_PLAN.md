# TeaQL Python 迁移计划

本文档记录从 `teaql-rs` (Rust 版本) 迁移到 `teaql-python` (Python 版本) 的计划。

## 目标
1. 保持与 Rust 版本的语义 1:1 对齐（包含所有底层算法、请求链式调用机制）。
2. 在开发者使用的 API 体验上，提供“读起来一模一样”的调用方式（保留业务层 Builder 模式流畅调用的感觉）。
3. 所有测试用例（尤其是以 Robot 机器人为测试例子的单元测试）必须严格迁移并保证等效通过。
4. 目标运行环境: Python 3.10+。无需向后兼容较老版本。

## 迁移阶段

### 阶段一：项目初始化与基础设施搭建
* 初始化 `pyproject.toml`，引入 `pytest` (用于单元测试)，`mypy` (严格类型检查)，`pytest-asyncio`。
* 明确包结构：`teaql.core`, `teaql.sql`, `teaql.runtime`, `teaql.data_service`。

### 阶段二：核心模型与数据结构 (对应 `teaql-core` 和 `teaql-sql`)
* 将 Rust 中的基础语法树（AST）节点、表达式（Expr）、查询结构（Query）迁移为 Python `@dataclass`。
* 使用结构化特性或 Enum 替代 Rust 的 enum/match。
* 迁移所有针对 `teaql-core` / `teaql-sql` 的基础单元测试。

### 阶段三：运行时与服务层 (对应 `teaql-runtime` 和 `teaql-data-service`)
* 迁移 UserContext，TraceNode 审计节点。
* 采用 Python 的 `asyncio` 来对接数据执行接口，对应 Rust 中的异步 Trait。
* 迁移执行流水线（Pipeline/Middleware）。

### 阶段四：测试用例全量对齐（Robot 示例工程）
* 根据 `teaql-rs` 中现有的测试用例集（如 Robot/Task 等业务实体的测试用例），在 Python 中进行完整重构。
* 验证算法的一致性：例如 JSON 序列化结构、查询构建（Build SQL）输出的结构，必须完全一致。
