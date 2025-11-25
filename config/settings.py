# /home/tdb/Tdbproject/config/settings.py
import os
from pathlib import Path

# --- add: load config/.env into os.environ (if exists) ---
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if not line or line.startswith("#") or "=" not in line: 
            continue
        k,v = line.split("=",1)
        os.environ.setdefault(k.strip(), v.strip())

def _env(name: str, default: str | None = None) -> str | None:
    # TDB_ 접두 환경변수 우선 사용
    return os.getenv(f"TDB_{name}", default)

# 서버/QR
SERVER_BASE_URL = _env("SERVER_BASE_URL", "http://127.0.0.1:8000")  # 예: http://ec2-xx:3000
QR_BASE_URL     = _env("QR_BASE_URL", SERVER_BASE_URL)

# 기기 식별
MACHINE_ID     = _env("MACHINE_ID", "MACHINE-0001")
DEVICE_UID     = _env("DEVICE_UID", MACHINE_ID)   # 없으면 MACHINE_ID로 대체
QR_MACHINE_KEY = _env("QR_MACHINE_KEY", "uid")
QR_KIT_KEY     = _env("QR_KIT_KEY", "k_uid")

# 시리얼
SERIAL_PORT  = os.getenv("TDB_SERIAL_PORT", None) # /dev/serial/by-id/... 권장, None=자동탐지
BAUDRATE     = int(_env("BAUDRATE", "9600"))
READ_TIMEOUT = float(_env("READ_TIMEOUT", "1.0"))

# 동작 옵션
DRY_RUN = False
UID_COOLDOWN_SEC = float(_env("UID_COOLDOWN_SEC", "2.0"))
HEARTBEAT_SEC    = int(_env("HEARTBEAT_SEC", "300"))
