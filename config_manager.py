#!/usr/bin/env python3

import json
import os
import logging

CONFIG_FILE = 'config.json'

def load_config(config_path=CONFIG_FILE):
    """Loads the configuration from the JSON file."""
    if not os.path.exists(config_path):
        logging.error(f"Configuration file not found at {config_path}")
        # Return a default empty structure or raise an error
        return {
            "database_path": "folder_watcher.db",
            "log_directory": "logs/",
            "max_concurrent_tasks": 1,
            "folders": [],
            "task_specific_config": {}
        }
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logging.info(f"Configuration loaded from {config_path}")
        return config
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {config_path}: {e}")
        raise # Re-raise the error to be handled by the caller
    except Exception as e:
        logging.error(f"Failed to load configuration from {config_path}: {e}")
        raise

def save_config(config_data, config_path=CONFIG_FILE):
    """Saves the configuration data to the JSON file."""
    try:
        # Create backup?
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        logging.info(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to save configuration to {config_path}: {e}")
        return False

def validate_config(config_data):
    """Performs basic sanity checks on the configuration data (SDD 0.3 - 9.2 Option A)."""
    errors = []
    # 1. Check basic structure and types (simple version)
    if not isinstance(config_data, dict):
        return ["Configuration must be a JSON object."]
    required_keys = ["database_path", "log_directory", "max_concurrent_tasks", "folders", "task_specific_config"]
    for key in required_keys:
        if key not in config_data:
            errors.append(f"Missing required configuration key: '{key}'")
    if not isinstance(config_data.get("max_concurrent_tasks"), int) or config_data.get("max_concurrent_tasks", 0) < 1:
        errors.append("'max_concurrent_tasks' must be a positive integer.")
    if not isinstance(config_data.get("folders"), list):
         errors.append("'folders' must be a list.")
    if not isinstance(config_data.get("task_specific_config"), dict):
         errors.append("'task_specific_config' must be an object.")

    if errors: return errors # Return early if basic structure is wrong

    # 2. Check path existence (relative to config file or absolute)
    # Note: This assumes relative paths are relative to where the app runs.
    # Consider resolving paths relative to the config file location if needed.
    db_path = config_data.get("database_path")
    log_dir = config_data.get("log_directory")

    # For paths, check if they exist or if their parent directory exists (for files/dirs to be created)
    if db_path and not os.path.exists(db_path) and not os.path.exists(os.path.dirname(db_path) or '.'):
         errors.append(f"Parent directory for database_path '{db_path}' does not exist.")
    if log_dir:
        # Ensure log directory exists, create if not
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
             errors.append(f"Could not create or access log_directory '{log_dir}': {e}")

    # 3. Check folder/task executable existence for enabled folders
    for i, folder_config in enumerate(config_data.get("folders", [])):
        if not isinstance(folder_config, dict):
            errors.append(f"Folder configuration at index {i} is not an object.")
            continue
        if folder_config.get("enabled", False): # Only check enabled folders
            folder_path = folder_config.get("folder_path")
            task_exec = folder_config.get("task_executable")

            if not folder_path or not os.path.isdir(folder_path):
                errors.append(f"Folder path '{folder_path}' for task '{folder_config.get('task_name')}' does not exist or is not a directory.")

            # Basic check for executable - split command and check first part
            if task_exec:
                exec_cmd_parts = task_exec.split()
                exec_path = exec_cmd_parts[0]
                # This check is basic: assumes executable is path/command, doesn't verify parameters
                # It also doesn't check *execute* permissions, only existence.
                # For 'python script.py', it checks 'python', which might not be desired.
                # A more robust check might involve `shutil.which()` or trying to resolve the path.
                # This basic check might need refinement based on expected executable formats.
                if not os.path.isfile(exec_path) and not shutil.which(exec_path):
                     # Add refinement here if needed, e.g., for python scripts
                     if exec_path.lower() == 'python' and len(exec_cmd_parts) > 1 and os.path.isfile(exec_cmd_parts[1]):
                         pass # Looks like 'python script.py', assume python exists and check script file
                     else:
                        errors.append(f"Task executable '{exec_path}' for task '{folder_config.get('task_name')}' not found or not a file.")
            else:
                 errors.append(f"Missing 'task_executable' for enabled folder '{folder_config.get('task_name')}'.")

    return errors

# Need to import shutil for shutil.which() used in validate_config
import shutil