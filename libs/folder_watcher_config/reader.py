import json
import os
import logging
from functools import lru_cache

# Basic caching to avoid reloading the same config file repeatedly within a task run
@lru_cache(maxsize=4)
def _load_config_data(config_path):
    """Internal function to load config with caching."""
    if not os.path.exists(config_path):
        logging.error(f"[Task Config Lib] Config file not found: {config_path}")
        return None
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"[Task Config Lib] Failed to load/parse config {config_path}: {e}")
        return None

def get_config(config_path):
    """
    Loads the entire configuration. Tasks should use this cautiously.
    Args:
        config_path (str): Path to the main config.json file.
    Returns:
        dict: The configuration dictionary, or None on error.
    """
    return _load_config_data(config_path)

def get_task_specific_config(config_path, task_name):
    """
    Gets the specific configuration block for a given task name.
    Args:
        config_path (str): Path to the main config.json file.
        task_name (str): The name of the task requesting config.
    Returns:
        dict: The task-specific configuration, or an empty dict if not found/error.
    """
    config = _load_config_data(config_path)
    if config and 'task_specific_config' in config and task_name in config['task_specific_config']:
        return config['task_specific_config'][task_name]
    else:
        logging.warning(f"[Task Config Lib] No specific config found for task '{task_name}' in {config_path}")
        return {}

def get_database_path(config_path):
     """Gets only the database path from the config."""
     config = _load_config_data(config_path)
     return config.get('database_path') if config else None

# Example usage (if run directly)
if __name__ == '__main__':
    # Assume config.json is in the parent directory relative to this script
    script_dir = os.path.dirname(__file__)
    config_file_path = os.path.join(script_dir, '..', '..', 'config.json')
    print(f"Attempting to load config from: {config_file_path}")

    full_config = get_config(config_file_path)
    if full_config:
        print("\nFull Config:")
        # print(full_config) # Can be large
        print(f"- DB Path: {get_database_path(config_file_path)}")

        task_name = "Example Processing Task" # Example task name from config
        task_config = get_task_specific_config(config_file_path, task_name)
        print(f"\nConfig for task '{task_name}':")
        print(task_config)

        task_name_no_config = "NonExistentTask"
        task_config_none = get_task_specific_config(config_file_path, task_name_no_config)
        print(f"\nConfig for task '{task_name_no_config}':")
        print(task_config_none)
    else:
        print("Failed to load configuration.")