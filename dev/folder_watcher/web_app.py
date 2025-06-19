# 요구사항: FR-0013 ~ FR-0019, SR-0001
import logging
import os
import signal
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash
from .auth import login_required, check_credentials
from .config import get_config_path

# 웹앱과 다른 모듈이 공유할 전역 변수
app_config = None
pids_dir = None
logs_dir = None
credential_file = None
software_version = "1.0.0"

def create_app(config, credential_path):
    global app_config, pids_dir, logs_dir, credential_file
    app_config = config
    pids_dir = app_config.get('common', 'pids')
    logs_dir = app_config.get('common', 'logs')
    credential_file = credential_path

    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.secret_key = os.urandom(24)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if check_credentials(username, password, credential_file):
                session['logged_in'] = True
                flash('로그인되었습니다.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('잘못된 사용자 이름 또는 비밀번호입니다.', 'danger')
        return render_template('login.html', title="로그인")

    @app.route('/logout')
    def logout():
        session.pop('logged_in', None)
        flash('로그아웃되었습니다.', 'info')
        return redirect(url_for('login'))

    @app.route('/')
    @login_required
    def dashboard():
        # FR-0014: 작업 현황(실행중, 완료, 중단) 정보 표시
        status_data = []
        num_tasks = app_config.getint('common', 'tasks', fallback=0)
        
        running_tasks_map = {}
        if os.path.isdir(pids_dir):
            for pid_file in os.listdir(pids_dir):
                if pid_file.endswith('.pid'):
                    try:
                        with open(os.path.join(pids_dir, pid_file)) as f:
                            pid = int(f.read().strip())
                        running_tasks_map[pid_file.replace('.pid', '')] = pid
                    except (IOError, ValueError):
                        continue
        
        for i in range(num_tasks):
            task_id = str(i)
            if task_id in app_config:
                task = app_config[task_id]
                
                def get_files_from_dir(path):
                    if not os.path.isdir(path): return []
                    return os.listdir(path)

                task_status = {
                    'name': task['name'],
                    'running': [{'file': f, 'pid': p} for f, p in running_tasks_map.items()],
                    'done': get_files_from_dir(task['done'])[-20:],
                    'stop': get_files_from_dir(task['stop'])[-20:],
                    'in_folder': task['in'],
                    'done_folder': task['done'],
                    'stop_folder': task['stop'],
                }
                status_data.append(task_status)
        return render_template('dashboard.html', title="대시보드", status_data=status_data)

    @app.route('/stop_task/<int:pid>', methods=['POST'])
    @login_required
    def stop_task(pid):
        # FR-0013, FR-0015: 실행중인 특정 작업 중단
        try:
            os.kill(pid, signal.SIGTERM)
            flash(f"프로세스(PID: {pid})에 중단 신호를 보냈습니다.", 'success')
            logging.info(f"사용자가 웹 UI를 통해 프로세스 {pid}를 중단시켰습니다.")
        except ProcessLookupError:
            flash(f"프로세스(PID: {pid})를 찾을 수 없습니다. 이미 종료되었을 수 있습니다.", 'warning')
        except Exception as e:
            flash(f"프로세스 중단 중 오류 발생: {e}", 'danger')
            logging.error(f"프로세스 {pid} 중단 오류: {e}")
        return redirect(url_for('dashboard'))

    @app.route('/logs')
    @login_required
    def view_logs():
        # FR-0017: 이벤트 로그 표시
        log_files = []
        if os.path.isdir(logs_dir):
            log_files = sorted([f for f in os.listdir(logs_dir) if 'folder-watcher' in f], reverse=True)
        else:
            flash(f"로그 디렉토리를 찾을 수 없습니다: {logs_dir}", 'danger')
            
        selected_log = request.args.get('file', log_files[0] if log_files else None)
        log_content = ""
        if selected_log and selected_log in log_files:
            try:
                with open(os.path.join(logs_dir, selected_log), 'r', encoding='utf-8') as f:
                    log_content = "".join(f.readlines()[-500:]) # 성능을 위해 마지막 500줄만
            except Exception as e:
                log_content = f"로그 파일 읽기 오류: {e}"
        return render_template('logs.html', title="로그", log_files=log_files, selected_log=selected_log, log_content=log_content)

    @app.route('/config')
    @login_required
    def view_config():
        # FR-0018: 설정 표시
        config_path = str(get_config_path())
        config_content = ""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
        except Exception as e:
            config_content = f"설정 파일 읽기 오류: {e}"
        return render_template('config_view.html', title="설정 보기", content=config_content)

    @app.route('/info')
    @login_required
    def view_info():
        # FR-0019, CR-0002, CR-0007
        info = {
            "name": "Folder-Watcher",
            "version": software_version,
            "repository": "https://github.com/DEEPBIO/folder-watcher.git"
        }
        return render_template('info.html', title="정보", info=info)

    return app