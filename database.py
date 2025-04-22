#!/usr/bin/env python3

import sqlite3
import datetime
import os
import logging

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection(db_path):
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(db_path, check_same_thread=False) # check_same_thread=False needed for multi-threaded Flask/Watchdog access
    conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
    return conn

def init_db(db_path):
    """Initializes the database schema."""
    if os.path.exists(db_path):
        logging.warning(f"Database '{db_path}' already exists. Skipping initialization.")
        # Consider adding logic here if you need to migrate schemas
        # return

    logging.info(f"Initializing database schema in '{db_path}'...")
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        # Active Tasks Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            folder_path TEXT NOT NULL,
            file_path TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            current_stage TEXT,
            message TEXT,
            start_time TEXT,
            last_update_time TEXT,
            executor_pid TEXT
        )
        ''')
        logging.info("Table 'active_tasks' created or already exists.")

        # Task History Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            folder_path TEXT NOT NULL,
            file_path TEXT NOT NULL,
            final_status TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            final_message TEXT
        )
        ''')
        logging.info("Table 'task_history' created or already exists.")

        # Users Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        ''')
        logging.info("Table 'users' created or already exists.")

        conn.commit()
        logging.info("Database schema initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database initialization failed: {e}")
        conn.rollback()
    finally:
        conn.close()

def add_initial_task(db_path, task_details):
    """Adds a new task to the active_tasks table with 'Pending' status."""
    conn = get_db_connection(db_path)
    try:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn.execute('''
            INSERT INTO active_tasks (task_name, folder_path, file_path, status, start_time, last_update_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            task_details['task_name'],
            task_details['folder_path'],
            task_details['file_path'],
            'Pending',
            now,
            now
        ))
        conn.commit()
        logging.info(f"Added pending task for file: {task_details['file_path']}")
        return True
    except sqlite3.IntegrityError:
         logging.error(f"File path '{task_details['file_path']}' already exists in active tasks.")
         return False
    except sqlite3.Error as e:
        logging.error(f"Failed to add initial task for {task_details['file_path']}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def move_task_to_history(db_path, file_path, final_status, final_message=""):
    """Moves a task from active_tasks to task_history."""
    conn = get_db_connection(db_path)
    try:
        with conn: # Use context manager for automatic commit/rollback
            # Fetch active task details
            active_task = conn.execute(
                'SELECT task_name, folder_path, start_time FROM active_tasks WHERE file_path = ?',
                (file_path,)
            ).fetchone()

            if not active_task:
                logging.warning(f"No active task found for file path '{file_path}' to move to history.")
                return False

            end_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # Insert into history
            conn.execute('''
                INSERT INTO task_history (task_name, folder_path, file_path, final_status, start_time, end_time, final_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                active_task['task_name'],
                active_task['folder_path'],
                file_path,
                final_status,
                active_task['start_time'],
                end_time,
                final_message
            ))

            # Delete from active tasks
            conn.execute('DELETE FROM active_tasks WHERE file_path = ?', (file_path,))
            logging.info(f"Moved task for file '{file_path}' to history with status '{final_status}'.")
            return True

    except sqlite3.Error as e:
        logging.error(f"Failed to move task '{file_path}' to history: {e}")
        # Transaction is automatically rolled back by context manager on exception
        return False
    # Connection is automatically closed when 'with' block exits, even on error

def log_launch_failure_to_history(db_path, task_details, error_message):
    """Directly logs a task launch failure to the history table."""
    conn = get_db_connection(db_path)
    try:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn.execute('''
            INSERT INTO task_history (task_name, folder_path, file_path, final_status, start_time, end_time, final_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_details['task_name'],
            task_details['folder_path'],
            task_details['file_path'],
            'Aborted', # Treat launch failure as Aborted
            now,       # Use current time as start/end
            now,
            f"Task launch failed: {error_message}"
        ))
        conn.commit()
        logging.error(f"Logged launch failure for task '{task_details['task_name']}' on file '{task_details['file_path']}'.")
    except sqlite3.Error as e:
        logging.error(f"Failed to log launch failure to history: {e}")
        conn.rollback()
    finally:
        conn.close()


# --- Functions for Flask App to Read Data ---

def get_active_tasks(db_path):
    conn = get_db_connection(db_path)
    tasks = conn.execute('SELECT * FROM active_tasks ORDER BY start_time ASC').fetchall()
    conn.close()
    return tasks

def get_task_history(db_path, limit=100): # Add limit/pagination
    conn = get_db_connection(db_path)
    # Add filtering/sorting options here later
    tasks = conn.execute('SELECT * FROM task_history ORDER BY end_time DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return tasks

def get_task_pid(db_path, file_path):
    """Gets the PID for an active task."""
    conn = get_db_connection(db_path)
    pid_row = conn.execute('SELECT executor_pid FROM active_tasks WHERE file_path = ?', (file_path,)).fetchone()
    conn.close()
    return pid_row['executor_pid'] if pid_row and pid_row['executor_pid'] else None