import asyncio
import aiosqlite
import time
from teaql.provider.sqlite import create_sqlite_service, SimpleSchemaProvider
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.value import DataType, Value, Timestamp
from teaql.data_service import QueryRequest
from teaql.runtime.context import UserContext

from generated.models.platform import Platform
from generated.models.task_status import TaskStatus
from generated.models.task import Task
from generated.models.task_execution_log import TaskExecutionLog

from generated.requests.task_request import TaskRequest
from generated.requests.task_execution_log_request import TaskExecutionLogRequest


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
        .property(PropertyDescriptor("displayOrder", DataType.I64))\
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
    platform = Platform(
        id=1,
        name="Main Platform",
        founded=Timestamp(int(time.time() * 1000)),
        userEmail="admin@robot.com",
        version=1
    )
    platform._action = "Create"
    await platform.save(ctx, service)

    # CREATE TaskStatus
    print("Creating TaskStatus...")
    status = TaskStatus(
        id=1,
        name="Planned",
        code="PLANNED",
        color="#94A3B8",
        displayOrder=10,
        progress=0,
        platform=1,
        version=1
    )
    status._action = "Create"
    await status.save(ctx, service)

    # CREATE Task
    print("Creating Task...")
    task = Task(
        id=1,
        name="Build Robot Arm",
        status=1,
        platform=1,
        version=1
    )
    task._action = "Create"
    await task.save(ctx, service)

    # READ Task
    print("Reading Tasks...")
    task_req = TaskRequest()
    res = await task_req.execute_for_list(ctx, service)
    for row in res["data"]:
        print("  - Task:", row)

    # UPDATE Task
    print("Updating Task...")
    task.name = "Build Robot Leg"
    task._action = "Update"
    await task.save(ctx, service)

    # Verify Update
    res = await task_req.execute_for_list(ctx, service)
    print("  - Updated Task:", res["data"][0])

    # INSERT TaskExecutionLog
    print("Inserting TaskExecutionLog...")
    log = TaskExecutionLog(
        id=1,
        task=1,
        action="Updated Task",
        detail="Changed arm to leg",
        version=1
    )
    log._action = "Create"
    await log.save(ctx, service)

    # QUERY Log
    print("Reading Logs...")
    log_req = TaskExecutionLogRequest()
    res = await log_req.execute_for_list(ctx, service)
    for row in res["data"]:
        print("  - Log:", row)

    print("Success!")

if __name__ == "__main__":
    asyncio.run(main())
