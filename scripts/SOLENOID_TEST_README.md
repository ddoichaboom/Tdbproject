# 솔레노이드 테스트 가이드

Arduino 펌웨어에 솔레노이드 테스트 명령을 추가하여 각 슬롯의 로딩/배출을 개별적으로 테스트할 수 있습니다.

## 준비 사항

### 1. 펌웨어 업로드

수정된 펌웨어를 Arduino에 업로드합니다:

```bash
cd /home/tdb/Tdbproject/firmware
pio run -t upload
```

### 2. Python 환경 확인

가상환경이 활성화되어 있는지 확인:

```bash
source .venv/bin/activate
```

## 사용 방법

### 개별 슬롯 테스트

#### 슬롯 1 로딩만 테스트
```bash
python scripts/test_solenoid.py --slot 1 --type L
```

#### 슬롯 2 배출만 테스트
```bash
python scripts/test_solenoid.py --slot 2 --type D
```

#### 슬롯 3 로딩+배출 테스트
```bash
python scripts/test_solenoid.py --slot 3 --type B
```

### 전체 슬롯 자동 테스트

모든 슬롯(1, 2, 3)을 순차적으로 테스트:

```bash
python scripts/test_solenoid.py --all
```

## 명령어 옵션

| 옵션 | 값 | 설명 |
|------|-----|------|
| `--slot` | 1, 2, 3 | 테스트할 슬롯 번호 |
| `--type` | L, D, B | L=Loading만, D=Dispensing만, B=Both(둘 다) |
| `--all` | - | 전체 슬롯 순차 테스트 (로딩+배출) |

## Arduino 명령 (시리얼 직접 전송)

Python 스크립트 없이 시리얼 모니터로 직접 테스트:

```
TEST_SOLENOID,1,L     # 슬롯1 로딩
TEST_SOLENOID,2,D     # 슬롯2 배출
TEST_SOLENOID,3,B     # 슬롯3 로딩+배출
```

### 시리얼 모니터 사용법

```bash
# PlatformIO 시리얼 모니터
cd firmware
pio device monitor

# 또는 직접 시리얼 연결
screen /dev/ttyACM0 9600
```

## 동작 타이밍

- **로딩 (Loading)**: 1초 ON → 0.5초 대기
- **배출 (Dispensing)**: 1초 ON → 0.5초 대기
- **Both**: 로딩 → 배출 순차 실행 (총 약 3초)

## 핀 매핑

| 슬롯 | 로딩 핀 | 배출 핀 |
|------|---------|---------|
| 1 | 22 | 23 |
| 2 | 24 | 25 |
| 3 | 26 | 27 |

## 예상 출력

### 성공 예시
```
Arduino 연결 중...
✓ Arduino 연결 성공: /dev/ttyACM0

==================================================
슬롯 1 테스트: Loading
==================================================
✓ 성공: OK,TEST_SOLENOID,1,L
```

### 실패 예시
```
❌ 시리얼 포트 열기 실패: could not open port

해결 방법:
1. Arduino가 연결되어 있는지 확인
2. config/.env에서 TDB_SERIAL_PORT 확인
3. 다른 프로그램에서 포트를 사용 중인지 확인
```

## 문제 해결

### 시리얼 포트를 찾을 수 없음

```bash
# 연결된 시리얼 포트 확인
ls /dev/tty* | grep -E "(ACM|USB)"

# config/.env 설정
TDB_SERIAL_PORT=/dev/ttyACM0
```

### 솔레노이드가 작동하지 않음

1. **전원 확인**: 솔레노이드에 충분한 전원이 공급되는지 확인 (릴레이 모듈)
2. **배선 확인**: 핀 연결이 올바른지 확인
3. **릴레이 로직**: HIGH/LOW 로직이 릴레이 모듈과 일치하는지 확인

### 타임아웃 에러

```bash
# timeout 값 조정이 필요한 경우
# test_solenoid.py의 send_raw() timeout 파라미터 수정
```

## 안전 주의사항

⚠️ **경고**: 실제 약품이 들어있지 않은 상태에서 테스트하세요.

1. 테스트 전 슬롯을 비운 상태로 확인
2. 연속 테스트 시 과열 주의
3. 솔레노이드 동작 중에는 손을 넣지 마세요

## 통합 테스트 워크플로우

전체 시스템 검증:

```bash
# 1. 서보 모터 홈 복귀
python scripts/recovery_jog.py --step HOME

# 2. 서보 STEP 테스트
python scripts/recovery_jog.py --step NEXT

# 3. 솔레노이드 전체 테스트
python scripts/test_solenoid.py --all

# 4. 서보 홈 복귀
python scripts/recovery_jog.py --step HOME
```
