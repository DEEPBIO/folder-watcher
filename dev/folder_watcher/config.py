# 요구사항: FR-0001, FR-0002, FR-0004
import configparser
import os
from pathlib import Path
import logging

# 실행 스크립트의 위치를 기준으로 프로젝트 루트 경로 계산
# __main__.py -> folder_watcher -> dev -> project_root
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

def get_config_templates(dev_mode=False):
    """실행 모드에 따라 다른 설정 템플릿을 반환합니다."""
    if dev_mode:
        # 개발 모드: 저장소 내의 test/demo 폴더를 절대 경로로 사용
        test_dir = PROJECT_ROOT / "dev" / "test"
        demo_dir = PROJECT_ROOT / "dev" / "demo"
        return f"""
[common]
tasks = 1
credential = {test_dir / 'cred'}
pids = {test_dir / 'pids'}
logs = {test_dir / 'logs'}

[0]
name = Dev Example Task
in = {demo_dir / 'input'}
done = {demo_dir / 'done'}
stop = {demo_dir / 'stop'}
app = /usr/bin/python3
param = -c "import time, sys; print(f'DEV MODE: Processing {{sys.argv[1]}}...'); time.sleep(5); print('Done.')"
interval = 2
"""
    else:
        # 배포 모드: 시스템 표준 경로 사용
        return f"""
[common]
tasks = 1
credential = /opt/folder-watcher/cred
pids = /var/run/folder-watcher/pids
logs = /var/log/folder-watcher

[0]
name = Example Task
in = /home/{os.getenv("USER", "your-username")}/folder-watcher-demo/input
done = /home/{os.getenv("USER", "your-username")}/folder-watcher-demo/done
stop = /home/{os.getenv("USER", "your-username")}/folder-watcher-demo/stop
app = /usr/bin/python3
param = -c "import time, sys; print(f'Processing {{sys.argv[1]}}...'); time.sleep(10); print('Done.')"
interval = 5
"""

def get_config_path() -> Path:
    return Path.home() / ".folder-watcher.ini"

def create_example_config(path: Path, dev_mode=False):
    logging.info(f"설정 파일이 없어 예시 파일을 생성합니다: {path}")
    config_template = get_config_templates(dev_mode)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(config_template)

def load_config(dev_mode=False) -> configparser.ConfigParser:
    config_path = get_config_path()
    if not config_path.exists():
        create_example_config(config_path, dev_mode)

    config = configparser.ConfigParser()
    try:
        config.read(config_path, encoding='utf-8')
    except configparser.Error as e:
        logging.critical(f"설정 파일 파싱 오류: {e}")
        raise
    return config