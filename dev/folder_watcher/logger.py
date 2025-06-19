# 요구사항: FR-0016, FR-0003
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

def setup_logging(log_folder: str):
    """시간 기반으로 로그 파일을 생성하고 관리하는 로거를 설정합니다."""
    try:
        # FR-0003: 설치 스크립트가 디렉토리를 생성하므로, 여기서는 존재 여부만 확인.
        if not os.path.isdir(log_folder):
             raise FileNotFoundError(f"Log directory not found: {log_folder}")

        # FR-0016: 로그 파일 이름 형식 및 로테이션 정책
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