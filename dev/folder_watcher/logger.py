# 요구사항: FR-0016, FR-0003
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

def setup_logging(log_folder: str):
    """시간 기반으로 로그 파일을 생성하고 관리하는 로거를 설정합니다."""
    try:
        # 디렉토리가 존재하지 않으면 생성
        if not os.path.isdir(log_folder):
             os.makedirs(log_folder, exist_ok=True)

        log_file_path = os.path.join(log_folder, "folder-watcher.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        handler = TimedRotatingFileHandler(
            log_file_path, when='W0', backupCount=13, encoding='utf-8'
        )
        handler.setFormatter(formatter)
        handler.suffix = "%Y-%m-%d.log"
        
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        if root_logger.hasHandlers():
            root_logger.handlers.clear()
        root_logger.addHandler(handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    except Exception as e:
        sys.stderr.write(f"로깅 설정 실패: {e}\n")
        sys.exit(1)