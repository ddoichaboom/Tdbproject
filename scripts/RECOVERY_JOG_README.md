# 서보 모터 수동 제어 가이드 (recovery_jog.py)

Arduino 펌웨어와 통신하여 서보 모터를 수동으로 제어하는 긴급 복구 도구입니다. 회전판이 잘못된 위치에 있거나 테스트가 필요할 때 사용합니다.

## 준비 사항

### 1. Python 환경 확인

가상환경이 활성화되어 있는지 확인:

```bash
source .venv/bin/activate
```

### 2. Arduino 연결 확인

Arduino가 USB로 연결되어 있고, 펌웨어가 업로드되어 있어야 합니다.

```bash
# 포트 확인
ls -l /dev/ttyACM0
```

## 사용 방법

### 🎯 STEP 모드 (정해진 단계 이동)

회전판을 정확한 단계로 이동합니다.

#### 다음 단계로 이동 (STEP_NEXT)

```bash
python scripts/recovery_jog.py --step NEXT
```

**동작**:
- 현재 스테이지 0 (아침) → 스테이지 1 (점심): 2000ms 전진
- 현재 스테이지 1 (점심) → 스테이지 2 (저녁): 2500ms 전진
- 현재 스테이지 2 (저녁): 더 이상 전진하지 않음

#### 홈 위치로 복귀 (STEP_HOME)

```bash
python scripts/recovery_jog.py --step HOME
```

**동작**:
- 현재 스테이지 2 (저녁) → 스테이지 1 (점심): 2500ms 후진
- 현재 스테이지 1 (점심) → 스테이지 0 (아침): 2000ms 후진
- 현재 스테이지 0 (아침): 이미 홈 위치

---

### 🕹️ JOG 모드 (수동 조작)

회전판을 임의의 거리만큼 수동으로 움직입니다.

#### 전진 (Forward)

```bash
# 1초간 전진 (기본 속도 50%)
python scripts/recovery_jog.py --dir F --ms 1000

# 2초간 빠르게 전진 (속도 80%)
python scripts/recovery_jog.py --dir F --ms 2000 --speed 80

# 500ms 천천히 전진 (속도 30%)
python scripts/recovery_jog.py --dir F --ms 500 --speed 30
```

#### 후진 (Backward)

```bash
# 1초간 후진 (기본 속도 50%)
python scripts/recovery_jog.py --dir B --ms 1000

# 3초간 빠르게 후진 (속도 70%)
python scripts/recovery_jog.py --dir B --ms 3000 --speed 70
```

---

## 명령어 옵션

### STEP 모드

| 옵션 | 값 | 설명 |
|------|-----|------|
| `--step` | `NEXT` | 다음 스테이지로 이동 (아침→점심→저녁) |
| `--step` | `HOME` | 홈 위치로 복귀 (저녁→점심→아침) |

### JOG 모드

| 옵션 | 값 | 필수 | 설명 |
|------|-----|------|------|
| `--dir` | `F` 또는 `B` | ✓ | 방향: F=전진, B=후진 |
| `--ms` | 숫자 (양수) | ✓ | 동작 시간 (밀리초) |
| `--speed` | 0-100 | ✗ | 속도 (기본값: 50%) |

---

## 사용 예제

### 예제 1: 회전판 위치 초기화

시스템 시작 전 홈 위치로 이동:

```bash
python scripts/recovery_jog.py --step HOME
```

### 예제 2: 단계별 이동 테스트

```bash
# 아침 → 점심
python scripts/recovery_jog.py --step NEXT

# 점심 → 저녁
python scripts/recovery_jog.py --step NEXT

# 저녁 → 아침 (홈)
python scripts/recovery_jog.py --step HOME
```

### 예제 3: 미세 조정

회전판이 정확한 위치에 있지 않을 때:

```bash
# 100ms만 살짝 전진
python scripts/recovery_jog.py --dir F --ms 100

# 200ms 천천히 후진 (속도 20%)
python scripts/recovery_jog.py --dir B --ms 200 --speed 20
```

### 예제 4: 긴급 복구

회전판이 끝까지 갔을 때:

```bash
# 최대 거리 후진 (4500ms = 저녁→아침)
python scripts/recovery_jog.py --dir B --ms 4500

# 또는 STEP HOME 사용
python scripts/recovery_jog.py --step HOME
```

---

## 회전판 스테이지 이해

```
┌─────────────────────────────────────────┐
│  스테이지 0 (아침)  - HOME 위치         │
│         ↓ 2000ms 전진 (STEP NEXT)       │
│  스테이지 1 (점심)                      │
│         ↓ 2500ms 전진 (STEP NEXT)       │
│  스테이지 2 (저녁)                      │
│         ↓ 4500ms 후진 (STEP HOME)       │
│  스테이지 0 (아침)  - HOME 위치         │
└─────────────────────────────────────────┘
```

**참고**:
- STEP 명령은 내부 상태를 추적합니다
- JOG 명령은 상태를 변경하지 않으므로 주의해서 사용

---

## 예상 출력

### 성공 예시

```bash
$ python scripts/recovery_jog.py --step NEXT
STEP -> OK,STEP,NEXT
```

```bash
$ python scripts/recovery_jog.py --dir F --ms 1000
JOG -> OK,JOG,F,50,1000
```

### 에러 예시

```bash
$ python scripts/recovery_jog.py --dir F --ms 1000 --step HOME
usage: recovery_jog.py [-h] [--dir {F,B}] [--ms MS] [--speed SPEED] [--step {NEXT,HOME}]
recovery_jog.py: error: STEP과 JOG는 동시에 사용할 수 없습니다
```

---

## 시리얼 포트 충돌 주의

⚠️ **중요**: 이 스크립트 실행 시 **serial_reader.py가 실행 중이면 충돌 발생**

### 해결 방법

#### 옵션 1: serial_reader 종료 후 사용

```bash
# 1. serial_reader 종료
pkill -f serial_reader

# 2. recovery_jog 실행
python scripts/recovery_jog.py --step HOME

# 3. serial_reader 재시작 (필요시)
python hwserial/serial_reader.py
```

#### 옵션 2: 시리얼 포트 강제 해제

```bash
# 모든 Python 프로세스 종료
pkill -f python

# 1-2초 대기 후 실행
python scripts/recovery_jog.py --step HOME
```

---

## 안전 제한

Arduino 펌웨어에서 안전을 위해 다음 제한이 있습니다:

- **최소 시간**: 100ms
- **최대 시간**: 15000ms (15초)
- **속도 범위**: 0-100%

이 범위를 벗어나면 자동으로 제한됩니다.

---

## Arduino 명령 (직접 시리얼 전송)

Python 스크립트 없이 시리얼 모니터로 직접 테스트:

```
STEP,NEXT           # 다음 단계
STEP,HOME           # 홈 복귀 (또는 HOME 만 입력)
JOG,F,1000          # 전진 1초 (기본 속도)
JOG,B,50,2000       # 후진 속도 50%, 2초
```

### 시리얼 모니터 열기

```bash
cd firmware
~/.platformio/penv/bin/pio device monitor --port /dev/ttyACM0 --baud 9600
```

---

## 문제 해결

### 시리얼 포트를 찾을 수 없음

```bash
# 포트 확인
ls -l /dev/ttyACM* /dev/ttyUSB*

# config/.env 설정
TDB_SERIAL_PORT=/dev/ttyACM0
```

### 타임아웃 에러

```bash
# Arduino 재연결
# USB 뽑았다가 다시 꽂고 재시도
```

### 회전판이 예상과 다르게 움직임

```bash
# 홈 위치로 리셋 후 다시 시도
python scripts/recovery_jog.py --step HOME
```

---

## 통합 워크플로우

전체 시스템 테스트 시퀀스:

```bash
# 1. 홈 위치로 초기화
python scripts/recovery_jog.py --step HOME

# 2. 아침 위치 확인 (현재 위치)
# (목시 확인)

# 3. 점심 위치로 이동
python scripts/recovery_jog.py --step NEXT

# 4. 솔레노이드 슬롯 2 테스트 (점심)
python scripts/test_solenoid.py --slot 2 --type B

# 5. 저녁 위치로 이동
python scripts/recovery_jog.py --step NEXT

# 6. 솔레노이드 슬롯 3 테스트 (저녁)
python scripts/test_solenoid.py --slot 3 --type B

# 7. 홈으로 복귀
python scripts/recovery_jog.py --step HOME

# 8. 솔레노이드 슬롯 1 테스트 (아침)
python scripts/test_solenoid.py --slot 1 --type B
```

---

## 관련 문서

- **솔레노이드 테스트**: `scripts/SOLENOID_TEST_README.md`
- **프로젝트 가이드**: `CLAUDE.md`
- **펌웨어 소스**: `firmware/src/main.cpp`
