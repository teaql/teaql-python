"""Current generated library + local runtime; no manual DDL or bootstrap writes."""
import asyncio
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().with_name("generated")))

from E import E
from Q import Q
from models.task import Task
from models.task_execution_log import TaskExecutionLog
from runtime_module import GENERATED_RUNTIME_MODULE
from teaql.data_service import SQLiteTeaQLClient
from teaql.runtime import UserContext


async def main():
    database = os.environ.get("TEAQL_TASK_BOARD_DB")
    if not database:
        with tempfile.NamedTemporaryFile(prefix="teaql-task-board-", suffix=".db", delete=False) as file:
            database = file.name
    client = SQLiteTeaQLClient(database)
    context = UserContext.new().install(GENERATED_RUNTIME_MODULE).insert_resource("dataService", client)
    try:
        await context.ensure_schema()
        await context.ensure_schema()
        task = Task(name="Build Robot Arm", platform=1).update_status_to_planned()
        await task.audit_as("create demo robot task").save(context)
        loaded = await (Q.tasks().with_id_is(task.id).limit(1)
                        .select_status_with(Q.task_statuses().limit(1))
                        .comment("load task and planned status").purpose("review complete task before editing")
                        .execute_for_one(context))
        assert E.task(loaded).name().eval() == "Build Robot Arm"
        assert E.task(loaded).status().name().eval() == "Planned"
        await loaded.update_name("Build Robot Arm V2").audit_as("rename demo robot task").save(context)
        updated = await (Q.tasks().with_id_is(task.id).limit(1)
                         .comment("read renamed task").purpose("verify persisted mutation")
                         .execute_for_one(context))
        assert updated.name == "Build Robot Arm V2"
        page = await (Q.tasks().with_id_is(task.id)
                      .comment("page renamed task").purpose("verify paginated task intent")
                      .execute_for_page(context, 0, 1))
        assert page.total_count == 1 and page.data[0].name == "Build Robot Arm V2"
        streamed = []
        async for row in (Q.tasks().with_id_is(task.id)
                          .comment("stream renamed task").purpose("verify streamed task intent")
                          .execute_for_stream(context, chunk_size=1)):
            streamed.append(row)
        assert len(streamed) == 1 and streamed[0].name == "Build Robot Arm V2"
        entry = TaskExecutionLog(task=task.id, action="RENAME", detail="PRIVATE-TASK-DETAIL")
        await entry.audit_as("record PRIVATE-TASK-DETAIL rename evidence").save(context)
        rows = await (Q.task_execution_logs().with_id_is(entry.id).with_detail_is("PRIVATE-TASK-DETAIL").limit(1)
                      .comment("read PRIVATE-TASK-DETAIL evidence").purpose("verify PRIVATE-TASK-DETAIL is persisted")
                      .execute_for_list(context))
        assert len(rows) == 1 and E.task_execution_log(rows[0]).detail().eval() == "PRIVATE-TASK-DETAIL"
        print("PASS task board: governed Q/E/mutation and masked detail")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
