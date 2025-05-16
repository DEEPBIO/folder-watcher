#!/usr/bin/env python3

import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileClosedEvent
import os

class FolderEventHandler(FileSystemEventHandler):
    """Handles file system events."""

    def __init__(self, callback, folder_config):
        self.callback = callback # Function to call when a valid event occurs
        self.folder_config = folder_config # Configuration for this specific folder
        logging.info(f"Handler initialized for folder: {self.folder_config.get('folder_path')}")

    def on_closed(self, event):
        """Called when a file opened for writing is closed."""
        if not event.is_directory:
            # Check if the file is directly in the monitored folder or handle recursively?
            # SDD doesn't specify recursion - assuming non-recursive for now.
            # file_dir = os.path.dirname(event.src_path)
            # monitored_dir = os.path.abspath(self.folder_config.get('folder_path'))
            # if os.path.abspath(file_dir) == monitored_dir:

            logging.info(f"File closed event: {event.src_path} in folder {self.folder_config.get('folder_name')}")
            # Pass relevant info to the callback
            task_details = {
                "task_name": self.folder_config.get("task_name"),
                "task_executable": self.folder_config.get("task_executable"),
                "folder_path": self.folder_config.get("folder_path"),
                "file_path": os.path.abspath(event.src_path), # Use absolute path
                # Add other relevant config if needed by the scheduler
            }
            self.callback(task_details)
            # else:
            #    logging.debug(f"Ignoring event in subfolder: {event.src_path}")

    def on_created(self, event):
         """Optional: Log creation event, but trigger on close."""
         if not event.is_directory:
            logging.debug(f"File created event: {event.src_path}")
            # Do not trigger task here, wait for on_closed

    # Add on_moved? What happens if a file is moved *into* the folder?
    # Watchdog might see it as on_created. Test this behaviour.

class WatcherManager:
    """Manages multiple watchdog observers."""

    def __init__(self, config, callback):
        self.config = config
        self.callback = callback # Callback function to handle detected files
        self.observers = []
        self._stopped = False

    def start(self):
        """Starts monitoring folders specified in the configuration."""
        self.stop() # Stop any existing observers first
        self._stopped = False
        self.observers = []
        folders_to_watch = self.config.get('folders', [])

        if not folders_to_watch:
            logging.warning("No folders configured for watching.")
            return

        for folder_conf in folders_to_watch:
            path = folder_conf.get('folder_path')
            is_enabled = folder_conf.get('enabled', False)

            if not path or not is_enabled:
                logging.info(f"Skipping disabled or path-missing folder config: {folder_conf.get('folder_name', 'N/A')}")
                continue

            if not os.path.isdir(path):
                logging.error(f"Configured folder path is not a valid directory: {path}. Skipping.")
                continue

            logging.info(f"Setting up watcher for: {path}")
            event_handler = FolderEventHandler(self.callback, folder_conf)
            observer = Observer()
            # recursive=False : Only watch the top-level directory
            # recursive=True : Watch directory and all subdirectories
            observer.schedule(event_handler, path, recursive=False)
            observer.start()
            self.observers.append(observer)
            logging.info(f"Observer started for {path}")

        logging.info(f"WatcherManager started with {len(self.observers)} observers.")
        # Keep the main thread alive if this runs independently
        # try:
        #     while not self._stopped:
        #         time.sleep(1)
        # except KeyboardInterrupt:
        #     self.stop()

    def stop(self):
        """Stops all observers."""
        self._stopped = True
        if not self.observers:
            return
        logging.info("Stopping WatcherManager...")
        for observer in self.observers:
            if observer.is_alive():
                observer.stop()
                observer.join() # Wait for thread termination
        self.observers = []
        logging.info("WatcherManager stopped.")

    def reload(self, new_config):
        """Stops existing watchers and starts new ones based on the new config."""
        logging.info("Reloading watcher configuration...")
        self.stop()
        self.config = new_config
        self.start()