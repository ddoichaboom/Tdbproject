#/home/tdb/Tdbproject/serial/arduino_link.py

import re, time
import serial
from serial.tools import list_ports
from config import settings

HEX_UID = re.compile(r"^[0-9A-F]{8,}$")

def autodetect_port():
    for p in list_ports.comports():
        text = f"{p.description or ''} {p.manufacturer or ''}".lower()
        if "arduino" in text or "wch" in text or "usb serial" in text:
            return p.device
    for cand in ("/dev/ttyACM0", "/dev/ttyUSB0"):
        try:
            open(cand).close()
            return cand
        except Exception:
            pass
    return None

def open_serial():
    import serial.tools.list_ports as lp
    port = settings.SERIAL_PORT
    if not port:
        # 간단 자동탐지
        for p in lp.comports():
            desc = (p.description or "").lower()
            mfg  = (p.manufacturer or "").lower()
            if "arduino" in desc or "arduino" in mfg:
                port = p.device
                break
        if not port:
            port = "/dev/ttyACM0"

    ser = serial.Serial(
        port, settings.BAUDRATE,
        timeout=settings.READ_TIMEOUT,
        write_timeout=2,
    )

    # 보드 리셋 후 READY 드레인
    t0 = time.time()
    while time.time() - t0 < 3.0:
        if ser.in_waiting:
            line = ser.readline().decode("ascii", "ignore").strip()
            if line == "READY":
                break
        else:
            time.sleep(0.01)
    ser.reset_input_buffer()
    return ser

def read_uid_once(ser: serial.Serial):
    line = ser.readline().decode("ascii", "ignore").strip().upper()
    return line if HEX_UID.fullmatch(line) else None

def _send_cmd_wait(ser: serial.Serial, cmd: str, timeout=5.0):
    if not cmd.endswith("\n"):
        cmd += "\n"
    ser.write(cmd.encode("ascii"))
    ser.flush()
    t0 = time.time()
    while time.time() - t0 < timeout:
        line = ser.readline().decode("ascii", "ignore").strip()
        if not line:
            continue
        if line.startswith("OK,"):
            return True, line
        if line.startswith("ERR,"):
            return False, line
    return False, "ERR,TIMEOUT"

def dispense(ser, slot: int, count: int):
    # 한 알당 약 3.0s (1s+0.5s+1s+0.5s) + 여유
    est = 3.0 * int(count) + 1.0   # 초
    to = max(5.0, est)             # 최소 5초
    return send_raw(ser, f"DISPENSE,{int(slot)},{int(count)}", timeout=to)


def home(ser: serial.Serial, timeout=5.0):
    return _send_cmd_wait(ser, "HOME", timeout)

def step_next(ser):
    # 2.0~2.5s + 여유
    return send_raw(ser, "STEP,NEXT", timeout=4.0)

def step_home(ser):
    # 최대 4.5s + 여유
    ok, resp = send_raw(ser, "HOME", timeout=6.0)
    if ok and resp:
        return ok, resp
    return send_raw(ser, "STEP,HOME", timeout=6.0)

def send_raw(ser, line: str, timeout: float = 8.0):
    """명령 전송 후 OK/ERR 응답 1줄 수신. READY/빈줄 무시."""
    line = (line.strip() + "\n").encode("ascii", "ignore")
    ser.reset_input_buffer()             # 이전 명령의 늦게 온 OK를 싹 비움
    ser.write(line); ser.flush()
    t0 = time.time()
    while time.time() - t0 < timeout:
        if ser.in_waiting:
            resp = ser.readline().decode("ascii", "ignore").strip()
            if not resp or resp == "READY":
                continue
            return True, resp
        time.sleep(0.01)
    return False, "TIMEOUT"


def jog(ser, direction: str, ms: int, speed: int | None = None):
    d = direction.strip().upper()[0]
    if d not in ("F", "B"):
        return False, "BAD_DIR"
    ms = int(ms)
    cmd = f"JOG,{d},{ms}" if speed is None else f"JOG,{d},{int(speed)},{ms}"
    return send_raw(ser, cmd)


def step_next_n(ser, n: int, gap_ms: int = 150):
    """
    STEP,NEXT를 n번 연속 수행. 중간 실패 시 즉시 중단.
    """
    n = max(0, int(n))
    for i in range(n):
        ok, msg = step_next(ser)
        if not ok:
            return False, f"{msg} (i={i+1}/{n})"
        if gap_ms > 0:
            time.sleep(gap_ms / 1000.0)
    return True, f"OK,STEP_NEXT_X{n}"