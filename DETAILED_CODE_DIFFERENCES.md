# Detailed Code Differences: GitHub vs Local

## hwserial/serial_reader.py

### Key Differences Summary
| Item | GitHub | Local | Impact |
|------|--------|-------|--------|
| Total Lines | ~400 | ~450 | Local has ~50 more lines |
| Helper Functions | None | `_t()`, `_dt()` | Local has performance timing |
| Adapter Support | No | Yes | Local supports GUI integration |
| User Name Lookup | No | Yes | Local shows actual user names |
| Offline Report Handling | Direct HTTP | Uses function | Local more maintainable |
| Session Lock | Basic | Stricter | Local more secure |

### Code Example 1: Timing Helpers
**GitHub**: No timing utilities
**Local**:
```python
def _t():
    """타이밍 측정용 시작 시간"""
    return time.monotonic()

def _dt(t0):
    """경과 시간 포맷팅 (ms)"""
    return f"{(time.monotonic() - t0) * 1000:.0f}ms"
```
**Usage**: `tmv = _t(); ... logi(f"STEP: {msg} [{_dt(tmv)}]")`

### Code Example 2: flush_offline() Implementation

**GitHub** (direct HTTP call):
```python
url = settings.SERVER_BASE_URL.rstrip("/") + "/dispense/report"
with OFFLINE_PATH.open("r", encoding="utf-8") as f:
    for line in f:
        ...
        try:
            payload = json.loads(line)
            r = requests.post(url, json=payload, timeout=5)
            r.raise_for_status()
            sent += 1
        except Exception:
            keep.append(line)
```

**Local** (uses function call):
```python
with OFFLINE_PATH.open("r", encoding="utf-8") as f:
    for line in f:
        ...
        try:
            payload = json.loads(line)
            report_dispense(
                user_id=payload.get("user_id"),
                machine_id=payload.get("machine_id"),
                items=payload.get("items", []),
                time=payload.get("time"),
                result=payload.get("result", "completed")
            )
            sent += 1
        except Exception:
            keep.append(line)
```

**Benefits of Local Approach**:
- Uses existing error handling from `report_dispense()`
- Consistent with main code path
- Easier to maintain (single function)
- Better logging/retry handling

### Code Example 3: process_queue() Signature

**GitHub**:
```python
def process_queue(base_url: str, machine_id: str, user_id: str, phases: list, ser):
```

**Local**:
```python
def process_queue(machine_id: str, user_id: str, phases: list, ser, adapter=None):
```

**Key Change**: 
- Removed `base_url` (not used)
- Added `adapter=None` (for GUI callbacks)

### Code Example 4: process_queue() Enhancement - Adapter Callbacks

**GitHub**: No callbacks
**Local**: Rich callback support
```python
# Movement with callback
write_state(status="moving", last_uid=_active_kit_uid, phase=time_key, progress=progress)
if adapter:
    adapter.notify_status_update(3, f"{time_key} 위치로 이동 중...")

# Dispensing with callback
write_state(status="dispensing", last_uid=_active_kit_uid, phase=time_key, progress=progress)
if adapter:
    adapter.notify_status_update(3, f"{time_key} - 슬롯 {slot}에서 {count}개 배출 중...")

# Error callback
if not ok:
    if adapter:
        adapter.notify_error(f"슬롯 {slot} 배출 실패!")
```

**Benefits**:
- Real-time GUI updates
- Rich error reporting
- Optional (doesn't break if adapter is None)

### Code Example 5: User Name Lookup

**GitHub**: Not implemented

**Local** (lines 374-381):
```python
# user_id로 user_name 찾기
users = get_users_for_machine(machine_id)
user_name = "알 수 없는 사용자"
if users:
    for user in users:
        if str(user.get("user_id")) == user_id:
            user_name = user.get("name")
            break

if adapter:
    adapter.notify_status_update(3, f"{user_name}님 스케줄 조회 중...")
```

**Benefits**:
- Shows friendly user names instead of IDs
- Better UX
- Still graceful if lookup fails

### Code Example 6: Session Lock

**GitHub**:
```python
if _session_user_id is not None:
    if _active_kit_uid and uid != _active_kit_uid:
        loge(f"[LOCK] KIT SWAP attempt during dispensing: active={_active_kit_uid}, new={uid} -> ignored")
    # Same or different, session is active so ignore
    continue
```

**Local**:
```python
if _session_user_id is not None:
    continue
```

**Analysis**:
- GitHub logs attempted swaps (informative)
- Local ignores all UIDs during session (simpler, safer)
- Both are acceptable, local is more secure
- GitHub's logging is useful for debugging

---

## hwserial/arduino_link.py

### Key Differences Summary
| Item | GitHub | Local | Impact |
|------|--------|-------|--------|
| `open_serial()` Signature | No params | `(baud_rate=9600, timeout=1)` | Local more flexible |
| Port Detection | Uses settings module | Uses autodetect_port() | Local simpler |
| READY Wait | 3s timeout for READY msg | 2s sleep after reset | Different timing |
| jog() Validation | Basic | Validates ranges (100-15000ms) | Local safer |
| Total Lines | ~130 | ~106 | GitHub slightly longer |

### Code Example 1: open_serial()

**GitHub**:
```python
def open_serial():
    port = settings.SERIAL_PORT
    if not port:
        # Auto-detect logic here
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
    
    # Wait for READY message
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
```

**Local**:
```python
def open_serial(baud_rate=9600, timeout=1):
    port = autodetect_port()
    if not port:
        raise IOError("Arduino not found")
    ser = serial.Serial(port, baud_rate, timeout=timeout)
    time.sleep(2)  # Wait for Arduino to reset
    ser.flushInput()
    return ser
```

**Comparison**:
| Aspect | GitHub | Local |
|--------|--------|-------|
| Flexibility | Can read from settings | Parameters with defaults |
| Timeout | 3s for READY message | Fixed 2s sleep |
| Error Handling | Falls back to /dev/ttyACM0 | Raises IOError |
| Clarity | More complex | Simpler, easier to test |
| Testability | Tied to settings | Can pass different params |

### Code Example 2: jog() Function

**GitHub**:
```python
def jog(ser, direction: str, ms: int, speed: int | None = None):
    d = direction.strip().upper()[0]
    if d not in ("F", "B"):
        return False, "BAD_DIR"
    ms = int(ms)
    cmd = f"JOG,{d},{ms}" if speed is None else f"JOG,{d},{int(speed)},{ms}"
    return send_raw(ser, cmd)
```

**Local**:
```python
def jog(ser, direction: str, ms: int, speed: int = None):
    """회전판을 수동으로 조작 (긴급 복구용)"""
    direction = str(direction).upper()
    if direction not in ("F", "B"):
        return False, "ERR,INVALID_DIRECTION"
    
    ms = max(100, min(15000, int(ms)))  # 안전 범위: 100ms ~ 15s
    
    if speed is None:
        cmd = f"JOG,{direction},{ms}"
    else:
        speed = max(0, min(100, int(speed)))  # 0-100%
        cmd = f"JOG,{direction},{speed},{ms}"
    
    return send_raw(ser, cmd, timeout=max(8.0, ms / 1000.0 + 2.0))
```

**Key Differences**:
1. Local validates input ranges (100-15000ms for duration)
2. Local validates speed (0-100%)
3. Local uses dynamic timeout based on duration
4. Local has docstring
5. GitHub simpler but less safe

**Safety Benefit**: Local prevents accidental unsafe values

---

## services/api_client.py

### Key Differences Summary
| Item | GitHub | Local | Impact |
|------|--------|-------|--------|
| Total Functions | 5 | 9 | Local has 4 dashboard API functions |
| Session Init | Pre-built at import | Lazy on first use | GitHub more efficient |
| Retry Config | Advanced `Retry` class | Same basic `Retry` | Equivalent |
| URL Building | Helper function `_url()` | Inline URL construction | GitHub more maintainable |
| `check_machine_registered()` | 4 fallback paths | Direct GET call | GitHub more robust |
| Queue Validation | Strict, extensive | Simple, minimal | GitHub more defensive |
| Parameter Order | Logical (machine_id first) | Less logical (user_id first) | GitHub better |
| Error Handling | `raise_for_status()` | Wrapped in try/except | Both adequate |

### Code Example 1: Session Management

**GitHub**:
```python
def _build_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3, connect=3, read=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
    )
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    return s

_session = _build_session()  # Built at module import
```

**Local**:
```python
_session = None

def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        retry = Retry(total=3, connect=3, read=3, backoff_factor=0.5, 
                     status_forcelist=(500, 502, 503, 504))
        adapter = HTTPAdapter(max_retries=retry)
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)
        _session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    return _session  # Lazy initialization
```

**Comparison**:
| Aspect | GitHub | Local |
|--------|--------|-------|
| Initialization | Eager (at import time) | Lazy (on first use) |
| Memory Impact | Always allocated | Only if used |
| Startup Time | Slightly slower | Slightly faster |
| Status Codes | 429, 500-504 | 500-504 only |
| Complexity | Explicit builder | Lazy with global |

GitHub's approach is slightly more efficient for immediate use, but local's lazy approach is more memory efficient for rare usage.

### Code Example 2: check_machine_registered()

**GitHub** (Fallback paths):
```python
def check_machine_registered(machine_id: str) -> bool:
    get_paths  = ("/machine/check", "/machines/check")
    post_paths = ("/machine/check", "/machines/check")
    
    # Try GET methods first
    for p in get_paths:
        try:
            r = _session.get(_url(p), params={"machine_id": machine_id}, timeout=DEFAULT_GET_TO)
            if r.status_code == 404:
                continue  # Try next path
            r.raise_for_status()
            data = r.json()
            return bool(data.get("registered", False))
        except requests.RequestException:
            continue
        except ValueError:  # JSON parse error
            continue
    
    # Try POST methods if GET failed
    for p in post_paths:
        try:
            r = _session.post(_url(p), json={"machine_id": machine_id}, timeout=DEFAULT_POST_TO)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            data = r.json()
            return bool(data.get("registered", False))
        except requests.RequestException:
            continue
        except ValueError:
            continue
    
    return False
```

**Local** (Direct call):
```python
def check_machine_registered(machine_id: str) -> bool:
    res = _get(f"/machine/check", params={"machine_id": machine_id})
    return res.get("registered", False) if isinstance(res, dict) else False
```

**Comparison**:
| Aspect | GitHub | Local |
|--------|--------|-------|
| Fallback Paths | 4 paths (GET + POST variants) | Single direct call |
| Robustness | Very robust, handles API changes | Less robust, assumes endpoint exists |
| Complexity | Complex with nested loops | Simple, direct |
| 404 Handling | Explicit with continue | Returns False on error |
| API Change Tolerance | Can survive endpoint renames | Breaks if endpoint changes |

GitHub is significantly more robust against API evolution, but local is simpler.

### Code Example 3: build_queue()

**GitHub** (Strict validation):
```python
def build_queue(machine_id: str, user_id: str, *, weekday: str | None = None) -> list[dict]:
    payload = {
        "machine_id": machine_id,
        "user_id": user_id,
        "client_ts": int(time.time()),
        "tz_offset_min": 540,
    }
    if weekday:
        payload["weekday"] = weekday
    
    r = _session.post(_url("/queue/build"), json=payload, timeout=DEFAULT_POST_TO)
    r.raise_for_status()
    
    # Strict validation
    data = r.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid response (not a JSON object): {str(data)[:500]}")
    queue = data.get("queue", [])
    if not isinstance(queue, list):
        raise RuntimeError(f"Invalid 'queue' type: {type(queue).__name__}")
    
    # Normalization: handle strings/ints
    norm = []
    for item in queue:
        if isinstance(item, dict):
            norm.append(item)
        elif isinstance(item, (str, int)):
            try:
                norm.append({"slot": int(item), "count": 1})
            except Exception:
                continue
    return norm
```

**Local** (Simple):
```python
def build_queue(machine_id: str, user_id: str, weekday: str = None):
    payload = {
        "machine_id": machine_id,
        "user_id": user_id,
        "client_ts": int(time.time()),
        "tz_offset_min": 540,
    }
    if weekday:
        payload["weekday"] = weekday
    
    return _post("/queue/build", json=payload)
```

**Comparison**:
| Aspect | GitHub | Local |
|--------|--------|-------|
| Validation | Extensive | Minimal |
| Error Messages | Specific RuntimeErrors | Generic None return |
| Type Handling | Converts strings/ints to dict | Passes through raw |
| Robustness | Validates structure | Assumes correct format |
| Debuggability | Clear error messages | Silent failures |

GitHub's approach is much more defensive and easier to debug.

### Code Example 4: report_dispense() Parameter Order

**GitHub**:
```python
def report_dispense(
    machine_id: str,
    user_id: str,
    time_key: str,
    items: List[Dict[str, Any]],
    result: str,
    client_tx_id: Optional[str] = None,
) -> Dict[str, Any]:
```

**Local**:
```python
def report_dispense(user_id: str, machine_id: str, items: list, time: str = None, result: str = "completed"):
```

**Issues with Local**:
- Parameter order is less logical
- No `client_tx_id` support
- `time` has confusing default (None)
- Less complete

GitHub's approach is clearer.

### Code Example 5: New Functions in Local

**Local ONLY** (not in GitHub):
```python
def get_users_for_machine(machine_id: str):
    return _get(f"/machine/{machine_id}/users")

def get_slots_for_machine(machine_id: str):
    return _get(f"/machine/{machine_id}/slots")

def get_today_schedules_for_machine(machine_id: str):
    return _get(f"/machine/{machine_id}/schedules/today")

def get_dose_history_for_machine(machine_id: str, start_date: str):
    return _get(f"/dose-history/machine/{machine_id}", params={"start_date": start_date})
```

**Purpose**: Dashboard data fetching
**GitHub**: Has no equivalent (no dashboard support)

---

## config/settings.py

### Key Difference

**GitHub** (line 35):
```python
DRY_RUN = _env("DRY_RUN", "false").lower() in ("1","true","yes","y","on")
```

**Local** (line 36):
```python
DRY_RUN = False
```

**Impact**:
| Aspect | GitHub | Local |
|--------|--------|-------|
| Flexibility | Highly configurable via env | Production default only |
| Testing | Easy to test dry-run mode | Must comment code or change file |
| Safety | More options, more risk | Safer default |
| Environment Driven | Yes | No |
| Default | false (safe) | False (safe) |

**Recommendation**: Local should revert to GitHub's approach for flexibility.

---

## main.py

### The Critical Difference

**GitHub**: Empty file (1 line or completely empty)
**Local**: 153-line complete application

### GitHub main.py
```
(empty or nearly empty)
```

### Local main.py Key Sections

1. **Imports** (13 lines):
   - Imports GUI, adapter, APIs, threading, datetime
   
2. **Event Handlers** (60+ lines):
   - `on_unregistered()` - Device registration QR
   - `on_waiting()` - Idle state
   - `on_uid()` - UID scanned
   - `on_error()` - Error display
   - `on_kit_unregistered()` - Kit QR display
   - `on_status_update()` - Status messages
   - `on_user_list_update()` - User inventory
   - `on_slot_list_update()` - Slot info
   - `on_schedule_list_update()` - Schedule info
   - `on_history_list_update()` - History records

3. **Polling Thread** (25 lines):
   - Fetches server data every 10 seconds
   - Updates all dashboard tiles
   - Handles history with date parsing
   
4. **Adapter Initialization** (12 lines):
   - Wires all callbacks
   - Configures adapter
   
5. **Main Loop** (15 lines):
   - Starts adapter
   - Runs app mainloop
   - Handles cleanup on exit

### Features Only in Local main.py
- Integrated GUI + Serial Reader in single process
- Background data polling (10s interval)
- Event-driven architecture
- Demo mode support (`--demo` flag)
- Thread management
- Proper error handling and cleanup
- Fullscreen support
- Real-time UI updates

### Why GitHub main.py is Empty
The GitHub version uses separate components:
- `serial_reader.py` runs independently
- `gui/qr_display.py` reads state.json
- No integrated entry point

---

## Summary Table: All Differences

| Category | GitHub | Local | Better |
|----------|--------|-------|--------|
| **serial_reader.py** | 400 lines | 450 lines | LOCAL (feature-rich) |
| - Performance timing | No | Yes | LOCAL |
| - User name lookup | No | Yes | LOCAL |
| - Adapter support | No | Yes | LOCAL |
| - Offline handling | HTTP direct | Function call | LOCAL |
| **arduino_link.py** | 130 lines | 106 lines | GITHUB (simpler) |
| - Input validation | No | Yes | LOCAL |
| - Dynamic timeout | No | Yes | LOCAL |
| **api_client.py** | 180 lines | 104 lines | GITHUB (more robust) |
| - Functions | 5 | 9 | LOCAL |
| - Retry config | Advanced | Basic | GITHUB |
| - URL building | Helper | Inline | GITHUB |
| - Fallback paths | Yes (4) | No | GITHUB |
| - Queue validation | Strict | Simple | GITHUB |
| - Parameter order | Logical | Less logical | GITHUB |
| **config/settings.py** | 38 lines | 38 lines | GITHUB (DRY_RUN env) |
| **main.py** | Empty | 153 lines | LOCAL (complete) |
| **Overall** | 40% complete | 100% complete | LOCAL |

