import sqlite3
import datetime
import logging
import os

# Setup basic logging for the library
# Tasks using this should configure their own overall logging
status_lib_logger = logging.getLogger('folder_watcher_status_lib')
status_lib_logger.setLevel(logging.INFO)
# Add handler if needed, e.g., logging.StreamHandler()

def _get_task_db_connection(db_path):
    """Establishes a connection for the task status updates."""
    try:
        # Tasks should not run concurrently on the *exact* same file_path
        # SQLite default locking should handle concurrent updates from different tasks okay,
        # but could block if many tasks update very frequently.
        # Consider increasing timeout if lock errors occur: sqlite3.connect(db_path, timeout=10)
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        status_lib_logger.error(f"[Status Lib] Failed to connect to database '{db_path}': {e}")
        return None

def _execute_update(db_path, sql, params):
    """Executes a single update statement."""
    conn = _get_task_db_connection(db_path)
    if not conn:
        return False
    try:
        with conn: # Context manager handles commit/rollback
            conn.execute(sql, params)
        status_lib_logger.debug(f"[Status Lib] Executed update successfully. SQL: {sql[:50]}...")
        return True
    except sqlite3.Error as e:
        status_lib_logger.error(f"[Status Lib] Database error during update: {e}")
        return False
    # Connection closed automatically by 'with'

def update_status(db_path: str, file_path: str, status: str = None, stage: str = None, message: str = None, pid: str = None):
    """
    Updates the status, stage, message, or pid of an active task.
    Args:
        db_path (str): Path to the SQLite database file.
        file_path (str): The unique file path identifying the active task run.
        status (str, optional): New status ('Running').
        stage (str, optional): Current processing stage.
        message (str, optional): Status message.
        pid (str, optional): The PID of the task executor process.
    Returns:
        bool: True if update was successful, False otherwise.
    """
    if not db_path or not file_path:
        status_lib_logger.error("[Status Lib] db_path and file_path are required for update_status.")
        return False

    fields_to_update = {}
    if status is not None:
        fields_to_update['status'] = status
    if stage is not None:
        fields_to_update['current_stage'] = stage
    if message is not None:
        fields_to_update['message'] = message
    if pid is not None:
        fields_to_update['executor_pid'] = pid

    # Always update the timestamp
    fields_to_update['last_update_time'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if not fields_to_update:
        status_lib_logger.warning("[Status Lib] No fields provided to update_status.")
        return False

    set_clauses = ", ".join([f"{key} = ?" for key in fields_to_update])
    sql = f"UPDATE active_tasks SET {set_clauses} WHERE file_path = ?"

    params = list(fields_to_update.values()) + [file_path]

    status_lib_logger.info(f"[Status Lib] Updating task status for {file_path}: {fields_to_update}")
    return _execute_update(db_path, sql, tuple(params))


def set_final_status(db_path: str, file_path: str, final_status: str, final_message: str = ""):
    """
    Placeholder: In v0.3, the main app moves tasks to history.
    Tasks *could* use this to signal completion state if the design changes,
    or just use it to update the final message before exiting.
    Currently, tasks signal completion by exiting. The main app handles the history move.

    Args:
        db_path (str): Path to the SQLite database file.
        file_path (str): The unique file path identifying the active task run.
        final_status (str): 'Completed' or 'Aborted'.
        final_message (str, optional): Final status message.
    Returns:
        bool: True if update was successful, False otherwise.
    """
    # In the current design (SDD 0.3), the task simply exits, and the main app
    # detects this and calls database.move_task_to_history.
    # A task *could* potentially use this to update its message just before exiting.
    status_lib_logger.info(f"[Status Lib] Task for {file_path} reporting final status '{final_status}'. Main app will move to history.")
    # Optional: Update the message one last time if provided
    if final_message:
         return update_status(db_path=db_path, file_path=file_path, message=f"Final ({final_status}): {final_message}")
    return True # Indicate signal was received


# Example Usage (if run directly - requires a dummy DB and task entry)
if __name__ == '__main__':
    print("Status Updater Library - Example Usage")
    # Setup dummy DB and entry for testing
    test_db = "test_status_lib.db"
    if os.path.exists(test_db): os.remove(test_db)
    conn_test = sqlite3.connect(test_db)
    conn_test.execute('''
        CREATE TABLE active_tasks (
            id INTEGER PRIMARY KEY, file_path TEXT UNIQUE, status TEXT,
            current_stage TEXT, message TEXT, last_update_time TEXT, executor_pid TEXT
        )''')
    conn_test.execute("INSERT INTO active_tasks (file_path, status) VALUES (?, ?)", ('/path/to/testfile.txt', 'Pending'))
    conn_test.commit()
    conn_test.close()
    print(f"Created dummy DB '{test_db}' with test entry.")

    print("\n1. Updating status to Running with PID:")
    success = update_status(test_db, '/path/to/testfile.txt', status='Running', pid='12345')
    print(f"Update successful: {success}")

    print("\n2. Updating stage and message:")
    success = update_status(test_db, '/path/to/testfile.txt', stage='Processing Step 1', message='50% done')
    print(f"Update successful: {success}")

    print("\n3. Signaling final status (Completed):")
    # Note: This only updates the message in the current design
    success = set_final_status(test_db, '/path/to/testfile.txt', 'Completed', 'All steps finished.')
    print(f"Final status signal successful: {success}")

    # Verify final state (optional)
    conn_verify = sqlite3.connect(test_db)
    task = conn_verify.execute("SELECT * from active_tasks WHERE file_path=?", ('/path/to/testfile.txt',)).fetchone()
    conn_verify.close()
    print("\nFinal state in active_tasks (before main app moves it):")
    if task:
        for key in task.keys(): print(f"- {key}: {task[key]}")
    else:
        print("Task not found (unexpected)")

    # Cleanup
    # os.remove(test_db)