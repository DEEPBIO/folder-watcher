import threading
import logging
import sys
import argparse

# 경로 문제를 피하기 위해 패키지 이름을 직접 지정
from dev.folder_watcher.config import load_config
from dev.folder_watcher.logger import setup_logging
from dev.folder_watcher.task_manager import TaskManager
from dev.folder_watcher.watcher_service import WatcherService
from dev.folder_watcher.web_app import create_app

def main():
    parser = argparse.ArgumentParser(description="Folder-Watcher: A tool to watch folders and execute tasks.")
    parser.add_argument(
        '--dev',
        action='store_true',
        help='Run in development mode using local test/ and demo/ directories.'
    )
    args = parser.parse_args()

    try:
        config = load_config(dev_mode=args.dev)
        log_folder = config.get('common', 'logs')
        setup_logging(log_folder)
        
    except Exception as e:
        sys.stderr.write(f"초기화 실패: {e}\n")
        sys.exit(1)

    logging.info(f"Folder-Watcher를 시작합니다. (모드: {'개발' if args.dev else '배포'})")

    task_manager = TaskManager(config)
    watcher_service = WatcherService(config, task_manager)
    watcher_thread = threading.Thread(target=watcher_service.start, name="WatcherThread", daemon=True)
    watcher_thread.start()

    app = create_app(config)
    
    logging.info("웹 UI를 http://0.0.0.0:5000 에서 시작합니다.")
    app.run(host='0.0.0.0', port=5000, debug=args.dev)

    watcher_service.stop()
    logging.info("Folder-Watcher를 종료합니다.")

if __name__ == "__main__":
    main()