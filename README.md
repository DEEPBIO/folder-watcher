# Folder-Watcher

요구사항 명세서에 따라 개발된 폴더 감시 및 자동 작업 처리 소프트웨어입니다.

---

## 👨‍💻 개발자를 위한 안내 (For Developers)

이 섹션은 소스 코드를 직접 수정하거나 빌드하려는 개발자를 위한 안내입니다.

### 개발 환경 설정
1.  **저장소 클론**
    ```bash
    git clone [https://github.com/DEEPBIO/folder-watcher.git](https://github.com/DEEPBIO/folder-watcher.git)
    cd folder-watcher/
    ```

2.  **가상 환경(fw) 생성 및 활성화**
    프로젝트의 루트 디렉토리 `folder-watcher/` 에서 가상 환경을 생성하는 것을 권장합니다.
    ```bash
    # 가상 환경 생성
    python3 -m venv fw

    # 가상 환경 활성화
    source fw/bin/activate
    ```

3.  **개발 의존성 설치 (CR-0005)**
    `dev/` 디렉토리의 `requirements.txt` 파일을 사용하여 개발 및 빌드에 필요한 모듈을 설치합니다.
    ```bash
    pip install -r dev/requirements.txt
    ```

### 개발 중 실행 (`--dev` 모드)
-   개발 및 테스트 시에는 반드시 `--dev` 플래그를 사용하여 저장소 내의 테스트 환경으로 실행해야 합니다.
-   프로젝트 루트 디렉토리에서 아래 명령어를 실행합니다.
    ```bash
    # dev 모드로 실행
    python3 -m dev.folder_watcher --dev
    ```
-   **최초 실행 시**:
    - 사용자의 홈 디렉토리(`~/`)에 개발용 `.folder-watcher.ini` 파일이 생성됩니다. 이 파일은 저장소 내의 `dev/test/` 및 `dev/demo/` 폴더를 활용하도록 설정되어 있습니다.

### `.deb` 패키지 빌드 프로세스 (CR-0006)
1.  **PyInstaller로 실행 파일 빌드**
    프로젝트 루트 디렉토리에서 아래 명령어를 실행하여 의존성이 포함된 단일 실행 파일을 생성합니다.
    ```bash
    # dev 디렉토리 안의 소스를 빌드
    pyinstaller --noconfirm --onefile --name folder-watcher-executable dev/folder_watcher/__main__.py
    ```

2.  **빌드 결과물 복사**
    생성된 실행 파일을 `prod/package/` 안의 목적지로 옮깁니다.
    ```bash
    # 실행 파일 복사
    mv dist/folder-watcher-executable prod/package/opt/folder-watcher/
    ```

3.  **Debian 패키지 빌드**
    프로젝트 루트 디렉토리에서 `dpkg-b` 명령어로 `.deb` 파일을 빌드합니다.
    ```bash
    dpkg-b prod/package/ folder-watcher_1.0.0_amd64.deb
    ```

---

## 👩‍💼 사용자를 위한 안내 (For Users)

### 설치
생성된 `folder-watcher_1.0.0_amd64.deb` 파일을 사용하여 소프트웨어를 설치합니다.
```bash
sudo dpkg -i folder-watcher_1.0.0_amd64.deb
```
설치가 완료되면 필요한 시스템 디렉토리, 권한, 기본 인증 파일이 자동으로 설정됩니다.

### 실행 (CR-0004)
-   Ubuntu의 '프로그램 표시' 메뉴에서 "Folder Watcher"를 찾아 실행합니다.
-   또는 터미널에서 아래 명령어로 직접 실행할 수 있습니다.
    ```bash
    /opt/folder-watcher/folder-watcher-executable
    ```

### 최초 설정 (FR-0001)
1.  소프트웨어를 처음 실행하면 홈 디렉토리에 `~/.folder-watcher.ini` 파일이 자동으로 생성됩니다.
2.  이 파일은 `/var/log`, `/var/run` 등 시스템 표준 경로를 기본값으로 가집니다.
3.  파일을 열어 `[0]` 섹션의 `in`, `done`, `stop` 폴더 경로를 실제 사용할 절대 경로로 수정해야 합니다. **이 폴더들은 사용자가 직접 생성해야 합니다.**
