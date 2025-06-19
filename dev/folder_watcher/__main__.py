# CR-0001: Ubuntu에서 동작하는 Python 어플리케이션
import threading
import logging
import sys
import argparse

from folder_watcher.config import load_config
from folder_watcher.logger import setup_logging
from folder_watcher.task_manager import TaskManager
from folder_watcher.watcher_service import WatcherService
from folder_watcher.web_app import create_app

def main():
    # 실행 인자 파서 설정
    parser = argparse.ArgumentParser(description="Folder-Watcher: A tool to watch folders and execute tasks.")
    parser.add_argument(
        '--credential',
        type=str,
        default='/opt/folder-watcher/cred',
        help='Path to the credential file. Defaults to /opt/folder-watcher/cred.'
    )
    args = parser.parse_args()

    try:
        config = load_config()
        log_folder = config.get('common', 'logs')
        setup_logging(log_folder)
        
    except Exception as e:
        sys.stderr.write(f"초기화 실패: {e}\n")
        sys.exit(1)

    logging.info("Folder-Watcher를 시작합니다.")
    logging.info(f"사용자 인증 파일: {args.credential}")

    task_manager = TaskManager(config)
    watcher_service = WatcherService(config, task_manager)
    watcher_thread = threading.Thread(target=watcher_service.start, name="WatcherThread", daemon=True)
    watcher_thread.start()

    app = create_app(config, credential_path=args.credential)
    
    logging.info("웹 UI를 http://0.0.0.0:5000 에서 시작합니다.")
    app.run(host='0.0.0.0', port=5000, debug=False)

    watcher_service.stop()
    logging.info("Folder-Watcher를 종료합니다.")


if __name__ == "__main__":
    main()