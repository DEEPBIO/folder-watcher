# 요구사항: FR-0001, FR-0002, FR-0004
import configparser
import os
from pathlib import Path
import logging

# FR-0001: 예시 설정 파일을 코드 내에 포함
CONFIG_TEMPLATE = '''
# Folder Watcher 설정 파일
[common]
# FR-0004: 활성화할 작업의 개수 (0부터 시작하므로 1은 작업 [0] 하나를 의미)
tasks = 1
# FR-0003: 프로세스 ID(PID) 관리 폴더 위치 (절대 경로). dpkg 설치 시 생성됩니다.
pids = /var/run/folder-watcher/pids
# FR-0003: 로그 파일 폴더 위치 (절대 경로). dpkg 설치 시 생성됩니다.
logs = /var/log/folder-watcher

# --- 작업 설정 (아래 번호는 0부터 시작) ---
[0]
name = Example Task
# FR-0002, FR-0006: 유입 폴더 위치 (절대 경로)
in = /home/{USERNAME}/folder-watcher-demo/input
# FR-0002, FR-0009: 완료 폴더 위치 (절대 경로)
done = /home/{USERNAME}/folder-watcher-demo/done
# FR-0002, FR-0010: 중단 폴더 위치 (절대 경로)
stop = /home/{USERNAME}/folder-watcher-demo/stop
# FR-0002, FR-0006: 실행할 작업 어플리케이션 위치 (절대 경로)
app = /usr/bin/python3
# FR-0002, FR-0006: 작업 어플리케이션에 전달할 파라미터 목록 (공백으로 구분)
param = -c "import time, sys; print(f'Processing {{sys.argv[1]}}...'); time.sleep(10); print('Done.')"
# FR-0002, FR-0008: 작업 처리 후 대기 시간 (초)
interval = 5
'''.replace("{USERNAME}", os.getenv("USER", "your-username"))

def get_config_path() -> Path:
    # FR-0001: 실행한 사용자의 홈 디렉토리에서 .folder-watcher.ini 설정 파일을 찾음
    return Path.home() / ".folder-watcher.ini"

def create_example_config(path: Path):
    # FR-0001: 설정 파일이 없으면 예시 설정 파일을 생성
    logging.info(f"설정 파일이 없어 예시 파일을 생성합니다: {path}")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(CONFIG_TEMPLATE)

def load_config() -> configparser.ConfigParser:
    config_path = get_config_path()
    if not config_path.exists():
        create_example_config(config_path)

    config = configparser.ConfigParser()
    try:
        config.read(config_path, encoding='utf-8')
    except configparser.Error as e:
        logging.critical(f"설정 파일 파싱 오류: {e}")
        raise

    # FR-0002: 모든 경로가 절대 경로인지 검증
    return config