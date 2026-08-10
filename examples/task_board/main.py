import asyncio
import aiosqlite
import time
from teaql.provider.sqlite import create_sqlite_service, SimpleSchemaProvider
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.value import DataType, Value, Timestamp
from teaql.core.query import SelectQuery
from teaql.core.mutation import InsertCommand, UpdateCommand, DeleteCommand, MutationRequest
from teaql.data_service import QueryRequest
from teaql.runtime.context import UserContext

async def main():
    print("Setting up Schema Provider...")
    provider = SimpleSchemaProvider()

    # 1. Platform
    platform_entity = EntityDescriptor("Platform")\
        .table_name("platform")\
        .property(PropertyDescriptor("id", DataType.I64).is_id())\
        .property(PropertyDescriptor("name", DataType.Text))\
        .property(PropertyDescriptor("founded", DataType.Timestamp))\
        .property(PropertyDescriptor("user_email", DataType.Text))\
        .property(PropertyDescriptor("version", DataType.I64).is_version())
    provider.register_entity(platform_entity)

    # 2. TaskStatus
    task_status_entity = EntityDescriptor("TaskStatus")\
        .table_name("task_status")\
        .property(PropertyDescriptor("id", DataType.I64).is_id())\
        .property(PropertyDescriptor("name", DataType.Text))\
        .property(PropertyDescriptor("code", DataType.Text))\
        .property(PropertyDescriptor("color", DataType.Text))\
        .property(PropertyDescriptor("display_order", DataType.I64))\
        .property(PropertyDescriptor("progress", DataType.I64))\
        .property(PropertyDescriptor("platform", DataType.I64))\
        .property(PropertyDescriptor("version", DataType.I64).is_version())
    provider.register_entity(task_status_entity)

    # 3. Task
    task_entity = EntityDescriptor("Task")\
        .table_name("task")\
        .property(PropertyDescriptor("id", DataType.I64).is_id())\
        .property(PropertyDescriptor("name", DataType.Text))\
        .property(PropertyDescriptor("status", DataType.I64))\
        .property(PropertyDescriptor("platform", DataType.I64))\
        .property(PropertyDescriptor("version", DataType.I64).is_version())
    provider.register_entity(task_entity)

    # 4. TaskExecutionLog
    log_entity = EntityDescriptor("TaskExecutionLog")\
        .table_name("task_execution_log")\
        .property(PropertyDescriptor("id", DataType.I64).is_id())\
        .property(PropertyDescriptor("task", DataType.I64))\
        .property(PropertyDescriptor("action", DataType.Text))\
        .property(PropertyDescriptor("detail", DataType.Text))\
        .property(PropertyDescriptor("version", DataType.I64).is_version())
    provider.register_entity(log_entity)

    db_path = "task_board.db"
    print(f"Creating sqlite service at {db_path}...")
    service = create_sqlite_service(db_path, provider)

    print("Initializing Database Schema...")
    ctx = UserContext.new()
    for e in provider.entities.values():
        ctx.register_entity(e)
    
    await service.ensure_schema(ctx)

    print("Performing CRUD operations...")

    # CREATE Platform
    print("Creating Platform...")
    insert_req = MutationRequest(InsertCommand("Platform", {
        "id": Value.I64(1), 
        "name": Value.Text("Main Platform"),
        "founded": Value.Timestamp(Timestamp(int(time.time() * 1000))),
        "user_email": Value.Text("admin@robot.com"),
        "version": Value.I64(1)
    }))
    await service.mutate(ctx, insert_req)

    # CREATE TaskStatus
    print("Creating TaskStatus...")
    insert_status = MutationRequest(InsertCommand("TaskStatus", {
        "id": Value.I64(1),
        "name": Value.Text("Planned"),
        "code": Value.Text("PLANNED"),
        "color": Value.Text("#94A3B8"),
        "display_order": Value.I64(10),
        "progress": Value.I64(0),
        "platform": Value.I64(1),
        "version": Value.I64(1)
    }))
    await service.mutate(ctx, insert_status)

    # CREATE Task
    print("Creating Task...")
    insert_task = MutationRequest(InsertCommand("Task", {
        "id": Value.I64(1),
        "name": Value.Text("Build Robot Arm"),
        "status": Value.I64(1),
        "platform": Value.I64(1),
        "version": Value.I64(1)
    }))
    await service.mutate(ctx, insert_task)

    # READ Task
    print("Reading Tasks...")
    query_task = QueryRequest(SelectQuery("Task"))
    res = await service.query(ctx, query_task)
    for row in res.rows:
        print("  - Task:", row)

    # UPDATE Task
    print("Updating Task...")
    update_task = MutationRequest(UpdateCommand("Task", Value.I64(1)).value("name", Value.Text("Build Robot Leg")))
    await service.mutate(ctx, update_task)

    # Verify Update
    res = await service.query(ctx, query_task)
    print("  - Updated Task:", res.rows[0])

    # INSERT TaskExecutionLog
    print("Inserting TaskExecutionLog...")
    insert_log = MutationRequest(InsertCommand("TaskExecutionLog", {
        "id": Value.I64(1),
        "task": Value.I64(1),
        "action": Value.Text("Updated Task"),
        "detail": Value.Text("Changed arm to leg"),
        "version": Value.I64(1)
    }))
    await service.mutate(ctx, insert_log)

    # QUERY Log
    print("Reading Logs...")
    query_log = QueryRequest(SelectQuery("TaskExecutionLog"))
    res = await service.query(ctx, query_log)
    for row in res.rows:
        print("  - Log:", row)

    print("Success!")

if __name__ == "__main__":
    asyncio.run(main())
