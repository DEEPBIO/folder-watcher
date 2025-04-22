# Folder Watcher

A Python application designed to monitor specified folders for new files and execute predefined tasks on them. It provides a web UI for monitoring task status, viewing history, and managing configuration.

## Key Features

* **Folder Monitoring:** Watches configured folders for new files (triggered upon file write completion).
* **Task Execution:** Launches user-defined executable tasks (scripts, programs) for each new file.
* **Web Interface:** Provides a web UI built with Flask for:
    * Viewing currently running tasks (status, stage, message, timestamps).
    * Viewing historical task records (completed, aborted).
    * Aborting running tasks (sends SIGTERM).
    * Editing the application's JSON configuration dynamically.
* **Configurable Concurrency:** Limits the number of tasks running simultaneously (`max_concurrent_tasks` in config).
* **Database Storage:** Uses SQLite to store active task status, task history, and user credentials.
* **JSON Configuration:** Main application settings, folder paths, and task details are managed via a `config.json` file.
* **Task Communication Libraries:** Provides simple Python libraries (`folder_watcher_config`, `folder_watcher_status`) for tasks to read configuration and update their status in the database.
* **Authentication:** Basic single-user authentication for the web UI.

## Architecture Overview

The application uses a multi-process architecture:

1.  **Main Process (`app.py`):** Runs the Flask web server and the `watchdog` file system monitor. It schedules tasks, manages concurrency, and updates the database when tasks complete or fail.
2.  **Task Executor Process:** Launched by the main process via `multiprocessing` / `subprocess` for each file detected. This process executes the user-defined task.
3.  **User Task Executable:** The actual script or program defined in the configuration that performs work on the file. It uses the provided Python libraries to interact with the system (read config, update status).
4.  **SQLite Database (`database.py`):** Stores active task state, historical records, and user credentials.
5.  **JSON Configuration (`config.json`, `config_manager.py`):** Central place for settings.
6.  **Python Libraries (`libs/`):** Helper modules provided to simplify task development.

*(You can insert your architecture diagram PNG here if desired)*

## Technology Stack

* **Backend:** Python 3
* **Web Framework:** Flask
* **File Monitoring:** Watchdog
* **Database:** SQLite3
* **Concurrency:** Multiprocessing, Subprocess, Threading
* **Process Handling:** psutil
* **Authentication Helpers:** Werkzeug
* **Frontend:** HTML, CSS, JavaScript (basic), Jinja2 (Templating)

## Project Structure

```
folder-watcher/
├── app.py                   # Main Flask application, watcher logic, task scheduling
├── config_manager.py        # Handles loading/saving/validation of config.json
├── database.py              # Database interaction logic (SQLite)
├── monitor.py               # File system monitoring class using watchdog
├── auth.py                  # Authentication logic (hashing, login)
├── init_db.py               # Script to initialize the database
├── config.json              # Default/Example configuration file
├── requirements.txt         # Python package dependencies
│
├── libs/                    # Task communication libraries (installable or PYTHONPATH)
│   ├── folder_watcher_config/ # Config reader lib
│   └── folder_watcher_status/ # Status updater lib
│
├── static/                  # Static files (CSS, JS)
│   └── style.css
│
├── templates/               # Flask/Jinja2 HTML templates
│   ├── base.html
│   ├── login.html
│   ├── status_history.html
│   └── configuration.html
│
└── tasks/                   # Example task directory (User-provided)
    └── example_task.py
```

## Configuration

The application is configured using `config.json`. Key fields:

* `database_path`: Path to the SQLite database file.
* `log_directory`: Path to the directory for the main application's operational logs.
* `max_concurrent_tasks`: Maximum number of tasks allowed to run simultaneously.
* `folders`: A list of objects, each defining a folder to watch:
    * `folder_path`: The path to the directory to monitor.
    * `folder_name`: A display name for the UI.
    * `task_name`: A name for the associated task.
    * `task_executable`: The command to execute the task (e.g., `python ./tasks/my_task.py`, `/usr/bin/my_script.sh`).
    * `enabled`: `true` to enable monitoring for this folder, `false` to disable.
* `task_specific_config`: An object where keys are `task_name`s and values are objects containing parameters specific to that task (accessed via the `folder_watcher_config` library).

The configuration can be edited directly in the file or via the "Configuration" tab in the web UI (requires restart or dynamic reload logic).

## Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd folder-watcher
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Linux/macOS:
    source venv/bin/activate
    # On Windows:
    .\venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    # You may also need: pip install psutil
    ```

4.  **Initialize the database:**
    This creates the SQLite database file and sets up the necessary tables and the initial admin user.
    ```bash
    python init_db.py
    ```
    * **Default Admin Credentials:** `admin` / `Admin12#$#`
    * **IMPORTANT:** Change the default password immediately after the first login! (Currently requires manual DB update or adding a password change feature).

5.  **Configure `config.json`:**
    * Review and edit `config.json`.
    * Ensure the `folder_path` directories exist.
    * Ensure the `task_executable` commands are correct and point to valid scripts/programs.
    * Create any necessary task scripts (see `tasks/example_task.py`).

## Running the Application

1.  **Ensure virtual environment is active.**
2.  **Set PYTHONPATH if running tasks from source:** If your tasks need to import from the `libs` directory and you haven't installed them as packages, you might need to add the `libs` directory's parent (the project root) to your `PYTHONPATH`.
    ```bash
    # On Linux/macOS:
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    # On Windows (Command Prompt):
    # set PYTHONPATH=%PYTHONPATH%;%CD%
    # On Windows (PowerShell):
    # $env:PYTHONPATH += ";${pwd}"
    ```
3.  **Start the Flask application:**
    ```bash
    python app.py
    ```
4.  **Access the Web UI:** Open your web browser and go to `http://127.0.0.1:5000`.
5.  **Login** with the admin credentials.

*(Note: For production, use a proper WSGI server like Gunicorn or Waitress instead of Flask's development server. See Deployment Notes.)*

## Usage

* **Login:** Use the credentials (`admin` / `Admin12#$#` initially).
* **Task Status & History:** View currently running tasks and completed/aborted tasks. Use the "Abort" button to send a SIGTERM signal to a running task.
* **Configuration:** View and edit the `config.json` content. Submitting saves the file and attempts to reload the configuration (including restarting folder watchers). Errors during validation or saving will be displayed.

## Developing Custom Tasks

1.  **Write your task script/executable** (e.g., a Python script, a shell script).
2.  **Configure it:** Add a folder entry in `config.json` pointing to your script via `task_executable`. Add any task-specific parameters under `task_specific_config`.
3.  **Task Interface:**
    * The task will be launched with command-line arguments: `--config <path_to_config.json> --input <path_to_target_file>`.
    * **(Python Tasks)** Use the provided libraries:
        * `from folder_watcher_config import get_database_path, get_task_specific_config` to read settings.
        * `from folder_watcher_status import update_status` to update the task's stage and status message in the database while running. Use the `file_path` argument as the identifier.
    * **Exit Codes:** Exit with `0` for successful completion. Exit with a non-zero code for failure/abortion. The main application monitors the exit code to determine the final status ('Completed' or 'Aborted').
    * **Signal Handling:** Implement a signal handler for `SIGTERM` to allow graceful shutdown when the "Abort" button is pressed.
    * **Logging:** Tasks should handle their own detailed logging if needed. Standard output/error are not currently captured by `folder-watcher`.
4.  **Example:** See `tasks/example_task.py` for a Python task demonstrating library usage and signal handling.

## Security Notes

* **CHANGE THE DEFAULT PASSWORD (`Admin12#$#`) IMMEDIATELY!**
* The application currently uses basic authentication and session management. Ensure the `app.secret_key` is set to a strong, unique value (ideally via environment variables) in production.
* Run tasks with the least privilege necessary. Be extremely cautious about what tasks are configured, as they execute commands on the server. Validate configuration carefully.
* Protect the `config.json` and `.db` file with appropriate file system permissions.
* For production deployments, **always run behind a reverse proxy (like Nginx) configured for HTTPS (SSL/TLS)** to encrypt traffic.

## Deployment Notes

* Use a production-grade WSGI server like Gunicorn or Waitress instead of `flask run`. Example with Gunicorn: `gunicorn --bind 0.0.0.0:5000 app:app`
* Use a process manager like `systemd` or `supervisor` to manage the application process (and potentially the watcher service if run separately).
* Configure a reverse proxy like Nginx to handle incoming requests, serve static files, and provide HTTPS termination.

## Contributing

(Add contribution guidelines here if the project is open source - e.g., pull request process, issue reporting).

## License

None
