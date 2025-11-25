# ⚡ 내일 작업 빠른 요약

**총 예상 시간**: 2-3시간
**프로덕션 배포**: 가능 (작업 완료 후)

---

## 🎯 핵심 3가지 버그 수정 (30분)

### 1. **DRY_RUN 보호** (5분)
```python
# hwserial/serial_reader.py:166, 274
if settings.DRY_RUN:
    logi("[DRY] HOME")
else:
    ok, msg = step_home(ser)
```

### 2. **dispense 타임아웃 동적 계산** (10분)
```python
# hwserial/arduino_link.py:42
def dispense(ser, slot: int, count: int):
    timeout = max(5.0, 3.0 + count * 1.0)
    return _send_cmd_wait(ser, f"DISPENSE,{slot},{count}", timeout=timeout)
```

### 3. **시리얼 논블로킹 읽기** (15분)
```python
# hwserial/arduino_link.py:20
def read_uid_once(ser: serial.Serial):
    if not ser.in_waiting:
        return None
    # ... 나머지 코드
```

---

## 🧪 테스트 (1시간)

### ✅ 정상 경로 (20분)
- RFID 스캔 → 배출 → 완료

### 🔥 예외 경로 (30분)
- 서버 다운
- Arduino 타임아웃
- 디스크 풀

### 🧩 에지 케이스 (10분)
- 키트 교체 시도
- took_today=1
- 빈 스케줄

---

## 🚀 배포 준비 (30분)

- [ ] 환경 변수 확인
- [ ] 서비스 설정 확인
- [ ] 로그 디렉토리 권한
- [ ] 24시간 안정성 테스트 시작

---

## 📋 체크리스트

```bash
# 1. 버그 수정
cd ~/Tdbproject
source .venv/bin/activate
# → 버그 #3, #4, #5 수정
python -m py_compile hwserial/*.py
git add . && git commit -m "Fix high-priority bugs"

# 2. 테스트
python main.py --demo  # 정상 경로
# → 예외 경로 & 에지 케이스

# 3. 배포 준비
sudo systemctl restart tdb.service
tail -f logs/serial_reader.log

# 4. 안정성 테스트
nohup ./scripts/stability_test.sh &
```

---

**상세 내용**: `TOMORROW_WORK_PLAN.md` 참조
