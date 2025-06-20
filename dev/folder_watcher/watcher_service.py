# 요구사항: CR-0005, FR-0005, FR-0006, FR-0007
import logging
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .task_manager import TaskManager

class TaskEventHandler(FileSystemEventHandler):
    def __init__(self, task_id, task_config, task_manager):
        self.task_id = task_id
        self.task_config = task_config
        self.task_manager = task_manager
        self.logger = logging.getLogger(self.__class__.__name__)

    def on_closed(self, event):
        if not event.is_directory:
            self.logger.info(f"파일 감지됨: {event.src_path} (작업: {self.task_config['name']})")
            self.task_manager.submit_task(self.task_id, event.src_path)

class WatcherService:
    def __init__(self, config, task_manager):
        self.config = config
        self.task_manager = task_manager
        self.observer = Observer()
        self.logger = logging.getLogger(self.__class__.__name__)

    def start(self):
        num_tasks = self.config.getint('common', 'tasks', fallback=0)
        for i in range(num_tasks):
            task_id = str(i)
            if task_id in self.config:
                task_config = self.config[task_id]
                
                for folder_key in ['in', 'done', 'stop']:
                    folder_path = task_config[folder_key]
                    if not os.path.isdir(folder_path):
                        self.logger.warning(f"설정된 폴더를 찾을 수 없습니다: '{folder_path}'.")
                
                self.logger.info(f"[{task_config['name']}] 시작 시 기존 파일 처리 중...")
                try:
                    for filename in os.listdir(task_config['in']):
                        file_path = os.path.join(task_config['in'], filename)
                        if os.path.isfile(file_path):
                            self.task_manager.submit_task(task_id, file_path)
                except FileNotFoundError:
                     self.logger.error(f"유입 폴더를 찾을 수 없어 기존 파일을 처리할 수 없습니다: {task_config['in']}")

                event_handler = TaskEventHandler(task_id, task_config, self.task_manager)
                self.observer.schedule(event_handler, task_config['in'], recursive=False)
                self.logger.info(f"폴더 감시 시작: '{task_config['in']}' (작업: {task_config['name']})")

        self.observer.start()
        self.logger.info("모든 감시 서비스가 시작되었습니다.")

    def stop(self):
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        self.logger.info("모든 감시 서비스가 중단되었습니다.")