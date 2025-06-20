# 요구사항: FR-0013 ~ FR-0019, SR-0001
import logging
import os
import sys
import signal
import time
import shutil
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from .auth import login_required, check_credentials
from .config import get_config_path

app_config = None
pids_dir = None
logs_dir = None
software_version = "1.0.0"

def resource_path(relative_path):
    """Get the absolute path to the resource, works for development and production."""
    try:
        base_path = sys._MEIPASS    # For PyInstaller
    except Exception:
        base_path = '..'
    return os.path.join(base_path, relative_path)

def create_app(config):
    global app_config, pids_dir, logs_dir
    app_config = config
    pids_dir = app_config.get('common', 'pids')
    logs_dir = app_config.get('common', 'logs')

    app = Flask(__name__, template_folder=resource_path('templates'), static_folder=resource_path('static'))
    app.secret_key = os.urandom(24)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if check_credentials(username, password, app_config):
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
        return render_template('dashboard.html', title="대시보드")
        
    @app.route('/api/status')
    @login_required
    def api_status():
        all_files = []
        num_tasks = app_config.getint('common', 'tasks', fallback=0)
        
        if os.path.isdir(pids_dir):
            for pid_filename in os.listdir(pids_dir):
                if pid_filename.endswith('.pid'):
                    try:
                        parts = pid_filename.rsplit('.pid', 1)[0].split('-', 1)
                        if len(parts) != 2: continue
                        
                        task_id, original_filename = parts
                        task_name = app_config.get(task_id, 'name', fallback=f"Task {task_id}")
                        
                        pid_file_path = os.path.join(pids_dir, pid_filename)
                        with open(pid_file_path) as f:
                            pid = int(f.read().strip())
                        
                        mtime = os.path.getmtime(pid_file_path)
                        elapsed_seconds = time.time() - mtime
                        
                        all_files.append({
                            "task_id": task_id,
                            "task_name": task_name,
                            "file_name": original_filename,
                            "status": "실행중",
                            "pid": pid,
                            "elapsed_seconds": elapsed_seconds
                        })
                    except (IOError, ValueError, IndexError):
                        continue
        
        for i in range(num_tasks):
            task_id = str(i)
            if task_id in app_config:
                task = app_config[task_id]
                task_name = task.get('name', f"Task {task_id}")

                def get_files(folder, status):
                    if not os.path.isdir(folder): return
                    for filename in os.listdir(folder)[-20:]:
                        if filename.startswith('.'):
                            continue
                        all_files.append({
                            "task_id": task_id,
                            "task_name": task_name,
                            "file_name": filename,
                            "status": status,
                            "pid": None,
                            "elapsed_seconds": None
                        })
                
                get_files(task['done'], "완료")
                get_files(task['stop'], "중단")
                
        return jsonify(all_files)

    @app.route('/api/retry', methods=['POST'])
    @login_required
    def retry_task():
        # 중단된 작업 재시도 기능
        data = request.get_json()
        task_id = data.get('task_id')
        file_name = data.get('file_name')

        if not task_id or not file_name:
            return jsonify({"success": False, "error": "Missing task_id or file_name"}), 400

        try:
            task_config = app_config[task_id]
            stop_path = os.path.join(task_config['stop'], file_name)
            in_path = os.path.join(task_config['in'], file_name)

            if os.path.exists(stop_path):
                shutil.copy(stop_path, in_path)
                os.unlink(stop_path)
                logging.info(f"재시도 요청: '{file_name}'을(를) '{task_config['in']}' 폴더로 이동했습니다.")
                return jsonify({"success": True})
            else:
                return jsonify({"success": False, "error": "File not found in stop folder"}), 404
        except Exception as e:
            logging.error(f"재시도 중 오류 발생: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/stop_task/<int:pid>', methods=['POST'])
    @login_required
    def stop_task(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            logging.error(f"프로세스 중단 중 오류 발생: {e}")
        return jsonify({"success": True})

    @app.route('/logs')
    @login_required
    def view_logs():
        log_files = []
        if os.path.isdir(logs_dir):
            log_files = sorted([f for f in os.listdir(logs_dir) if 'folder-watcher' in f], reverse=True)
        
        selected_log = request.args.get('file', log_files[0] if log_files else None)
        log_content = ""
        if selected_log and selected_log in log_files:
            try:
                with open(os.path.join(logs_dir, selected_log), 'r', encoding='utf-8') as f:
                    log_content = "".join(f.readlines()[-500:])
            except Exception as e:
                log_content = f"로그 파일 읽기 오류: {e}"
        return render_template('logs.html', title="로그", log_files=log_files, selected_log=selected_log, log_content=log_content)

    @app.route('/config')
    @login_required
    def view_config():
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
        info = {
            "name": "Folder-Watcher", "version": software_version,
            "repository": "https://github.com/DEEPBIO/folder-watcher.git"
        }
        return render_template('info.html', title="정보", info=info)

    return app