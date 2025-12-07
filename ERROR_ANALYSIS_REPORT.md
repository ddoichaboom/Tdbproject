# TDB 프로젝트 오류 및 예외 처리 점검 보고서

**작성일**: 2025-11-27
**점검 범위**: Python 클라이언트, Arduino 펌웨어, GUI, 설정

---

## 📊 점검 결과 요약

| 구분 | 상태 | 위험도 | 조치 필요 |
|------|------|--------|----------|
| **시리얼 통신** | ⚠️ 부분 양호 | 🟡 중간 | 일부 개선 |
| **API 통신** | ✅ 양호 | 🟢 낮음 | - |
| **GUI 스레드** | ⚠️ 주의 | 🟡 중간 | 검증 필요 |
| **설정/환경변수** | ⚠️ 주의 | 🟡 중간 | 개선 권장 |
| **리소스 관리** | ⚠️ 주의 | 🟡 중간 | 개선 필요 |
| **Arduino 펌웨어** | ⚠️ 부분 양호 | 🟡 중간 | 일부 개선 |

---

## 🔴 발견된 잠재적 오류 및 개선 사항

### 1. 시리얼 통신 관련

#### 🔴 문제 1-1: 시리얼 포트 열기 실패 시 복구 불가

**위치**: `hwserial/serial_reader.py:309-314`

**현재 코드**:
```python
try:
    ser = open_serial(baud_rate=9600)
except Exception as e:
    loge(f"[ERR] Serial open failed: {e}")
    if adapter: adapter.notify_error(f"시리얼 포트 열기 실패: {e}")
    return  # ❌ 바로 종료, 재시도 없음
```

**문제점**:
- Arduino 연결 실패 시 프로그램이 바로 종료됨
- 일시적 연결 문제 시 복구 불가능
- 재부팅 전까지 시스템 사용 불가

**개선 방안**:
```python
MAX_RETRIES = 3
retry_delay = 5

for attempt in range(MAX_RETRIES):
    try:
        ser = open_serial(baud_rate=9600)
        break  # 성공
    except Exception as e:
        loge(f"[ERR] Serial open failed (attempt {attempt+1}/{MAX_RETRIES}): {e}")
        if attempt < MAX_RETRIES - 1:
            time.sleep(retry_delay)
        else:
            # 최종 실패
            if adapter:
                adapter.notify_error(f"시리얼 연결 실패. Arduino를 확인하세요.")
            return
```

**우선순위**: 🟡 중간

---

#### 🟡 문제 1-2: 시리얼 타임아웃 후 자동 복구 없음

**위치**: `hwserial/arduino_link.py:26-40`

**현재 코드**:
```python
def _send_cmd_wait(ser: serial.Serial, cmd: str, timeout=5.0):
    # ... 명령 전송 ...
    while time.time() - t0 < timeout:
        line = ser.readline().decode("ascii", "ignore").strip()
        if line.startswith("OK,"):
            return True, line
        if line.startswith("ERR,"):
            return False, line
    return False, "ERR,TIMEOUT"  # ❌ 타임아웃 후 복구 시도 없음
```

**문제점**:
- 타임아웃 발생 시 시리얼 버퍼가 꼬일 수 있음
- 다음 명령이 이전 응답을 받을 가능성

**개선 방안**:
```python
def _send_cmd_wait(ser: serial.Serial, cmd: str, timeout=5.0):
    # 명령 전송 전 버퍼 클리어
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # ... 기존 로직 ...

    if timeout_occurred:
        ser.reset_input_buffer()  # 타임아웃 후 버퍼 정리
        return False, "ERR,TIMEOUT"
```

**우선순위**: 🟢 낮음 (이미 `send_raw()`에는 구현됨)

---

### 2. API 통신 관련

#### ✅ 양호: 재시도 메커니즘 구현됨

**위치**: `services/api_client.py:10-15`

```python
retry = Retry(total=3, connect=3, read=3, backoff_factor=0.5,
              status_forcelist=(500, 502, 503, 504))
```

**평가**: ✅ 네트워크 오류 시 자동 재시도 잘 구현됨

---

#### 🟡 문제 2-1: 오프라인 리포트 파일 크기 제한 없음

**위치**: `hwserial/serial_reader.py:107-139`

**현재 코드**:
```python
def store_offline(payload: dict):
    # ... 파일에 계속 추가만 함 ...
    f.write(json.dumps(payload) + "\n")
    # ❌ 파일 크기 제한 없음
```

**문제점**:
- 서버 장기 다운 시 `offline_reports.jsonl` 파일 무한 증가
- 디스크 공간 부족 가능성
- 라즈베리파이 SD 카드 수명 단축

**개선 방안**:
```python
MAX_OFFLINE_REPORTS = 1000
MAX_FILE_SIZE_MB = 10

def store_offline(payload: dict):
    offline_file = Path("data/offline_reports.jsonl")

    # 파일 크기 확인
    if offline_file.exists() and offline_file.stat().st_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        # 오래된 것 삭제 (FIFO)
        with open(offline_file, 'r') as f:
            lines = f.readlines()
        with open(offline_file, 'w') as f:
            f.writelines(lines[-MAX_OFFLINE_REPORTS:])

    # 추가
    with open(offline_file, 'a') as f:
        f.write(json.dumps(payload) + "\n")
```

**우선순위**: 🟡 중간

---

### 3. GUI 및 스레드 안전성

#### 🟡 문제 3-1: GUI 업데이트 시 스레드 안전성 미검증

**위치**: `gui/gui_app.py:157-158`

**현재 코드**:
```python
def ui_call(self, func, *args, **kwargs):
    self.after(0, lambda: func(*args, **kwargs))
```

**문제점**:
- 폴링 스레드에서 GUI 업데이트 시 `after()` 사용
- 일반적으로 안전하지만, 예외 발생 시 처리 없음

**개선 방안**:
```python
def ui_call(self, func, *args, **kwargs):
    def safe_call():
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"[GUI_ERROR] {func.__name__}: {e}")
            import traceback
            traceback.print_exc()

    self.after(0, safe_call)
```

**우선순위**: 🟡 중간

---

#### 🟡 문제 3-2: 폴링 스레드 종료 시 리소스 정리 불완전

**위치**: `main.py:82-108`

**현재 코드**:
```python
def poll_server_data():
    time.sleep(1)
    while not stop_polling.is_set():
        # ... 폴링 ...
        time.sleep(10)
# ❌ 종료 시 cleanup 없음
```

**문제점**:
- 프로그램 종료 시 스레드가 즉시 멈추지 않을 수 있음
- 데몬 스레드라 강제 종료되지만 cleanup 없음

**개선 방안**:
```python
def poll_server_data():
    try:
        time.sleep(1)
        while not stop_polling.is_set():
            try:
                # ... 폴링 로직 ...
            except Exception as e:
                print(f"[POLLING_ERROR] {e}")
            time.sleep(10)
    finally:
        print("[POLLING] Thread stopped cleanly")
```

**우선순위**: 🟢 낮음 (데몬 스레드라 큰 문제 없음)

---

### 4. 설정 및 환경변수

#### 🟡 문제 4-1: 필수 환경변수 누락 시 기본값 사용

**위치**: `config/settings.py:20-24`

**현재 코드**:
```python
SERVER_BASE_URL = _env("SERVER_BASE_URL", "http://127.0.0.1:8000")  # 기본값
MACHINE_ID = _env("MACHINE_ID", "MACHINE-0001")  # 기본값
```

**문제점**:
- `.env` 파일이 없어도 오류 없이 실행됨
- 잘못된 기본값으로 운영될 위험
- 프로덕션 환경에서 로컬 서버 접속 시도

**개선 방안**:
```python
def _env_required(name: str) -> str:
    """필수 환경변수"""
    value = os.getenv(f"TDB_{name}")
    if not value:
        raise EnvironmentError(
            f"필수 환경변수 TDB_{name}이 설정되지 않았습니다. "
            f"config/.env 파일을 확인하세요."
        )
    return value

# 프로덕션 환경에서는 필수
if os.getenv("TDB_ENV") == "production":
    SERVER_BASE_URL = _env_required("SERVER_BASE_URL")
    MACHINE_ID = _env_required("MACHINE_ID")
else:
    # 개발 환경에서는 기본값 허용
    SERVER_BASE_URL = _env("SERVER_BASE_URL", "http://127.0.0.1:8000")
    MACHINE_ID = _env("MACHINE_ID", "MACHINE-0001")
```

**우선순위**: 🟡 중간

---

#### 🟢 문제 4-2: .env 파일 존재 여부 확인 없음

**위치**: `config/settings.py:6-13`

**현재 코드**:
```python
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    # ... 로드 ...
# ✅ exists() 체크는 있음
```

**평가**: ✅ 양호

---

### 5. 리소스 관리

#### 🔴 문제 5-1: 시리얼 포트 리소스 누수 가능성

**위치**: `hwserial/serial_reader.py:309-465`

**현재 코드**:
```python
try:
    ser = open_serial(baud_rate=9600)
except Exception:
    return  # ❌ ser가 부분적으로 열렸을 경우 정리 안됨

# ... 메인 루프 ...
# ❌ finally 블록 없음
```

**문제점**:
- 예외 발생 시 시리얼 포트가 닫히지 않을 수 있음
- 재시작 시 "port already in use" 오류 가능

**개선 방안**:
```python
ser = None
try:
    ser = open_serial(baud_rate=9600)
    # ... 메인 루프 ...
except KeyboardInterrupt:
    logi("[STOP] Interrupted by user")
except Exception as e:
    loge(f"[FATAL] {e}")
finally:
    if ser and ser.is_open:
        ser.close()
        logi("[CLEANUP] Serial port closed")
```

**우선순위**: 🟡 중간

---

#### 🟡 문제 5-2: JSON 파일 동시 쓰기 경합

**위치**: `hwserial/serial_reader.py:55-66`

**현재 코드**:
```python
def write_state(status, **kwargs):
    # ... state 업데이트 ...
    with open("data/state.json", "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
# ❌ 파일 잠금 없음
```

**문제점**:
- 시리얼 스레드와 폴링 스레드가 동시에 `state.json` 쓰기 가능
- 파일 손상 가능성 (낮음)

**개선 방안**:
```python
import threading

_state_lock = threading.Lock()

def write_state(status, **kwargs):
    with _state_lock:
        # ... state 업데이트 ...
        with open("data/state.json", "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
```

**우선순위**: 🟢 낮음 (실제 충돌 확률 매우 낮음)

---

### 6. Arduino 펌웨어

#### 🟡 문제 6-1: 명령 버퍼 오버플로우 가능성

**위치**: `firmware/src/main.cpp:48-59`

**현재 코드**:
```cpp
void handleSerialCommand() {
  static String buf;
  while (Serial.available() > 0) {
    char ch = Serial.read();
    if (ch == '\n') {
      // ... 명령 처리 ...
      buf = "";
    } else {
      buf += ch;  // ❌ 길이 제한 없음
    }
  }
}
```

**문제점**:
- 명령 길이 제한 없음
- 매우 긴 명령 수신 시 메모리 부족
- Mega 2560의 SRAM은 8KB밖에 안됨

**개선 방안**:
```cpp
void handleSerialCommand() {
  static String buf;
  static const int MAX_CMD_LEN = 128;

  while (Serial.available() > 0) {
    char ch = Serial.read();
    if (ch == '\n') {
      // ... 명령 처리 ...
      buf = "";
    } else if (buf.length() < MAX_CMD_LEN) {
      buf += ch;
    } else {
      // 버퍼 오버플로우 방지
      Serial.println("ERR,CMD_TOO_LONG");
      buf = "";
    }
  }
}
```

**우선순위**: 🟡 중간

---

#### 🟡 문제 6-2: RFID 초기화 실패 시 무한 루프

**위치**: `firmware/src/hardware.cpp:31-43`

**현재 코드**:
```cpp
if (!init_ok) {
    Serial.println(F("FATAL: RFID Reader initialization failed!"));
    while (true) {  // ❌ 무한 루프, 복구 불가
      digitalWrite(LED_BUILTIN, HIGH);
      delay(100);
      digitalWrite(LED_BUILTIN, LOW);
      delay(100);
    }
}
```

**문제점**:
- RFID 초기화 실패 시 Arduino가 멈춤
- 재시작 전까지 복구 불가능
- Pi에서 시리얼 응답 없음 → 타임아웃

**개선 방안**:
```cpp
const int MAX_INIT_RETRIES = 3;
bool rfid_available = false;

for (int i = 0; i < MAX_INIT_RETRIES; i++) {
  if (mfrc522.PCD_PerformSelfTest()) {
    rfid_available = true;
    Serial.println(F("RFID Reader OK."));
    break;
  }
  delay(1000);
}

if (!rfid_available) {
  Serial.println(F("WARN: RFID Reader unavailable. Continuing without RFID."));
  // RFID 없이도 수동 명령은 처리 가능
}
```

**우선순위**: 🟡 중간

---

#### 🟢 문제 6-3: 솔레노이드 동시 작동 시 전류 제한 없음

**위치**: `firmware/src/main.cpp:203-218`

**현재 상태**:
```cpp
// 현재는 슬롯별로 순차 작동 (한 번에 하나)
// ✅ 동시 작동 안함
```

**평가**: ✅ 양호 (순차 처리로 전류 급증 방지)

---

### 7. 기타 잠재적 문제

#### 🟡 문제 7-1: GUI 폴링 실패 시 사용자 알림 없음

**위치**: `main.py:106-108`

**현재 코드**:
```python
except Exception as e:
    print(f"[POLLING_ERROR] 데이터 업데이트 중 오류 발생: {e}")
# ❌ GUI에 오류 표시 없음
```

**문제점**:
- 서버 다운 시 사용자가 모름
- GUI는 마지막 데이터 계속 표시
- 재고 정보가 오래되었는지 알 수 없음

**개선 방안**:
```python
except Exception as e:
    print(f"[POLLING_ERROR] {e}")
    if app:
        app.ui_call(
            app.update_tile_content,
            4,  # 상태 타일
            "⚠️ 서버 연결 끊김"
        )
```

**우선순위**: 🟡 중간

---

#### 🟡 문제 7-2: 배출 중 전력 손실 시 재고 불일치

**현재 상황**:
```
1. Pi: Arduino에 배출 명령
2. Arduino: 배출 시작
3. ❌ 전력 손실 → Arduino 리셋
4. Pi: 타임아웃 → 실패로 기록
5. 서버: 재고 감소 안함 (result=failed)

실제: 약이 일부 배출됨
기록: 배출 안된 것으로 기록
결과: 재고 불일치 ❌
```

**해결 방안**:
- 하드웨어: UPS 또는 배터리 백업
- 소프트웨어: 재고 수동 조정 기능 추가 (관리자 페이지)

**우선순위**: 🟢 낮음 (하드웨어 문제)

---

## 📋 우선순위별 조치 계획

### 🔴 긴급 (즉시 수정)

없음

### 🟡 중요 (1주일 내)

1. **시리얼 연결 실패 시 재시도** (문제 1-1)
2. **오프라인 리포트 파일 크기 제한** (문제 2-1)
3. **시리얼 포트 리소스 정리** (문제 5-1)
4. **GUI 업데이트 예외 처리** (문제 3-1)
5. **환경변수 필수 체크** (문제 4-1)

### 🟢 개선 (1개월 내)

1. **Arduino 명령 버퍼 길이 제한** (문제 6-1)
2. **RFID 초기화 재시도** (문제 6-2)
3. **JSON 파일 쓰기 잠금** (문제 5-2)
4. **GUI 폴링 오류 알림** (문제 7-1)

---

## 🧪 테스트 시나리오

### 장애 상황 시뮬레이션

1. **서버 다운**
   ```bash
   # 서버 중단 상태에서 RFID 스캔
   # 예상: 오프라인 저장 → 서버 복구 시 자동 전송
   ```

2. **Arduino 연결 끊김**
   ```bash
   # Arduino USB 케이블 제거
   # 예상: 시리얼 오류 → 재시도 → GUI 오류 표시
   ```

3. **네트워크 지연**
   ```bash
   # tc qdisc add dev eth0 root netem delay 5000ms
   # 예상: 타임아웃 후 재시도
   ```

4. **디스크 공간 부족**
   ```bash
   # dd if=/dev/zero of=/tmp/filler bs=1M
   # 예상: state.json 쓰기 실패 → 오류 로그
   ```

---

## 🔧 권장 개선 사항

### 모니터링 강화

```python
# 시스템 헬스 체크 추가
def system_health_check():
    checks = {
        "serial_port": is_serial_connected(),
        "server": is_server_reachable(),
        "disk_space": get_disk_usage() < 90,  # 90% 미만
        "memory": get_memory_usage() < 80,
    }
    return all(checks.values()), checks
```

### 로그 레벨 추가

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/tdb.log'),
        logging.StreamHandler()
    ]
)
```

### Watchdog 추가

```bash
# systemd 서비스에 자동 재시작 강화
[Service]
Restart=always
RestartSec=10
WatchdogSec=60  # 60초마다 헬스체크
```

---

## ✅ 결론

### 전반적 평가

- ✅ **기본적인 예외 처리는 잘 되어 있음**
- ⚠️ **엣지 케이스 처리 부족**
- ⚠️ **리소스 관리 개선 필요**
- ⚠️ **사용자 피드백 부족**

### 시스템 안정성 점수

**7.5 / 10** (양호)

- 일반적인 사용 환경에서는 안정적
- 장애 상황에서 일부 취약점 존재
- 프로덕션 운영 전 개선 권장

---

**작성자**: Claude Code
**검토 필요**: 시리얼 통신, 리소스 관리, 환경변수 처리
**최종 업데이트**: 2025-11-27
