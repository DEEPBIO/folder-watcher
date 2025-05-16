#!/usr/bin/env python3
#
# status_manager.py
#
# this module is designed to manage the status of tasks in a SQLite database.
# It provides functions for initializing the database, creating task entries,
# updating task statuses, and querying task information.
# The module uses SQLite3 to store task information, including task ID, target file,
# status, start time, end time, and any messages associated with the task.
# The task ID is generated using UUID to ensure uniqueness.
# The module is intended to be used in a context where tasks are monitored by a watcher,
# which can query the status of tasks and update their statuses as they progress.
#

import sqlite3
import uuid
import datetime
import os

# --- Constants ---
DB_FILE = 'task_status.db' # SQLite 데이터베이스 파일 이름
TABLE_NAME = 'task_status' # 테이블 이름

# Task 상태 값
STATUS_RUNNING = 'RUNNING'
STATUS_SUCCESS = 'SUCCESS'
STATUS_FAILED = 'FAILED'
STATUS_PENDING = 'PENDING' # (Optional) Task 시작 전 대기 상태

# --- Database Initialization ---
def initialize_db(db_path=DB_FILE):
    """
    SQLite 데이터베이스 및 task_status 테이블을 초기화합니다.
    테이블이 이미 존재하면 새로 생성하지 않습니다.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        create_table_sql = f'''
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            task_id TEXT PRIMARY KEY,
            target_file TEXT NOT NULL,
            status TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            message TEXT
        );
        '''
        cursor.execute(create_table_sql)
        conn.commit()
        print(f"Database initialized at {db_path}")
    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --- Functions for the Task to Use ---

def create_task_entry(task_id, target_file, db_path=DB_FILE):
    """
    Task가 시작될 때 자신의 상태 항목을 데이터베이스에 생성합니다.
    task_id는 watcher로부터 uuid로 생성되어 전달됩니다.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        current_time = datetime.datetime.now().isoformat()

        insert_sql = f'''
        INSERT INTO {TABLE_NAME} (task_id, target_file, status, start_time, end_time, message)
        VALUES (?, ?, ?, ?, ?, ?);
        '''
        # Task가 생성되면 바로 실행 상태로 간주
        cursor.execute(insert_sql, (task_id, target_file, STATUS_RUNNING, current_time, None, None))
        conn.commit()
        # print(f"Task entry created for task_id: {task_id}")
    except sqlite3.IntegrityError:
        print(f"Error: Task ID {task_id} already exists. This should not happen with UUIDs normally.")
        if conn:
             conn.rollback()
    except sqlite3.Error as e:
        print(f"Database error creating task entry {task_id}: {e}")
        if conn:
             conn.rollback()
    finally:
        if conn:
            conn.close()

def update_task_status(task_id, status, message=None, db_path=DB_FILE):
    """
    Task가 자신의 상태를 데이터베이스에 업데이트합니다.
    status는 STATUS_RUNNING, STATUS_SUCCESS, STATUS_FAILED 중 하나입니다.
    최종 상태(SUCCESS, FAILED)인 경우 end_time이 업데이트됩니다.
    """
    if status not in [STATUS_RUNNING, STATUS_SUCCESS, STATUS_FAILED]:
        print(f"Warning: Invalid status '{status}' for task_id {task_id}. Not updating.")
        return

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        current_time = datetime.datetime.now().isoformat()

        update_sql = f'''
        UPDATE {TABLE_NAME}
        SET status = ?,
            end_time = ?,
            message = ?
        WHERE task_id = ?;
        '''

        end_time = current_time if status in [STATUS_SUCCESS, STATUS_FAILED] else None

        cursor.execute(update_sql, (status, end_time, message, task_id))

        if cursor.rowcount == 0:
            print(f"Warning: Task ID {task_id} not found for update.")

        conn.commit()
        # print(f"Task status updated for task_id {task_id} to {status}")

    except sqlite3.Error as e:
        print(f"Database error updating task status {task_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --- Functions for the Watcher to Use ---

def get_task_status(task_id, db_path=DB_FILE):
    """
    특정 Task ID의 상태 정보를 조회합니다. Task 자체 또는 watcher가 사용할 수 있습니다.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row # 결과를 사전처럼 접근 가능하게 함
        cursor = conn.cursor()

        select_sql = f'''
        SELECT task_id, target_file, status, start_time, end_time, message
        FROM {TABLE_NAME}
        WHERE task_id = ?;
        '''
        cursor.execute(select_sql, (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None # 결과를 딕셔너리로 반환

    except sqlite3.Error as e:
        print(f"Database error getting task status for {task_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_task_statuses(db_path=DB_FILE):
    """
    데이터베이스에 기록된 모든 Task의 상태 정보를 조회합니다.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        select_sql = f'''
        SELECT task_id, target_file, status, start_time, end_time, message
        FROM {TABLE_NAME}
        ORDER BY start_time DESC; -- 최신 Task 먼저 보이도록 정렬
        '''
        cursor.execute(select_sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows] # 결과를 딕셔너리 리스트로 반환

    except sqlite3.Error as e:
        print(f"Database error getting all task statuses: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_running_task_statuses(db_path=DB_FILE):
    """
    현재 실행 중인 Task(status = 'RUNNING')의 상태 정보를 조회합니다.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        select_sql = f'''
        SELECT task_id, target_file, status, start_time, end_time, message
        FROM {TABLE_NAME}
        WHERE status = ?;
        '''
        cursor.execute(select_sql, (STATUS_RUNNING,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except sqlite3.Error as e:
        print(f"Database error getting running task statuses: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- Example Usage (Demonstration) ---

if __name__ == '__main__':
    # --- Watcher Side Simulation ---

    print("--- Watcher Side Simulation ---")
    # 1. 데이터베이스 초기화 (watcher 시작 시 한 번)
    initialize_db()

    # 2. 새로운 파일 감지 및 Task 실행 (시뮬레이션)
    # 실제로는 subprocess 등을 사용하여 Task를 별도의 프로세스로 실행합니다.
    # 이때 task_id와 target_file을 인자로 넘겨줍니다.

    files_to_process = ["/path/to/file_A.txt", "/path/to/image_B.png", "/path/to/data_C.csv"]
    simulated_tasks = []

    for file in files_to_process:
        task_id = str(uuid.uuid4()) # watcher가 UUID 생성
        simulated_tasks.append({'task_id': task_id, 'target_file': file})
        print(f"Watcher: Detected file {file}. Assigned task_id: {task_id}. (Simulating task start...)")

        # --- Task Side Simulation (within the watcher's context for demonstration) ---
        # 실제로는 이 부분이 별도의 스크립트나 함수로 분리되어,
        # watcher가 subprocess.Popen 등으로 실행할 때 task_id와 file 경로를 인자로 받습니다.
        # Task는 시작하자마자 create_task_entry를 호출합니다.
        create_task_entry(task_id, file)
        print(f"  Task {task_id[:8]}: Entry created in DB.")
        # -----------------------------------------------------------------------------

    print("\n--- Watcher checking running tasks ---")
    running_tasks = get_running_task_statuses()
    print("Currently Running Tasks:")
    if running_tasks:
        for task in running_tasks:
            print(f"- ID: {task['task_id'][:8]}..., File: {task['target_file']}, Status: {task['status']}, Start: {task['start_time']}")
    else:
        print("No tasks currently running.")

    # 3. Task 완료 시 상태 업데이트 (시뮬레이션)
    # 실제 Task 코드가 작업을 마친 후 이 함수를 호출합니다.

    print("\n--- Task Side Simulation (Updating Status) ---")
    # Task A 완료 (성공)
    task_a_id = simulated_tasks[0]['task_id']
    print(f"  Task {task_a_id[:8]}: Simulating successful completion.")
    update_task_status(task_a_id, STATUS_SUCCESS, message="Processing successful.")

    # Task B 완료 (실패)
    task_b_id = simulated_tasks[1]['task_id']
    print(f"  Task {task_b_id[:8]}: Simulating failure.")
    update_task_status(task_b_id, STATUS_FAILED, message="Failed to process image format.")

    # Task C 아직 실행 중 (시뮬레이션 상)
    task_c_id = simulated_tasks[2]['task_id']
    print(f"  Task {task_c_id[:8]}: Still running...")
    # Task C는 아직 업데이트 안 함

    # 4. Watcher가 다시 상태 확인 (시뮬레이션)
    print("\n--- Watcher checking running tasks again ---")
    running_tasks = get_running_task_statuses()
    print("Currently Running Tasks:")
    if running_tasks:
        for task in running_tasks:
            print(f"- ID: {task['task_id'][:8]}..., File: {task['target_file']}, Status: {task['status']}, Start: {task['start_time']}")
    else:
        print("No tasks currently running.") # Task C가 RUNNING으로 남아있어야 정상

    # 5. Watcher가 모든 Task 이력 확인 (시뮬레이션)
    print("\n--- Watcher checking all task history ---")
    all_tasks = get_all_task_statuses()
    print("All Task History:")
    if all_tasks:
        for task in all_tasks:
             print(f"- ID: {task['task_id'][:8]}..., File: {task['target_file']}, Status: {task['status']}, Start: {task['start_time']}, End: {task['end_time']}, Msg: {task['message']}")
    else:
        print("No task history found.")

    # 6. Task C 완료 시뮬레이션 (성공)
    print(f"\n  Task {task_c_id[:8]}: Simulating successful completion.")
    update_task_status(task_c_id, STATUS_SUCCESS, message="Data processed okay.")

    # 7. Watcher가 마지막으로 모든 이력 확인 (시뮬레이션)
    print("\n--- Watcher checking all task history (final) ---")
    all_tasks = get_all_task_statuses()
    print("All Task History:")
    if all_tasks:
        for task in all_tasks:
             print(f"- ID: {task['task_id'][:8]}..., File: {task['target_file']}, Status: {task['status']}, Start: {task['start_time']}, End: {task['end_time']}, Msg: {task['message']}")
    else:
        print("No task history found.")

    # 예제 실행 후 DB 파일 삭제 (선택 사항)
    # if os.path.exists(DB_FILE):
    #    os.remove(DB_FILE)
    #    print(f"\nCleaned up {DB_FILE}")