import time
import sys
import os
import signal
import logging
import argparse

# Assume libs are installed or in PYTHONPATH
# If running directly from repo root, PYTHONPATH might need adjustment
# export PYTHONPATH=$PYTHONPATH:./libs
try:
    from libs.folder_watcher_config import get_task_specific_config, get_database_path
    from libs.folder_watcher_status import update_status #, set_final_status (Not strictly needed by task in v0.3)
except ImportError:
    print("Error: Could not import folder_watcher libraries.")
    print("Ensure 'libs' directory is in PYTHONPATH or the libraries are installed.")
    sys.exit(1)

# Basic logging setup for the task
log_format = '%(asctime)s - %(levelname)s - TASK [%(process)d] - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)

terminate_signal_received = False

def signal_handler(signum, frame):
    """Handle termination signals gracefully."""
    global terminate_signal_received
    if not terminate_signal_received:
        terminate_signal_received = True
        logging.warning(f"Received signal {signum}. Initiating graceful shutdown...")
        # Don't call set_final_status here - main app handles 'Aborted' on termination
        # Just try to exit cleanly. The main app will detect the non-zero exit if needed or handle cleanup.
        # sys.exit(128 + signum) # Exit with signal code - might be complex for main app
        sys.exit(1) # Simple non-zero exit often indicates abnormal termination
    else:
        logging.warning("Multiple termination signals received. Exiting immediately.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Example Folder Watcher Task")
    parser.add_argument("--config", required=True, help="Path to the main config.json file")
    parser.add_argument("--input", required=True, help="Path to the input file to process")
    args = parser.parse_args()

    config_path = args.config
    input_file = args.input
    task_name = "Example Processing Task" # Task should know its own name or derive it

    logging.info(f"Starting task '{task_name}' for file: {input_file}")
    logging.info(f"Using configuration file: {config_path}")

    # --- Get Configuration ---
    db_path = get_database_path(config_path)
    task_config = get_task_specific_config(config_path, task_name)

    if not db_path:
        logging.error("Could not retrieve database path from config. Exiting.")
        sys.exit(1)

    processing_delay = task_config.get("processing_delay_seconds", 3)
    output_msg = task_config.get("output_message", "Task completed nominally.")

    logging.info(f"Task specific config: Delay={processing_delay}s, Message='{output_msg}'")

    # --- Register Signal Handlers ---
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler) # Handle Ctrl+C if run manually

    # --- Update Status: Running ---
    pid = str(os.getpid())
    update_success = update_status(db_path, input_file, status='Running', stage='Initialization', message='Task started', pid=pid)
    if not update_success:
        logging.warning("Failed to update initial 'Running' status in DB.")
        # Decide if task should continue or exit

    # --- Simulate Work ---
    try:
        # Stage 1
        logging.info("Starting processing stage 1...")
        update_status(db_path, input_file, stage='Stage 1 Processing', message='Working on step 1...')
        time.sleep(processing_delay / 2)
        if terminate_signal_received: return # Check after potentially long operations

        # Stage 2
        logging.info("Starting processing stage 2...")
        update_status(db_path, input_file, stage='Stage 2 Processing', message='Finishing up...')
        time.sleep(processing_delay / 2)
        if terminate_signal_received: return

        # --- Work Complete ---
        logging.info(f"Processing complete for file: {input_file}")
        # In v0.3, task just exits successfully. Main app moves to history.
        # Optional: Update message one last time before exit.
        update_status(db_path, input_file, message=f"Finalizing: {output_msg}")
        logging.info("Task finished successfully.")
        sys.exit(0) # Exit with 0 for success

    except Exception as e:
        logging.error(f"An error occurred during task execution: {e}", exc_info=True)
        # Update status with error before exiting (optional, main app will mark aborted anyway)
        update_status(db_path, input_file, message=f"Error: {e}")
        # In v0.3, task just exits non-zero. Main app moves to history as 'Aborted'.
        sys.exit(1) # Exit with non-zero for failure

if __name__ == "__main__":
    main()