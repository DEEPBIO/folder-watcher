# 요구사항: SR-0001, SR-0002
import os
from functools import wraps
from flask import request, redirect, url_for, session
import logging

def check_credentials(username, password, config) -> bool:
    """설정 파일에 지정된 경로의 cred 파일을 기반으로 사용자 인증을 확인합니다."""
    try:
        credential_path = config.get('common', 'credential')
    except Exception:
        logging.error("설정 파일에서 credential 경로를 찾을 수 없습니다.")
        return False

    if not os.path.exists(credential_path):
        logging.error(f"인증 파일을 찾을 수 없습니다: {credential_path}")
        return False
    try:
        with open(credential_path, 'r', encoding='utf-8') as f:
            stored_user, stored_pass = f.read().strip().split(':', 1)
        return username == stored_user and password == stored_pass
    except Exception as e:
        logging.error(f"인증 파일 읽기 오류 ({credential_path}): {e}")
        return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function