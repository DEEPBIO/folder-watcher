# 요구사항: PR-0001, FR-0006, FR-0008, FR-0009, FR-0010, FR-0011, FR-0012
import logging
import os
import shlex
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

MAX_WORKERS = max(2, (os.cpu_count() or 1) - 2)

class TaskManager:
    def __init__(self, config):
        self.config = config
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix='TaskWorker')
        self.pids_dir = self.config.get('common', 'pids')
        logging.info(f"작업 관리자 초기화. 최대 동시 작업 수: {MAX_WORKERS}")

    def submit_task(self, task_id, file_path):
        self.executor.submit(self._execute_task, task_id, file_path)
        
    def _execute_task(self, task_id, file_path):
        task_config = self.config[task_id]
        file_name = os.path.basename(file_path)

        if file_name.startswith('.'):
            logging.info(f"숨김 파일 '{file_path}'은 건너뜁니다.")
            return

        pid_filename = f"{task_id}-{file_name}.pid"
        pid_file_path = os.path.join(self.pids_dir, pid_filename)

        if os.path.exists(pid_file_path):
            logging.warning(f"이미 처리 중인 작업이므로 건너뜁니다: {task_id} - {file_name}")
            return

        logging.info(f"작업 제출: [{task_config['name']}] 파일: {file_name}")
        process = None
        try:
            command = [task_config['app']] + shlex.split(task_config['param']) + [file_path]
            logging.info(f"[{task_config['name']}] 명령어 실행: {' '.join(command)}")
            
            process = subprocess.Popen(command)
            with open(pid_file_path, 'w') as f:
                f.write(str(process.pid))

            return_code = process.wait()
            
            if return_code == 0:
                destination = os.path.join(task_config['done'], file_name)
                shutil.move(file_path, destination)
                logging.info(f"[{task_config['name']}] 작업 성공: '{file_name}' -> '{destination}'")
            else:
                destination = os.path.join(task_config['stop'], file_name)
                shutil.move(file_path, destination)
                logging.warning(f"[{task_config['name']}] 작업 실패 (종료 코드 {return_code}): '{file_name}' -> '{destination}'")

        except Exception as e:
            logging.error(f"[{task_config['name']}] 작업 실행 중 예외 발생: {e}", exc_info=True)
            if os.path.exists(file_path):
                destination = os.path.join(task_config['stop'], file_name)
                shutil.move(file_path, destination)
                logging.warning(f"[{task_config['name']}] 예외 발생으로 파일 이동: '{file_name}' -> '{destination}'")
        finally:
            if os.path.exists(pid_file_path):
                os.remove(pid_file_path)
            
            interval = task_config.getint('interval', fallback=0)
            if interval > 0:
                time.sleep(interval)