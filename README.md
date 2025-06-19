# Folder-Watcher

요구사항 명세서에 따라 개발된 폴더 감시 및 자동 작업 처리 소프트웨어입니다.

---

## 👨‍💻 개발자를 위한 안내 (For Developers)

이 섹션은 소스 코드를 직접 수정하거나 빌드하려는 개발자를 위한 안내입니다.

### 개발 환경 설정
1.  **저장소 클론 및 `dev` 디렉토리로 이동**
    ```bash
    git clone [https://github.com/DEEPBIO/folder-watcher.git](https://github.com/DEEPBIO/folder-watcher.git)
    cd folder-watcher/dev/
    ```

2.  **가상 환경(fw) 생성 및 활성화**
    ```bash
    # 가상 환경 생성
    python3 -m venv fw

    # 가상 환경 활성화
    source fw/bin/activate
    ```

3.  **개발 의존성 설치 (CR-0005)**
    `requirements.txt` 파일을 사용하여 개발 및 빌드에 필요한 모듈을 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```

### 개발 중 실행
-   가상 환경이 활성화된 상태에서 아래 명령어로 애플리케이션을 실행하여 테스트할 수 있습니다.
    ```bash
    # 기본값(/opt/folder-watcher/cred) 사용
    python -m folder_watcher

    # credential 파일 위치를 직접 지정
    python -m folder_watcher --credential /path/to/your/cred
    ```
-   **참고**: 개발 모드에서 기본값으로 실행 시, 애플리케이션은 `/opt/folder-watcher/cred` 파일을 읽으려고 시도합니다. 테스트를 위해 해당 파일을 수동으로 생성해야 할 수 있습니다.
    ```bash
    sudo mkdir -p /opt/folder-watcher
    sudo sh -c 'echo "admin:password123" > /opt/folder-watcher/cred'
    sudo chmod 644 /opt/folder-watcher/cred
    ```

### `.deb` 패키지 빌드 프로세스 (CR-0006)
1.  **PyInstaller로 실행 파일 빌드**
    `dev` 디렉토리에서 아래 명령어를 실행하여 의존성이 포함된 단일 실행 파일을 생성합니다.
    ```bash
    pyinstaller --noconfirm --onefile --name folder-watcher-executable folder_watcher/__main__.py
    ```

2.  **빌드 결과물 및 `cred` 파일 복사**
    생성된 실행 파일을 `prod/package/` 안의 목적지로 옮기고, `cred` 파일의 기본값을 생성합니다.
    ```bash
    # 실행 파일 복사
    mv dist/folder-watcher-executable ../prod/package/opt/folder-watcher/

    # 기본 cred 파일 생성
    echo "admin:password123" > ../prod/package/opt/folder-watcher/cred
    ```

3.  **Debian 패키지 빌드**
    프로젝트 루트 디렉토리에서 `dpkg-b` 명령어로 `.deb` 파일을 빌드합니다. (버전은 `DEBIAN/control` 파일과 일치해야 합니다)
    ```bash
    # 빌드할 디렉토리는 prod/package/ 입니다.
    dpkg-b prod/package/ folder-watcher_1.0.0_amd64.deb
    ```

---

## 👩‍💼 사용자를 위한 안내 (For Users)

### 설치
생성된 `folder-watcher_1.0.0_amd64.deb` 파일을 사용하여 소프트웨어를 설치합니다. 이 과정에서 root 권한이 필요합니다.
```bash
sudo dpkg -i folder-watcher_1.0.0_amd64.deb
```
설치가 완료되면 필요한 시스템 디렉토리와 권한이 자동으로 설정됩니다.

### 실행 (CR-0004)
-   Ubuntu의 '프로그램 표시' 메뉴에서 "Folder Watcher"를 찾아 실행합니다. (기본 credential 파일 사용)
-   또는 터미널에서 아래 명령어로 직접 실행할 수 있습니다.
    ```bash
    # 기본 credential 파일(/opt/folder-watcher/cred) 사용
    /opt/folder-watcher/folder-watcher-executable
    
    # 다른 credential 파일을 사용하려는 경우
    /opt/folder-watcher/folder-watcher-executable --credential /path/to/your/custom_cred
    ```

### 최초 설정 (FR-0001)
1.  소프트웨어를 처음 실행하면 홈 디렉토리에 `~/.folder-watcher.ini` 파일이 자동으로 생성됩니다.
2.  이 파일을 열어 사용자의 환경에 맞게 `in`, `done`, `stop` 등의 폴더 경로를 **절대 경로**로 수정해야 합니다. 이 폴더들은 사용자가 직접 생성해야 합니다.
