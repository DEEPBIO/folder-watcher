import sys
import signal
import logging
import time
import os
import threading
import multiprocessing
import subprocess
import queue # For queuing tasks if max_concurrent is reached
import psutil # To check process status and terminate
import sqlite3
import json
import traceback

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.exceptions import Unauthorized

# Local imports
import database
import config_manager
from monitor import WatcherManager
from auth import verify_user

# --- Configuration & Globals ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(threadName)s] %(message)s')
CONFIG_FILE = 'config.json'
config = config_manager.load_config(CONFIG_FILE)
db_path = config.get('database_path', 'folder_watcher.db')

app = Flask(__name__)
# IMPORTANT: Change this secret key for production!
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_very_insecure_default_secret_key')

# --- Concurrency Management ---
# Using multiprocessing.Manager for shared state if needed, but simple counts might suffice
# Using simple lock and counter for active processes
process_lock = threading.Lock()
active_processes = {} # Store mapping: file_path -> multiprocessing.Process object
task_queue = queue.Queue() # Queue for pending tasks

# --- Watcher Setup ---
watcher_manager = None
watcher_thread = None

def handle_new_file(task_details):
    """Callback function for WatcherManager."""
    logging.info(f"Received new file notification: {task_details['file_path']}")
    # Add task to the queue for processing by the scheduler thread
    if database.add_initial_task(db_path, task_details):
         task_queue.put(task_details)
    else:
         logging.error(f"Skipping task for {task_details['file_path']} due to DB error or duplicate.")


def launch_task(task_details):
    """Launches the task executable in a separate process."""
    file_path = task_details['file_path']
    executable_cmd = task_details['task_executable'] # e.g., "python ./tasks/example_task.py"
    config_path_abs = os.path.abspath(CONFIG_FILE) # Pass absolute path to config

    # Construct command arguments
    # Using lists for subprocess is generally safer
    command = executable_cmd.split() # Basic split, might need shlex for complex commands
    command.extend(['--config', config_path_abs, '--input', file_path])

    logging.info(f"Launching command: {' '.join(command)}")

    try:
        # Start the process
        # Use start_new_session=True on POSIX to make it easier to kill the whole process group later if needed
        process = subprocess.Popen(command, shell=False, start_new_session=True) # Avoid shell=True
        pid = process.pid
        logging.info(f"Task '{task_details['task_name']}' launched for file '{file_path}' with PID {pid}")

        # Update DB with PID (use the status updater logic, maybe refactor later)
        conn = database.get_db_connection(db_path)
        try:
            conn.execute('UPDATE active_tasks SET executor_pid = ? WHERE file_path = ?', (str(pid), file_path))
            conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Failed to update PID {pid} for {file_path}: {e}")
        finally:
            conn.close()

        return process # Return the Popen object

    except FileNotFoundError:
        error_msg = f"Executable not found: {command[0]}"
        logging.error(error_msg)
        database.log_launch_failure_to_history(db_path, task_details, error_msg)
        return None
    except Exception as e:
        error_msg = f"Failed to launch task: {e}"
        logging.error(error_msg, exc_info=True)
        database.log_launch_failure_to_history(db_path, task_details, error_msg)
        return None


def task_scheduler_worker():
    """Worker thread to process the task queue and manage concurrency."""
    logging.info("Task scheduler worker thread started.")
    global active_processes
    max_tasks = config.get('max_concurrent_tasks', 1)

    while True:
        try:
            # Check for completed tasks
            with process_lock:
                completed_files = []
                for file_path, process_info in active_processes.items():
                    proc_obj = process_info['process']
                    return_code = proc_obj.poll() # Non-blocking check

                    if return_code is not None: # Process finished
                        logging.info(f"Task for {file_path} (PID {proc_obj.pid}) finished with exit code {return_code}.")
                        final_status = 'Completed' if return_code == 0 else 'Aborted'
                        # Retrieve last message? Might be tricky. Rely on task to update before exit.
                        # For now, just use a generic message based on exit code.
                        final_message = f"Process exited with code {return_code}."
                        if database.move_task_to_history(db_path, file_path, final_status, final_message):
                            completed_files.append(file_path)
                        else:
                            logging.error(f"Failed to move completed task {file_path} to history.")
                            # Keep it in active_processes? Or force remove? Decide on error handling.
                            completed_files.append(file_path) # Remove anyway to avoid loop

                # Remove completed tasks from tracking
                for file_path in completed_files:
                    del active_processes[file_path]
                    logging.debug(f"Removed completed task {file_path} from active processes.")

            # Check if we can launch a new task
            can_launch = False
            with process_lock:
                if len(active_processes) < max_tasks:
                    can_launch = True

            if can_launch and not task_queue.empty():
                try:
                    task_details = task_queue.get_nowait() # Non-blocking get
                    logging.info(f"Dequeued task for file: {task_details['file_path']}")

                    # Check again for concurrency within the lock before launching
                    with process_lock:
                         if len(active_processes) < max_tasks:
                             launched_process = launch_task(task_details)
                             if launched_process:
                                 active_processes[task_details['file_path']] = {
                                     'process': launched_process,
                                     'task_name': task_details['task_name']
                                     # Add start time etc. if needed for monitoring here
                                 }
                                 logging.info(f"Active processes: {len(active_processes)}/{max_tasks}")
                             else:
                                 # Launch failed, error already logged to history by launch_task
                                 logging.error(f"Launch failed for {task_details['file_path']}. Not adding to active processes.")
                         else:
                             # Re-queue if concurrency limit reached just before launch
                             logging.warning(f"Concurrency limit reached just before launch. Re-queuing {task_details['file_path']}")
                             task_queue.put(task_details)

                except queue.Empty:
                    pass # No tasks waiting
                except Exception as e:
                    logging.error(f"Error in scheduler loop processing queue: {e}", exc_info=True)

            time.sleep(1) # Check queue/processes every second

        except Exception as e:
            logging.error(f"Critical error in task_scheduler_worker: {e}", exc_info=True)
            time.sleep(5) # Avoid tight loop on critical error

# --- Flask Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if verify_user(db_path, username, password):
            session['username'] = username # Store username in session
            flash('Login successful!', 'success')
            return redirect(url_for('status_history'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None) # Remove username from session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Decorator to require login
from functools import wraps
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    # Redirect to the main status page
    return redirect(url_for('status_history'))

@app.route('/status')
@login_required
def status_history():
    # This page shows both status and history as per SDD 0.3 / UI 5.1
    return render_template('status_history.html')

@app.route('/api/status')
@login_required
def api_status():
    tasks = database.get_active_tasks(db_path)
    # Convert Row objects to plain dicts for JSON serialization
    tasks_list = [dict(task) for task in tasks]
    return jsonify(tasks_list)

@app.route('/api/history')
@login_required
def api_history():
    # Add pagination/filtering parameters later (e.g., ?page=1&limit=50)
    limit = request.args.get('limit', 100, type=int)
    tasks = database.get_task_history(db_path, limit=limit)
    tasks_list = [dict(task) for task in tasks]
    return jsonify(tasks_list)

@app.route('/config', methods=['GET', 'POST'])
@login_required
def configuration():
    global config, watcher_manager # Allow modification of global config and watcher
    if request.method == 'POST':
        try:
            # Get raw JSON data from form field (e.g., a textarea)
            new_config_str = request.form['config_json']
            new_config_data = json.loads(new_config_str)

            # Validate the new configuration
            validation_errors = config_manager.validate_config(new_config_data)
            if validation_errors:
                 flash(f"Configuration validation failed: {'; '.join(validation_errors)}", 'danger')
                 # Pass the invalid string back to the template to display in the editor
                 return render_template('configuration.html', config_json=new_config_str)

            # Save the validated config
            if config_manager.save_config(new_config_data, CONFIG_FILE):
                flash('Configuration saved successfully. Reloading watchers...', 'success')
                # Reload config in memory and restart watchers
                config = new_config_data
                if watcher_manager:
                     watcher_manager.reload(config) # Trigger watcher reload
                else:
                     # Handle case where watcher wasn't running? Start it?
                     logging.warning("Configuration saved, but watcher manager was not running.")

                # Update globals derived from config if necessary (e.g., max_tasks for scheduler)
                global max_tasks
                max_tasks = config.get('max_concurrent_tasks', 1)
                # May need more sophisticated updates if scheduler logic depends heavily on other configs

            else:
                flash('Error saving configuration file.', 'danger')

        except json.JSONDecodeError:
            flash('Invalid JSON format submitted.', 'danger')
            return render_template('configuration.html', config_json=request.form.get('config_json', '')) # Show invalid json back
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
            logging.error(f"Error handling config POST: {e}", exc_info=True)

        # Redirect to GET to show the potentially updated config
        return redirect(url_for('configuration'))

    # GET request: Load current config and display it
    current_config_str = json.dumps(config, indent=2)
    return render_template('configuration.html', config_json=current_config_str)


@app.route('/api/abort/<path:file_path>', methods=['POST'])
@login_required
def api_abort_task(file_path):
    logging.info(f"Received request to abort task for file: {file_path}")
    # Need to find the process associated with this file_path
    # The PID is stored in the DB, but we also need the Process object if using multiprocessing directly,
    # or just the PID if using subprocess. Our current scheduler uses subprocess.

    pid_str = database.get_task_pid(db_path, file_path)

    if not pid_str:
        return jsonify({"success": False, "message": "Task not found or PID not recorded."}), 404

    try:
        pid = int(pid_str)
        logging.info(f"Attempting to send SIGTERM to PID {pid} for file {file_path}")

        # Use psutil for more robust process handling
        if not psutil.pid_exists(pid):
             logging.warning(f"PID {pid} does not exist. Task might have already finished.")
             # Maybe clean up the DB entry if the process is gone but entry remains?
             # Force move to history?
             database.move_task_to_history(db_path, file_path, 'Aborted', 'Process not found during abort.')
             return jsonify({"success": True, "message": f"Process PID {pid} not found. Marked as aborted."})

        process_to_kill = psutil.Process(pid)
        # Send SIGTERM (graceful shutdown)
        # On Windows, SIGTERM is tricky. terminate() is preferred.
        process_to_kill.terminate()
        logging.info(f"Sent SIGTERM/terminate() to PID {pid}")

        # Optional: Wait a short period and send SIGKILL if it hasn't terminated
        # try:
        #    process_to_kill.wait(timeout=5) # Wait 5 seconds
        #    logging.info(f"Process {pid} terminated gracefully.")
        # except psutil.TimeoutExpired:
        #    logging.warning(f"Process {pid} did not terminate after 5s. Sending SIGKILL.")
        #    process_to_kill.kill() # Force kill

        # Note: The scheduler thread should detect the non-zero exit code
        # and move the task to history as 'Aborted'. Sending the signal is enough.
        return jsonify({"success": True, "message": f"Sent termination signal to PID {pid}."})

    except ValueError:
         return jsonify({"success": False, "message": "Invalid PID format found in database."}), 500
    except psutil.NoSuchProcess:
        logging.warning(f"Process with PID {pid_str} not found during abort attempt (race condition?).")
        database.move_task_to_history(db_path, file_path, 'Aborted', 'Process disappeared during abort.')
        return jsonify({"success": True, "message": f"Process PID {pid_str} disappeared. Marked as aborted."})
    except psutil.AccessDenied:
        logging.error(f"Permission denied trying to terminate PID {pid_str}.")
        return jsonify({"success": False, "message": "Permission denied to terminate process."}), 500
    except Exception as e:
        logging.error(f"Error aborting task for {file_path} (PID {pid_str}): {e}", exc_info=True)
        return jsonify({"success": False, "message": f"An error occurred: {e}"}), 500


# --- Application Startup and Shutdown ---

def start_watcher():
    global watcher_manager
    logging.info("Starting Watcher Manager...")
    watcher_manager = WatcherManager(config, handle_new_file)
    watcher_manager.start()
    logging.info("Watcher Manager started.")

def shutdown_watcher(signum=None, frame=None):
    """Gracefully shut down the watcher and scheduler."""
    logging.info("Shutdown signal received. Stopping services...")
    if watcher_manager:
        watcher_manager.stop()
    # Need a way to signal the scheduler thread to stop
    # e.g., using an event or checking a global flag
    # Also need to wait for active processes? Or just signal them?
    # This part needs refinement for graceful shutdown.
    logging.info("Exiting application.")
    sys.exit(0)


if __name__ == '__main__':
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_watcher)
    signal.signal(signal.SIGTERM, shutdown_watcher)

    # Start the task scheduler worker thread
    scheduler_thread = threading.Thread(target=task_scheduler_worker, name="TaskScheduler", daemon=True)
    scheduler_thread.start()

    # Start the file watcher in a separate thread
    # Delay start slightly maybe?
    start_watcher()
    # watcher_thread = threading.Thread(target=start_watcher, name="FileWatcher", daemon=True)
    # watcher_thread.start()


    # Run Flask app (use host='0.0.0.0' to be accessible externally)
    # debug=False for production/when running watchdog in separate thread
    # Use Waitress or Gunicorn for production instead of Flask's dev server
    logging.info("Starting Flask development server...")
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

    # Note: Running watchdog and Flask in the same process like this can be complex.
    # For production, consider:
    # 1. Running Flask with Gunicorn/Waitress.
    # 2. Running the watcher/scheduler as a separate background service (using `python app.py worker` mode?)
    #    that communicates with the Flask app (e.g., via DB or Redis).
    # This example combines them for simplicity but has limitations.