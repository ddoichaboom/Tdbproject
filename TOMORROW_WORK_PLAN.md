# 📋 TDB Dispenser - 내일 작업 계획 명세서

**작성일**: 2025-11-26
**작성자**: Claude Code
**프로젝트**: TDB Dispenser (약 자동 배출 시스템)
**현재 상태**: 크리티컬 버그 수정 완료, 프로덕션 준비 90%

---

## 🎯 작업 목표

### **Phase 1: 남은 버그 수정 (우선순위 높음)**
- 3개 고우선순위 버그 수정
- 안정성 및 개발 편의성 향상
- 예상 시간: **30분**

### **Phase 2: 종합 테스트**
- 전체 시스템 통합 테스트
- 예외 경로 테스트
- 24시간 안정성 테스트 준비
- 예상 시간: **1-2시간**

### **Phase 3: 프로덕션 배포 준비**
- 최종 점검 및 문서화
- 배포 체크리스트 완료
- 예상 시간: **30분**

---

## 📝 Phase 1: 고우선순위 버그 수정 (30분)

### **버그 #3: DRY_RUN 보호 누락** ⚠️
**우선순위**: HIGH
**예상 시간**: 5분
**영향도**: 개발/테스트 모드 안정성

#### 문제점
```python
# hwserial/serial_reader.py:166, 274
ok, msg = step_home(ser)  # ← DRY_RUN 체크 없음
```

테스트 모드(`DRY_RUN=True`)에서도 실제 하드웨어를 동작시켜 예상치 못한 동작 발생

#### 수정 방법
```python
# Line 166 (process_queue 내부 - RESET 시)
if settings.DRY_RUN:
    logi("[DRY] HOME(reset)")
else:
    ok, msg = step_home(ser)
    logi(f"  HOME(reset): {msg}")
    if not ok:
        all_ok = False

# Line 274 (process_queue 내부 - 최종 복귀)
if settings.DRY_RUN:
    logi("[DRY] HOME(final)")
else:
    thm = _t()
    ok, msg = step_home(ser)
    logi(f"  HOME(final): {msg} [{_dt(thm)}]")
    if not ok:
        all_ok = False
        loge(f"[ERR] Failed to return HOME: {msg}")
        if adapter:
            adapter.notify_error(f"HOME 복귀 실패: {msg}")
```

#### 테스트 방법
```bash
# 1. DRY_RUN 모드 활성화
export TDB_DRY_RUN=true

# 2. 프로그램 실행
python main.py --demo

# 3. 로그 확인 (실제 하드웨어 동작 없어야 함)
tail -f logs/serial_reader.log | grep "DRY"
```

---

### **버그 #4: dispense() 타임아웃 동적 계산 필요** ⚠️
**우선순위**: HIGH
**예상 시간**: 10분
**영향도**: 다량 배출 시 타임아웃 가능성

#### 문제점
```python
# hwserial/arduino_link.py:42-43
def dispense(ser, slot: int, count: int):
    return _send_cmd_wait(ser, f"DISPENSE,{int(slot)},{int(count)}")
    # ← 항상 5초 타임아웃 (count 무관)
```

8개 이상 배출 시 Arduino 동작 시간(약 1초/개) > 타임아웃(5초) → 실패

#### 수정 방법
```python
# hwserial/arduino_link.py
def dispense(ser, slot: int, count: int):
    """
    슬롯에서 약을 배출합니다.
    타임아웃은 count에 비례하여 자동 계산됩니다.

    타이밍:
    - 기본: 3초
    - 배출당: +1초
    - 예: count=5 → 3 + 5*1 = 8초 타임아웃
    """
    count = int(count)
    timeout = max(5.0, 3.0 + count * 1.0)  # 최소 5초, 개당 1초 추가
    return _send_cmd_wait(ser, f"DISPENSE,{slot},{count}", timeout=timeout)
```

#### 테스트 방법
```bash
# 다량 배출 테스트
python -c "
from hwserial.arduino_link import open_serial, dispense
ser = open_serial()
print('Testing 10-pill dispense...')
ok, msg = dispense(ser, 1, 10)
print(f'Result: {ok}, {msg}')
ser.close()
"
```

---

### **버그 #5: 시리얼 블로킹 읽기 레이턴시** ⚠️
**우선순위**: HIGH
**예상 시간**: 15분
**영향도**: GUI 반응성 (1초 지연)

#### 문제점
```python
# hwserial/arduino_link.py:20-24
def read_uid_once(ser: serial.Serial):
    line = ser.readline()  # ← 1초 블로킹
    if re.fullmatch(r"^[0-9A-F]{8,}$", line):
        return line
    return None
```

RFID 카드가 없으면 매번 1초 대기 → GUI 업데이트 1초 지연

#### 수정 방법
```python
# hwserial/arduino_link.py
def read_uid_once(ser: serial.Serial):
    """
    RFID UID를 논블로킹으로 읽습니다.
    데이터가 없으면 즉시 None 반환하여 GUI 반응성 향상.
    """
    if not ser.in_waiting:
        return None  # 즉시 반환 (0ms)

    try:
        line = ser.readline().decode("ascii", "ignore").strip().upper()
        if re.fullmatch(r"^[0-9A-F]{8,}$", line):
            return line
    except Exception:
        pass

    return None
```

#### 주의사항
⚠️ **CPU 사용률 증가 가능**
- 기존: 1초마다 체크 → CPU 사용률 낮음
- 수정: 연속 체크 → CPU 사용률 증가 가능

#### 대안: 적절한 sleep 추가
```python
# hwserial/serial_reader.py:329 수정
uid = read_uid_once(ser)
if not uid:
    time.sleep(0.1)  # 100ms 대기로 CPU 사용률 제어
    continue
```

#### 테스트 방법
```bash
# GUI 반응성 테스트
python main.py

# 터미널에서 모니터링
watch -n 1 'ps aux | grep python | grep -v grep'
# ← CPU 사용률 확인 (10% 미만 권장)
```

---

## 🧪 Phase 2: 종합 테스트 (1-2시간)

### **테스트 1: 정상 경로 (Happy Path)** ✅
**목적**: 기본 기능 정상 동작 확인
**예상 시간**: 20분

#### 시나리오
```
1. 시스템 부팅
   → 기기 등록 확인
   → RFID 대기 상태

2. RFID 카드 스캔
   → UID 인식
   → 사용자 확인
   → 스케줄 조회

3. 약 배출 프로세스
   → 아침 위치 배출
   → 점심 위치 이동 + 배출
   → 저녁 위치 이동 + 배출
   → HOME 복귀

4. 서버 리포트
   → 각 시간대별 리포트 전송
   → 서버 took_today=1 업데이트
   → 로그 파일 기록
```

#### 체크리스트
- [ ] GUI 정상 표시
- [ ] 회전판 정확한 위치 이동
- [ ] 약 배출 정확한 개수
- [ ] 서버 리포트 전송 성공
- [ ] 로그 파일 생성 확인
- [ ] state.json 업데이트 확인

---

### **테스트 2: 예외 경로 (Exception Paths)** 🔥
**목적**: 오류 상황 안정성 확인
**예상 시간**: 30분

#### 시나리오 A: 서버 다운
```bash
# 1. 서버 중지 (또는 네트워크 차단)
# config/.env에서 잘못된 서버 URL 설정
TDB_SERVER_BASE_URL=http://localhost:9999

# 2. 프로그램 실행 및 RFID 스캔
python main.py

# 3. 확인 사항
# - 크래시 없이 계속 실행
# - data/offline_reports.jsonl 파일 생성
# - 로그에 "[OFFLINE] stored" 메시지
```

**체크리스트**:
- [ ] 크래시 없음
- [ ] 오프라인 리포트 저장됨
- [ ] GUI 오류 메시지 표시
- [ ] 배출은 정상 진행

#### 시나리오 B: Arduino 타임아웃
```bash
# 1. dispense 명령 중 Arduino 케이블 뽑기
python main.py

# 2. 확인 사항
# - 타임아웃 에러 로그
# - 재시도 로직 동작
# - 최종 에러 상태로 종료
```

**체크리스트**:
- [ ] 타임아웃 감지
- [ ] 재시도 1회 수행
- [ ] 적절한 에러 메시지
- [ ] progress 변수 초기화로 크래시 방지 확인

#### 시나리오 C: 디스크 풀 (store_offline 실패)
```bash
# 1. data/ 디렉토리 쓰기 권한 제거
chmod 000 data/

# 2. 서버 다운 상태에서 RFID 스캔
python main.py

# 3. 확인 사항
# - store_offline 예외 로그
# - 크래시 없이 계속 실행
# - 배출은 완료됨
```

**체크리스트**:
- [ ] store_offline 예외 처리 확인
- [ ] 크래시 방지 (Bug #2 수정 확인)
- [ ] 로그에 "Failed to store offline" 메시지

---

### **테스트 3: 에지 케이스 (Edge Cases)** 🧩
**예상 시간**: 20분

#### 케이스 1: 배출 중 키트 교체 시도
```
1. RFID A 스캔 → 배출 시작
2. 배출 중 RFID B 스캔
3. 확인: RFID B 무시됨 (세션 잠금)
```

#### 케이스 2: 오늘 이미 복용 완료
```
1. RFID 스캔 → took_today=1
2. 확인: "이미 복용" 메시지 표시
3. 확인: 배출 진행 안 됨
```

#### 케이스 3: 빈 스케줄
```
1. RFID 스캔 → 스케줄 없음
2. 확인: "배출할 약이 없습니다" 메시지
3. 확인: 대기 상태로 복귀
```

#### 케이스 4: DRY_RUN 모드
```bash
export TDB_DRY_RUN=true
python main.py --demo

# 확인: 하드웨어 동작 없음, 로그에 "[DRY]" 표시
```

---

### **테스트 4: 24시간 안정성 테스트 준비** 🕐
**예상 시간**: 10분 (설정만, 실제 테스트는 24시간)

#### 스크립트 작성
```bash
# scripts/stability_test.sh
#!/bin/bash
echo "Starting 24-hour stability test..."
echo "Start time: $(date)" > stability_test.log

# 프로그램 실행
python main.py >> stability_test.log 2>&1 &
PID=$!

# 모니터링
while kill -0 $PID 2>/dev/null; do
    echo "[$(date)] Process $PID running - Memory: $(ps -o rss= -p $PID) KB" >> stability_test.log
    sleep 300  # 5분마다 체크
done

echo "End time: $(date)" >> stability_test.log
echo "Process terminated!"
```

#### 실행
```bash
chmod +x scripts/stability_test.sh
nohup ./scripts/stability_test.sh &

# 로그 모니터링
tail -f stability_test.log
```

#### 체크 항목
- [ ] 메모리 누수 없음
- [ ] CPU 사용률 안정적
- [ ] 크래시 없음
- [ ] 로그 파일 크기 정상 (RotatingFileHandler 동작)

---

## 🚀 Phase 3: 프로덕션 배포 준비 (30분)

### **배포 전 최종 점검**

#### 1. 환경 변수 확인
```bash
# config/.env
cat config/.env

# 필수 설정 확인
# - TDB_SERVER_BASE_URL: 프로덕션 서버 URL
# - TDB_MACHINE_ID: 기기 고유 ID
# - TDB_DRY_RUN: false (프로덕션)
```

#### 2. 서비스 설정 확인
```bash
# systemd 서비스 파일 확인
cat /etc/systemd/system/tdb.service

# 서비스 활성화 상태
systemctl is-enabled tdb.service
```

#### 3. 로그 디렉토리 권한
```bash
ls -ld logs/
# drwxrwxr-x 2 tdb tdb ... logs/

ls -ld data/
# drwxrwxr-x 2 tdb tdb ... data/
```

#### 4. 펌웨어 버전 확인
```bash
cd firmware
pio device monitor --port /dev/ttyACM0 --baud 9600

# 터미널에 입력:
# VERSION (또는 펌웨어에 VERSION 명령 추가)
```

---

### **배포 체크리스트**

#### 코드 품질
- [x] 크리티컬 버그 수정 완료 (2개)
- [ ] 고우선순위 버그 수정 완료 (3개)
- [x] 구문 검사 통과
- [ ] 종합 테스트 통과
- [ ] 24시간 안정성 테스트 시작

#### 문서화
- [x] DATABASE.md
- [x] PROJECT_CONTEXT.md
- [x] AUTORUN_BACKUP.md
- [x] BUG_ANALYSIS_REPORT.md
- [ ] DEPLOYMENT_GUIDE.md (작성 필요)
- [ ] TROUBLESHOOTING_GUIDE.md (작성 필요)

#### 설정 파일
- [ ] config/.env (프로덕션 설정)
- [ ] systemd 서비스 (자동 시작)
- [ ] 로그 로테이션 (logrotate 설정)
- [ ] 방화벽 규칙 (필요 시)

#### 하드웨어
- [ ] Arduino 펌웨어 최신 버전
- [ ] 회전판 HOME 위치 확인
- [ ] 솔레노이드 동작 테스트
- [ ] RFID 리더 동작 확인

#### 서버 연동
- [ ] 기기 등록 완료
- [ ] API 엔드포인트 접근 가능
- [ ] 네트워크 연결 안정적
- [ ] 하트비트 정상 동작

---

### **배포 시나리오**

#### A. 신규 배포
```bash
# 1. 저장소 클론
git clone https://github.com/ddoichaboom/Tdbproject.git
cd Tdbproject

# 2. 가상환경 설정
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 환경 변수 설정
cp config/.env.example config/.env
nano config/.env  # 프로덕션 설정 입력

# 4. 펌웨어 업로드
cd firmware
pio run -t upload

# 5. 서비스 등록
sudo cp tdb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tdb.service
sudo systemctl start tdb.service

# 6. 로그 확인
sudo journalctl -u tdb.service -f
```

#### B. 업데이트 배포
```bash
# 1. 서비스 중지
sudo systemctl stop tdb.service

# 2. 코드 업데이트
git pull origin main

# 3. 의존성 업데이트 (필요 시)
pip install -r requirements.txt

# 4. 펌웨어 업데이트 (필요 시)
cd firmware
pio run -t upload

# 5. 서비스 재시작
sudo systemctl start tdb.service

# 6. 로그 확인
sudo journalctl -u tdb.service -f
```

---

## 📚 Phase 4: 추가 문서 작성 (선택사항)

### **DEPLOYMENT_GUIDE.md**
**예상 시간**: 30분

내용:
- 신규 기기 설정 절차
- 프로덕션 배포 체크리스트
- 롤백 절차
- 백업 및 복구

---

### **TROUBLESHOOTING_GUIDE.md**
**예상 시간**: 30분

내용:
- 자주 발생하는 오류
- 로그 분석 방법
- 긴급 복구 절차
- 지원 연락처

---

### **API_INTEGRATION_GUIDE.md**
**예상 시간**: 20분

내용:
- 서버 API 엔드포인트
- 요청/응답 예제
- 오류 코드 설명
- 인증 방법 (향후)

---

## 🎯 우선순위 매트릭스

| 작업 | 우선순위 | 시간 | 영향도 | 난이도 |
|------|---------|------|--------|--------|
| 버그 #3 수정 (DRY_RUN) | ⭐⭐⭐ | 5분 | 중간 | 쉬움 |
| 버그 #4 수정 (타임아웃) | ⭐⭐⭐ | 10분 | 높음 | 쉬움 |
| 버그 #5 수정 (레이턴시) | ⭐⭐ | 15분 | 중간 | 보통 |
| 정상 경로 테스트 | ⭐⭐⭐ | 20분 | 높음 | 쉬움 |
| 예외 경로 테스트 | ⭐⭐⭐ | 30분 | 높음 | 보통 |
| 에지 케이스 테스트 | ⭐⭐ | 20분 | 중간 | 보통 |
| 24시간 안정성 테스트 | ⭐⭐ | 10분 | 높음 | 쉬움 |
| 배포 준비 | ⭐⭐⭐ | 30분 | 높음 | 쉬움 |
| 문서 작성 | ⭐ | 1시간 | 낮음 | 쉬움 |

---

## ⏱️ 예상 일정

### **최소 일정 (핵심만)**
```
09:00 - 09:30  버그 #3, #4, #5 수정
09:30 - 10:00  정상 경로 테스트
10:00 - 10:30  예외 경로 테스트
10:30 - 11:00  배포 준비
─────────────────────────────
총 소요 시간: 2시간
```

### **권장 일정 (종합)**
```
09:00 - 09:30  버그 #3, #4, #5 수정
09:30 - 10:00  정상 경로 테스트
10:00 - 10:30  예외 경로 테스트
10:30 - 11:00  에지 케이스 테스트
11:00 - 11:30  배포 준비 및 체크리스트
11:30 - 12:00  24시간 안정성 테스트 시작
─────────────────────────────
총 소요 시간: 3시간

(오후 - 선택사항)
14:00 - 15:00  DEPLOYMENT_GUIDE.md 작성
15:00 - 15:30  TROUBLESHOOTING_GUIDE.md 작성
```

---

## 📊 완료 기준

### **Phase 1 완료 기준**
- [ ] 모든 고우선순위 버그 수정
- [ ] 수정 코드 구문 검사 통과
- [ ] Git 커밋 및 푸시

### **Phase 2 완료 기준**
- [ ] 모든 테스트 시나리오 통과
- [ ] 테스트 로그 정리
- [ ] 발견된 이슈 문서화

### **Phase 3 완료 기준**
- [ ] 배포 체크리스트 100%
- [ ] 서비스 정상 동작 확인
- [ ] 24시간 안정성 테스트 실행 중

---

## 🚨 리스크 및 대응

### **리스크 1: 버그 #5 수정 후 CPU 사용률 증가**
**확률**: 중간
**영향**: 낮음
**대응**: sleep(0.1) 추가로 CPU 사용률 제어

### **리스크 2: 테스트 중 예상치 못한 버그 발견**
**확률**: 높음
**영향**: 중간
**대응**:
- 버그 문서화 (BUG_ANALYSIS_REPORT.md 업데이트)
- 우선순위 평가 후 수정 여부 결정
- 크리티컬한 경우 즉시 수정

### **리스크 3: 24시간 안정성 테스트 실패**
**확률**: 낮음
**영향**: 높음
**대응**:
- 로그 분석으로 원인 파악
- 메모리 누수 → 리소스 정리 코드 추가
- 크래시 → 예외 처리 강화

---

## 📝 메모 공간

### **추가 확인 사항**
```
-
-
-
```

### **발견된 이슈**
```
-
-
-
```

### **개선 아이디어**
```
-
-
-
```

---

## ✅ 최종 체크리스트

### **내일 출근 후 즉시**
- [ ] 이 문서 읽기
- [ ] 개발 환경 활성화 (`source .venv/bin/activate`)
- [ ] Git 최신 상태 확인 (`git pull`)

### **작업 완료 후**
- [ ] 모든 변경사항 커밋
- [ ] GitHub에 푸시
- [ ] 이 문서에 완료 표시
- [ ] 발견된 이슈 기록

---

**작성 완료!** 🎉

이 명세서를 따라가면 **2-3시간 내에 프로덕션 배포 준비 완료** 가능합니다!
