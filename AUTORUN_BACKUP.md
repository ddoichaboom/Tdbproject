# TDB 자동 실행 설정 복구 가이드

이 문서는 `main.py`를 사용하는 새로운 통합 자동 실행 방식(`tdb.service`)에서, 기존의 분리된 방식(`tdb-serial.service`, `tdb-gui.service`)으로 되돌리는 방법을 안내합니다.

## 1. 새로운 `tdb.service` 비활성화 및 중지

먼저 현재 사용 중인 `tdb.service`를 중지하고 비활성화합니다.

```bash
sudo systemctl disable --now tdb.service
```

## 2. 기존 서비스 재활성화

아래 명령어를 실행하여 기존의 두 서비스를 다시 활성화하고 시작합니다.

```bash
sudo systemctl enable --now tdb-serial.service
sudo systemctl enable --now tdb-gui.service
```

## 3. (참고) 기존 서비스 파일 내용

만약 서비스 파일(`tdb-serial.service`, `tdb-gui.service`)이 삭제되었을 경우, 아래 내용을 참고하여 `/etc/systemd/system/` 경로에 다시 생성할 수 있습니다.

### `/etc/systemd/system/tdb-serial.service`

```ini
[Unit]
Description=TDB Serial Reader
After=network-online.target
Wants=network-online.target

[Service]
User=tdb
WorkingDirectory=/home/tdb/Tdbproject
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/tdb/Tdbproject/.venv/bin/python -m hwserial.serial_reader
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

### `/etc/systemd/system/tdb-gui.service`

```ini
[Unit]
Description=TDB QR/Status GUI
After=graphical.target

[Service]
User=tdb
WorkingDirectory=/home/tdb/Tdbproject
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/tdb/.Xauthority
ExecStart=/home/tdb/Tdbproject/.venv/bin/python -m gui.qr_display
Restart=always
RestartSec=2

[Install]
WantedBy=graphical.target
```
