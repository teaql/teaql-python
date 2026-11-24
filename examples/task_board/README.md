# Robot task board

Create a robot task, inspect its planned status, rename it and read the attached
execution history. The example calls explicit schema setup twice to reconcile
the platform and four status constants.

- `model.xml` owns the robot task, status and execution-log model.
- `python-lib-core/` holds the generated domain library.
- `python-app-console/app/main.py` runs the application through generated Q and E.

The SDK inventory uses this workspace. Set `TEAQL_TASK_BOARD_DB` to a file
in an existing directory to retain data. Each run adds one task and its
history while preserving the root and constants. The focused acceptance runs
twice against one database and independently checks task versions, status and
history. The native log test checks intent and masks the private log detail.
