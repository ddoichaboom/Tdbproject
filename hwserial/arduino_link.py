import re, time
import serial
from serial.tools import list_ports

def autodetect_port():
    for p in list_ports.comports():
        if "Arduino" in (p.description or "") or "Arduino" in (p.manufacturer or ""):
            return p.device
    return None

def open_serial(baud_rate=9600, timeout=1):
    port = autodetect_port()
    if not port:
        raise IOError("Arduino not found")
    ser = serial.Serial(port, baud_rate, timeout=timeout)
    time.sleep(2) # Wait for Arduino to reset
    ser.flushInput()
    return ser

def read_uid_once(ser: serial.Serial):
    line = ser.readline().decode("ascii", "ignore").strip().upper()
    if re.fullmatch(r"^[0-9A-F]{8,}$", line):
        return line
    return None

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
    return _send_cmd_wait(ser, f"DISPENSE,{int(slot)},{int(count)}")

def send_raw(ser, line: str, timeout: float = 8.0):
    """명령 전송 후 OK/ERR 응답 1줄 수신. READY/빈줄 무시."""
    line = (line.strip() + "\n").encode("ascii", "ignore")
    ser.reset_input_buffer()  # 이전 명령의 늦게 온 OK를 싹 비움
    ser.write(line)
    ser.flush()
    t0 = time.time()
    while time.time() - t0 < timeout:
        if ser.in_waiting:
            resp = ser.readline().decode("ascii", "ignore").strip()
            if not resp or resp == "READY":
                continue
            return True, resp
        time.sleep(0.01)
    return False, "TIMEOUT"

def step_next(ser):
    """회전판을 다음 단계로 이동 (2.0~2.5s 소요)"""
    return send_raw(ser, "STEP,NEXT", timeout=4.0)

def step_home(ser):
    """회전판을 HOME 위치로 복귀 (최대 4.5s 소요)"""
    ok, resp = send_raw(ser, "HOME", timeout=6.0)
    if ok and resp:
        return ok, resp
    return send_raw(ser, "STEP,HOME", timeout=6.0)

def step_next_n(ser, n: int, gap_ms: int = 150):
    """
    STEP,NEXT를 n번 연속 수행. 중간 실패 시 즉시 중단.
    gap_ms: 각 스텝 사이 대기 시간 (밀리초)
    """
    n = max(0, int(n))
    for i in range(n):
        ok, msg = step_next(ser)
        if not ok:
            return False, f"{msg} (i={i+1}/{n})"
        if gap_ms > 0:
            time.sleep(gap_ms / 1000.0)
    return True, f"OK,STEP_NEXT_X{n}"

def jog(ser, direction: str, ms: int, speed: int = None):
    """
    회전판을 수동으로 조작 (긴급 복구용)
    direction: "F" (전진) or "B" (후진)
    ms: 동작 시간 (밀리초)
    speed: 속도 (0-100, 선택사항)
    """
    direction = str(direction).upper()
    if direction not in ("F", "B"):
        return False, "ERR,INVALID_DIRECTION"

    ms = max(100, min(15000, int(ms)))  # 안전 범위: 100ms ~ 15s

    if speed is None:
        cmd = f"JOG,{direction},{ms}"
    else:
        speed = max(0, min(100, int(speed)))  # 안전 범위: 0-100%
        cmd = f"JOG,{direction},{speed},{ms}"

    return send_raw(ser, cmd, timeout=max(8.0, ms / 1000.0 + 2.0))
