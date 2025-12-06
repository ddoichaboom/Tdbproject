# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TDB Dispenser is a medication dispensing system consisting of:
- **Raspberry Pi client** (Python): Reads RFID cards, communicates with backend server, controls Arduino via serial
- **Arduino Mega firmware** (C++/PlatformIO): Controls servos, RFID reader (MFRC522), and dispenses medication
- **Dashboard GUI** (Tkinter): Modern 2x3 tile dashboard for real-time status monitoring and QR code display
- **NestJS Server** (TypeScript): Production backend with MySQL database (cloned locally in `tdb_server/`)
- **Mock server** (FastAPI): Local testing server simulating backend API

The system dispenses medication in three time slots (morning/afternoon/evening) by rotating a carousel mechanism using servo motors.

## Development Environment Setup

```bash
# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Firmware (requires PlatformIO)
cd firmware
pio run              # Build firmware
pio run -t upload    # Upload to Arduino Mega
pio device monitor   # Monitor serial output
```

## Common Commands

### Running the System

```bash
# Option 1: Run integrated system (GUI + Serial Reader)
python main.py                    # Production mode (fullscreen)
python main.py --demo             # Demo mode (windowed, simulated events)

# Option 2: Run components separately (legacy mode)
python hwserial/serial_reader.py  # Serial reader only (requires Arduino)
python gui/qr_display.py          # Simple QR display GUI

# Run mock server for local testing (development only)
cd dev
uvicorn mock_server:app --reload --port 8000
```

### Testing & Recovery

```bash
# Manual jog control (emergency recovery)
python scripts/recovery_jog.py --dir F --ms 1000           # Jog forward 1s
python scripts/recovery_jog.py --dir B --ms 500            # Jog backward 0.5s
python scripts/recovery_jog.py --step NEXT                 # Step to next slot
python scripts/recovery_jog.py --step HOME                 # Return to home

# Test firmware commands directly
cd firmware
pio device monitor
# Then send: DISPENSE,1,2  or  STEP,NEXT  or  HOME
```

## Architecture

### Data Flow

```
RFID Card → Arduino → Serial → Pi (serial_reader.py) → Backend API (NestJS/MySQL)
                                ↓
                           State File (data/state.json)
                                ↓
                     ┌──────────┴──────────┐
                     ↓                     ↓
            GUI (qr_display.py)    Dashboard (gui_app.py)
            (Simple QR Display)    (2x3 Tile Dashboard)
```

**Integrated Mode (main.py)**:
```
RFID Card → Arduino → Serial → serial_reader_adapter → Dashboard GUI (gui_app.py)
                                         ↓
                                   Backend API (NestJS/MySQL)
```

### Key Components

**hwserial/serial_reader.py** - Main event loop
- Polls RFID UIDs from Arduino
- Calls backend API to resolve user and build medication queue
- Orchestrates dispensing sequence (morning→afternoon→evening)
- Writes state to `data/state.json` for GUI consumption
- Session locking prevents kit swapping during dispensing

**hwserial/arduino_link.py** - Serial protocol wrapper
- `open_serial()`: Auto-detects Arduino port, waits for READY
- `dispense(ser, slot, count)`: Commands Arduino to dispense pills
- `step_next(ser)`, `step_home(ser)`: Carousel positioning
- `send_raw(ser, cmd, timeout)`: Low-level command/response handler

**services/api_client.py** - Backend communication
- `check_machine_registered()`: Verify machine registration
- `resolve_uid(uid)`: Check if RFID card is registered
- `build_queue(machine_id, user_id)`: Get medication schedule
- `report_dispense()`: Report completion to server
- `heartbeat()`: Periodic keepalive + offline report flush

**config/settings.py** - Configuration loader
- Reads `config/.env` file (TDB_* environment variables)
- `SERVER_BASE_URL`, `MACHINE_ID`, `SERIAL_PORT`, `BAUDRATE`
- `DRY_RUN`, `UID_COOLDOWN_SEC`, `HEARTBEAT_SEC`

**firmware/src/main.cpp** - Arduino firmware
- Reads MFRC522 RFID tags, prints UID to serial
- Processes commands: `DISPENSE,<slot>,<count>`, `STEP,NEXT`, `HOME`, `JOG,<dir>,<ms>`
- Controls servos via `servos.hpp` (timing: morning=0ms, afternoon=2000ms, evening=4500ms)

**gui/gui_app.py** - Dashboard GUI (NEW)
- Modern 2x3 tile layout with dark theme
- Real-time status display (time, inventory, users, schedule, status, device ID)
- Popup overlay system for alerts and QR codes
- Thread-safe UI updates via `ui_call()` method
- Fullscreen support for Raspberry Pi touchscreen

**gui/qr_display.py** - Simple QR display GUI (Legacy)
- Lightweight QR code display for registration
- Polls `data/state.json` every 500ms
- Status text display for basic states
- Used when running components separately

**hwserial/serial_reader_adapter.py** - GUI adapter (NEW)
- Bridges serial_reader and GUI components
- Event-driven callbacks: `on_waiting`, `on_uid`, `on_error`, `on_unregistered`
- UID debouncing (1 second cooldown)
- Demo mode for testing without hardware

**main.py** - Integrated application bootstrap (NEW)
- Combines Dashboard GUI + Serial Reader in one process
- Command-line flags: `--demo` for simulation mode
- Event callback wiring between adapter and GUI
- Production-ready entry point for systemd service

### Carousel Positioning Logic

The system uses a 3-stage carousel:
- **Stage 0 (morning)**: Initial position (HOME)
- **Stage 1 (afternoon)**: Advance 1 step (2000ms rotation)
- **Stage 2 (evening)**: Advance 1 more step (2500ms rotation from afternoon)

Dispensing always proceeds morning→afternoon→evening, then returns HOME.

### State Machine

`data/state.json` status values:
- `machine_not_registered`: Show machine registration QR
- `waiting_uid`: Idle, ready for RFID scan
- `kit_not_registered`: Show kit registration QR
- `resolving_uid`: Checking user with backend
- `queue_ready`: Medication queue retrieved
- `moving`: Carousel moving to next time slot
- `dispensing`: Pills being dispensed
- `returning`: Carousel returning to HOME
- `done`: All doses dispensed for today
- `error`: Failure occurred

### Offline Resilience

- Failed dispense reports are appended to `data/offline_reports.jsonl`
- Periodic heartbeat flushes offline queue via `flush_offline()`
- Serial retries: 3 attempts with exponential backoff via `urllib3.Retry`

## Configuration

Edit `config/.env` (create from template if needed):
```bash
TDB_SERVER_BASE_URL=http://your-server:3000
TDB_MACHINE_ID=MACHINE-0001
TDB_SERIAL_PORT=/dev/serial/by-id/usb-Arduino...  # or omit for auto-detect
TDB_BAUDRATE=9600
TDB_DRY_RUN=false
TDB_UID_COOLDOWN_SEC=2.0
TDB_HEARTBEAT_SEC=300
```

## Serial Protocol

Arduino accepts newline-terminated ASCII commands:
- `DISPENSE,<slot>,<count>` → `OK,<slot>,<count>` or `ERR,<reason>`
- `HOME` or `STEP,HOME` → `OK,HOME`
- `STEP,NEXT` → `OK,STEP,NEXT`
- `JOG,<F|B>,<ms>[,<speed>]` → `OK,JOG` (for manual calibration)

Arduino sends unsolicited RFID UIDs as uppercase hex strings (e.g., `6CEFECBF`).

## Troubleshooting

- **Serial not found**: Check `TDB_SERIAL_PORT` or ensure Arduino shows up in `/dev/serial/by-id/`
- **Timeout errors**: Increase timeout in `arduino_link.dispense()` based on pill count
- **Queue format errors**: Server must return `{"queue": [{"time": "morning", "items": [...]}]}`
- **Kit swap during dispensing**: Session lock prevents this; user sees error in logs

---

## 📊 Database Schema

The production database is fully documented in `DATABASE.md`. Key highlights:

**Database Host**: AWS RDS MySQL 8.0.42 at `tdb.cxc48q26c73q.ap-southeast-2.rds.amazonaws.com`

**Core Tables**:
- `users` - User accounts with RFID card mapping (`k_uid` field)
- `user_group` - Family groups that share a dispenser
- `user_group_membership` - Many-to-many user-group relationships
- `machine` - Physical dispenser devices
- `machine_slot` - Slot assignments (slot 1-3) with inventory tracking
- `medicine` - Medicine catalog with prescriptions and supplements
- `schedule` - Weekly recurring schedules (day_of_week + time_of_day)
- `dose_history` - Complete audit trail of all dispensing events

**Local Database Dumps**: SQL schema exports are available in `DBstructure/` directory.

For complete schema documentation, ER diagrams, and sample queries, see `DATABASE.md`.

---

## 🖥️ Backend Server (Local Clone)

The TDB NestJS server has been cloned locally in `tdb_server/TDB_Server/`.

**Quick Start**:
```bash
cd tdb_server/TDB_Server

# Install dependencies
npm install

# Configure environment
cp .env.example .env  # Edit with MySQL credentials

# Run development server
npm run start:dev
```

**Documentation**:
- Server architecture: `tdb_server/INIT.md`
- API changes for Pi: `tdb_server/TDB_Server/API_CHANGES.md`
- Pi setup guide: `tdb_server/TDB_Server/RASPBERRY_PI_SETUP.md`

**Production Server**:
- The production instance runs on AWS EC2 with RDS MySQL
- Connection details in `config/.env` (`TDB_SERVER_BASE_URL`)

---

## 🔄 System Service Configuration

The system can run as a systemd service for automatic startup on boot.

**Current Setup**: Integrated service (`tdb.service`)
- Runs `main.py` which combines GUI + Serial Reader
- Single service manages both components

**Legacy Setup**: Separate services
- `tdb-serial.service` - Serial reader only
- `tdb-gui.service` - GUI only

**Rollback Guide**: To revert to legacy separate services, see `AUTORUN_BACKUP.md`

**Service Commands**:
```bash
# Check status
sudo systemctl status tdb.service

# View logs
sudo journalctl -u tdb.service -f

# Restart
sudo systemctl restart tdb.service
```

---

# 한국어 가이드

## 프로젝트 개요

TDB Dispenser는 약 자동 배출 시스템으로, 다음 컴포넌트로 구성됩니다:
- **라즈베리파이 클라이언트** (Python): RFID 카드 읽기, 백엔드 서버 통신, 시리얼로 Arduino 제어
- **Arduino Mega 펌웨어** (C++/PlatformIO): 서보모터, RFID 리더(MFRC522) 제어 및 약 배출
- **대시보드 GUI** (Tkinter): 실시간 상태 모니터링을 위한 현대적인 2x3 타일 대시보드 및 QR 코드 표시
- **NestJS 서버** (TypeScript): MySQL 데이터베이스를 사용하는 프로덕션 백엔드 (`tdb_server/`에 로컬 클론)
- **Mock 서버** (FastAPI): 로컬 테스트용 백엔드 API 시뮬레이터

시스템은 서보모터로 회전판(carousel)을 돌려 세 시간대(아침/점심/저녁)에 맞춰 약을 배출합니다.

## 개발 환경 설정

```bash
# Python 환경
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 펌웨어 (PlatformIO 필요)
cd firmware
pio run              # 펌웨어 빌드
pio run -t upload    # Arduino Mega에 업로드
pio device monitor   # 시리얼 모니터
```

## 주요 명령어

### 시스템 실행

```bash
# 옵션 1: 통합 시스템 실행 (GUI + 시리얼 리더)
python main.py                    # 프로덕션 모드 (전체화면)
python main.py --demo             # 데모 모드 (윈도우 모드, 시뮬레이션)

# 옵션 2: 컴포넌트 개별 실행 (레거시 모드)
python hwserial/serial_reader.py  # 시리얼 리더만 (Arduino 필요)
python gui/qr_display.py          # 간단한 QR 표시 GUI

# 로컬 테스트용 mock 서버 실행 (개발용)
cd dev
uvicorn mock_server:app --reload --port 8000
```

### 테스트 및 복구

```bash
# 수동 조그 제어 (긴급 복구용)
python scripts/recovery_jog.py --dir F --ms 1000           # 앞으로 1초
python scripts/recovery_jog.py --dir B --ms 500            # 뒤로 0.5초
python scripts/recovery_jog.py --step NEXT                 # 다음 슬롯으로
python scripts/recovery_jog.py --step HOME                 # 홈 위치로

# 펌웨어 명령 직접 테스트
cd firmware
pio device monitor
# 입력: DISPENSE,1,2  또는  STEP,NEXT  또는  HOME
```

## 아키텍처

### 데이터 흐름

```
RFID 카드 → Arduino → 시리얼 → Pi (serial_reader.py) → 백엔드 API (NestJS/MySQL)
                                    ↓
                              상태 파일 (data/state.json)
                                    ↓
                          ┌──────────┴──────────┐
                          ↓                     ↓
                 GUI (qr_display.py)    대시보드 (gui_app.py)
                 (간단한 QR 표시)       (2x3 타일 대시보드)
```

**통합 모드 (main.py)**:
```
RFID 카드 → Arduino → 시리얼 → serial_reader_adapter → 대시보드 GUI (gui_app.py)
                                         ↓
                                   백엔드 API (NestJS/MySQL)
```

### 핵심 컴포넌트

**hwserial/serial_reader.py** - 메인 이벤트 루프
- Arduino로부터 RFID UID 폴링
- 백엔드 API를 호출해 사용자 확인 및 복약 큐 생성
- 배출 시퀀스 조율 (아침→점심→저녁)
- GUI용 상태를 `data/state.json`에 기록
- 세션 잠금으로 배출 중 키트 교체 방지

**hwserial/arduino_link.py** - 시리얼 프로토콜 래퍼
- `open_serial()`: Arduino 포트 자동 탐지, READY 대기
- `dispense(ser, slot, count)`: Arduino에 약 배출 명령
- `step_next(ser)`, `step_home(ser)`: 회전판 위치 제어
- `send_raw(ser, cmd, timeout)`: 저수준 명령/응답 핸들러

**services/api_client.py** - 백엔드 통신
- `check_machine_registered()`: 기기 등록 확인
- `resolve_uid(uid)`: RFID 카드 등록 여부 확인
- `build_queue(machine_id, user_id)`: 복약 스케줄 조회
- `report_dispense()`: 배출 완료 보고
- `heartbeat()`: 주기적 keepalive + 오프라인 리포트 재전송

**config/settings.py** - 설정 로더
- `config/.env` 파일 읽기 (TDB_* 환경변수)
- `SERVER_BASE_URL`, `MACHINE_ID`, `SERIAL_PORT`, `BAUDRATE`
- `DRY_RUN`, `UID_COOLDOWN_SEC`, `HEARTBEAT_SEC`

**firmware/src/main.cpp** - Arduino 펌웨어
- MFRC522 RFID 태그 읽고 UID를 시리얼로 출력
- 명령 처리: `DISPENSE,<slot>,<count>`, `STEP,NEXT`, `HOME`, `JOG,<dir>,<ms>`
- `servos.hpp`로 서보 제어 (타이밍: 아침=0ms, 점심=2000ms, 저녁=4500ms)

**gui/gui_app.py** - 대시보드 GUI (신규)
- 다크 테마의 현대적인 2x3 타일 레이아웃
- 실시간 상태 표시 (시간, 재고, 사용자, 스케줄, 상태, 기기 ID)
- 알림 및 QR 코드용 팝업 오버레이 시스템
- `ui_call()` 메서드를 통한 스레드 안전 UI 업데이트
- 라즈베리파이 터치스크린용 전체화면 지원

**gui/qr_display.py** - 간단한 QR 표시 GUI (레거시)
- 등록용 경량 QR 코드 표시
- 500ms마다 `data/state.json` 폴링
- 기본 상태용 텍스트 표시
- 컴포넌트 개별 실행 시 사용

**hwserial/serial_reader_adapter.py** - GUI 어댑터 (신규)
- serial_reader와 GUI 컴포넌트 연결
- 이벤트 기반 콜백: `on_waiting`, `on_uid`, `on_error`, `on_unregistered`
- UID 디바운싱 (1초 쿨다운)
- 하드웨어 없이 테스트 가능한 데모 모드

**main.py** - 통합 애플리케이션 부트스트랩 (신규)
- 대시보드 GUI + 시리얼 리더를 하나의 프로세스로 통합
- 명령줄 플래그: `--demo` 시뮬레이션 모드용
- 어댑터와 GUI 간 이벤트 콜백 연결
- systemd 서비스용 프로덕션 준비 진입점

### 회전판 위치 로직

시스템은 3단계 회전판을 사용합니다:
- **스테이지 0 (아침)**: 초기 위치 (HOME)
- **스테이지 1 (점심)**: 1스텝 전진 (2000ms 회전)
- **스테이지 2 (저녁)**: 1스텝 추가 전진 (점심에서 2500ms 더 회전)

배출은 항상 아침→점심→저녁 순서로 진행되며, 완료 후 HOME으로 복귀합니다.

### 상태 머신

`data/state.json`의 status 값:
- `machine_not_registered`: 기기 등록 QR 표시
- `waiting_uid`: 대기 중, RFID 스캔 준비
- `kit_not_registered`: 키트 등록 QR 표시
- `resolving_uid`: 백엔드에서 사용자 확인 중
- `queue_ready`: 복약 큐 준비 완료
- `moving`: 회전판 다음 타임 슬롯으로 이동 중
- `dispensing`: 약 배출 중
- `returning`: 회전판 HOME 복귀 중
- `done`: 오늘 모든 복약 완료
- `error`: 오류 발생

### 오프라인 내구성

- 배출 리포트 전송 실패 시 `data/offline_reports.jsonl`에 저장
- 주기적 하트비트 때 `flush_offline()`으로 재전송 시도
- 시리얼 재시도: `urllib3.Retry`로 3회 시도 및 exponential backoff

## 설정

`config/.env` 파일 편집 (필요시 템플릿에서 생성):
```bash
TDB_SERVER_BASE_URL=http://your-server:3000
TDB_MACHINE_ID=MACHINE-0001
TDB_SERIAL_PORT=/dev/serial/by-id/usb-Arduino...  # 또는 생략 시 자동 탐지
TDB_BAUDRATE=9600
TDB_DRY_RUN=false
TDB_UID_COOLDOWN_SEC=2.0
TDB_HEARTBEAT_SEC=300
```

## 시리얼 프로토콜

Arduino는 개행(\n)으로 끝나는 ASCII 명령을 받습니다:
- `DISPENSE,<slot>,<count>` → `OK,<slot>,<count>` 또는 `ERR,<reason>`
- `HOME` 또는 `STEP,HOME` → `OK,HOME`
- `STEP,NEXT` → `OK,STEP,NEXT`
- `JOG,<F|B>,<ms>[,<speed>]` → `OK,JOG` (수동 캘리브레이션용)

Arduino는 RFID UID를 대문자 16진수 문자열로 전송합니다 (예: `6CEFECBF`).

## 문제 해결

- **시리얼 포트를 찾을 수 없음**: `TDB_SERIAL_PORT` 확인 또는 `/dev/serial/by-id/`에 Arduino가 있는지 확인
- **타임아웃 에러**: 약 개수에 따라 `arduino_link.dispense()`의 timeout 증가 필요
- **큐 포맷 에러**: 서버는 반드시 `{"queue": [{"time": "morning", "items": [...]}]}` 형식으로 응답해야 함
- **배출 중 키트 교체**: 세션 잠금이 방지하며, 로그에 에러 기록됨

## 주요 특징

**세션 잠금 메커니즘**
- `_session_user_id`와 `_active_kit_uid`로 배출 세션 관리
- 배출 진행 중에는 다른 RFID 카드 인식을 무시하여 키트 스왑 방지
- 안전한 약 배출 보장

**물리적 맵핑**
- 회전판은 아침(0) → 점심(1) → 저녁(2) 순으로 이동
- 각 단계별 정확한 타이밍으로 서보 제어 (2000ms, 2500ms)
- 모든 배출 완료 후 자동으로 HOME 복귀

**복구 도구**
- `recovery_jog.py`로 회전판 수동 제어 가능
- 긴급 상황에서 물리적 위치 조정 지원

---

## 📊 데이터베이스 스키마

프로덕션 데이터베이스는 `DATABASE.md`에 완전히 문서화되어 있습니다. 주요 내용:

**데이터베이스 호스트**: AWS RDS MySQL 8.0.42 (`tdb.cxc48q26c73q.ap-southeast-2.rds.amazonaws.com`)

**핵심 테이블**:
- `users` - RFID 카드 매핑이 포함된 사용자 계정 (`k_uid` 필드)
- `user_group` - 디스펜서를 공유하는 가족 그룹
- `user_group_membership` - 다대다 사용자-그룹 관계
- `machine` - 물리적 디스펜서 기기
- `machine_slot` - 재고 추적이 포함된 슬롯 할당 (슬롯 1-3)
- `medicine` - 처방약 및 건강기능식품 카탈로그
- `schedule` - 주간 반복 스케줄 (day_of_week + time_of_day)
- `dose_history` - 모든 배출 이벤트의 완전한 감사 추적

**로컬 데이터베이스 덤프**: SQL 스키마 내보내기 파일이 `DBstructure/` 디렉토리에 있습니다.

완전한 스키마 문서, ER 다이어그램, 샘플 쿼리는 `DATABASE.md`를 참조하세요.

---

## 🖥️ 백엔드 서버 (로컬 클론)

TDB NestJS 서버가 `tdb_server/TDB_Server/`에 로컬로 클론되어 있습니다.

**빠른 시작**:
```bash
cd tdb_server/TDB_Server

# 의존성 설치
npm install

# 환경 설정
cp .env.example .env  # MySQL 자격증명으로 편집

# 개발 서버 실행
npm run start:dev
```

**문서**:
- 서버 아키텍처: `tdb_server/INIT.md`
- Pi용 API 변경사항: `tdb_server/TDB_Server/API_CHANGES.md`
- Pi 설정 가이드: `tdb_server/TDB_Server/RASPBERRY_PI_SETUP.md`

**프로덕션 서버**:
- 프로덕션 인스턴스는 RDS MySQL과 함께 AWS EC2에서 실행됩니다
- 연결 세부정보는 `config/.env` (`TDB_SERVER_BASE_URL`)에 있습니다

---

## 🔄 시스템 서비스 설정

시스템은 부팅 시 자동 시작을 위해 systemd 서비스로 실행할 수 있습니다.

**현재 설정**: 통합 서비스 (`tdb.service`)
- GUI + 시리얼 리더를 결합한 `main.py` 실행
- 단일 서비스가 두 컴포넌트를 모두 관리

**레거시 설정**: 개별 서비스
- `tdb-serial.service` - 시리얼 리더만
- `tdb-gui.service` - GUI만

**롤백 가이드**: 레거시 개별 서비스로 되돌리려면 `AUTORUN_BACKUP.md`를 참조하세요

**서비스 명령어**:
```bash
# 상태 확인
sudo systemctl status tdb.service

# 로그 보기
sudo journalctl -u tdb.service -f

# 재시작
sudo systemctl restart tdb.service
```

---

# 백엔드 서버 연동 가이드

## ⚠️ 중요: 서버 API 변경 사항 (2025-11-11 업데이트)

서버가 **통합 서버 아키텍처**로 재편되었습니다. 라즈베리파이 전용 API가 `/dispenser` 경로로 통합되었으며, 기존 클라이언트 코드는 **URL만 변경하면 호환**됩니다.

**주요 변경사항**:
- 라즈베리파이 API: `/dispenser/*` 경로로 통합
- 모바일 앱 API: `/auth`, `/users`, `/medicine` 등 (JWT 인증 필수)
- 기존 엔드포인트는 호환성 유지 (일부는 `/dispenser`로 이동 예정)

---

## 서버 개요

**저장소**: https://github.com/wantraiseapomeranian/TDB_Server

**기술 스택**:
- **프레임워크**: NestJS 11.0.1 (TypeScript)
- **데이터베이스**: MySQL + TypeORM 0.3.24
- **인증**: 이중 구조 (모바일 앱: JWT, 라즈베리파이: 인증 없음)
- **언어**: TypeScript 5.7.3
- **배포**: Docker Compose, AWS EC2/RDS 지원

**아키텍처 특징**:
- **통합 서버**: React Native 앱 + 라즈베리파이 하드웨어 동시 지원
- **경로 분리**: 모바일(`/auth`, `/users`) vs 하드웨어(`/dispenser`)
- **호환성**: 기존 Python 클라이언트 코드 100% 호환 (URL만 변경)

---

## 주요 API 엔드포인트

### 옵션 A: 기존 API (호환성 유지 중)

**현재 클라이언트 코드가 사용 중인 엔드포인트입니다.**

#### 1. 기기 관리 (`/machine`)

```
GET  /machine/check?machine_id=<id>
  → 기기 등록 여부 확인
  → 응답: { registered: boolean }

POST /machine/heartbeat
  → Body: { machine_id, status?, ts? }
  → 주기적 상태 전송 (HEARTBEAT_SEC 간격)
```

클라이언트 코드: `services/api_client.py:check_machine_registered()`, `heartbeat()`

#### 2. RFID 인증 (`/rfid`)

```
POST /rfid/resolve
  → Body: { uid: string }
  → RFID 카드 UID로 사용자 식별
  → 응답: { registered, user_id, group_id, took_today, ... }
```

클라이언트 코드: `services/api_client.py:resolve_uid()`

#### 3. 배출 큐 생성 (`/queue`)

```
POST /queue/build
  → Body: {
      machine_id: string,
      user_id: string,
      weekday?: string,      # "mon"..."sun"
      client_ts?: number,    # 초 단위 타임스탬프
      tz_offset_min?: number # KST = 540 (UTC+9)
    }
  → 응답: {
      status: "ok",
      queue: [
        {
          time: "morning" | "afternoon" | "evening",
          items: [{ slot, medi_id, count }]
        }
      ]
    }
```

**중요**: 응답 구조가 시간대별 그룹화로 변경되었습니다. `slot` 필드가 각 item에 포함됩니다.

클라이언트 코드: `services/api_client.py:build_queue()`

#### 4. 배출 완료 보고 (`/dispense`)

```
POST /dispense/report
  → Body: {
      machine_id: string,
      user_id: string,
      time: "morning" | "afternoon" | "evening",
      items: [{ medi_id, count }],
      result: "completed" | "partial" | "failed",
      client_tx_id?: string
    }
  → 각 시간대 배출 완료 시마다 개별 전송
```

클라이언트 코드: `services/api_client.py:report_dispense()`

---

### 옵션 B: 신규 통합 API (`/dispenser` 경로)

**서버 측에서 추가된 라즈베리파이 전용 통합 엔드포인트입니다.**

#### 1. RFID 자동 배출 (신규)

```
POST /dispenser/rfid-auto-dispense
  → Body: { k_uid: string, machine_id: string }
  → RFID 태그 인식 시 자동으로 오늘의 스케줄에 따라 약 배출
  → 응답: 배출 목록 + 실행 결과
```

**특징**: UID 검증 + 스케줄 조회 + 배출 지시를 하나의 API로 통합

#### 2. 기기 상태 조회

```
GET /dispenser/machine-status?machine_id=<id>
GET /dispenser/status/{machine_id}
  → 기기 정보 조회 (두 가지 경로 모두 지원)
```

#### 3. 배출 목록 조회

```
GET /dispenser/dispense-list?machine_id=<id>&userId=<id>
  → 특정 사용자의 배출 목록 조회
```

#### 4. 슬롯 상태 조회

```
GET /dispenser/slot-status?machine_id=<id>
  → 기기별 슬롯 정보 및 약품 잔량 확인
```

#### 5. 기기별 사용자 목록

```
GET /dispenser/users/by-machine?machine_id=<id>
  → 해당 기기에 연결된 사용자 목록
```

#### 6. 기기별 스케줄 조회

```
GET /dispenser/schedules-by-date?machine_id=<id>&date=YYYY-MM-DD
  → 특정 날짜의 스케줄 조회
```

---

## 마이그레이션 가이드

### 현재 클라이언트 코드 유지 (권장)

**변경 사항**: `config/.env`의 서버 URL만 업데이트

```bash
# 기존
TDB_SERVER_BASE_URL=http://localhost:8000

# 신규 통합 서버
TDB_SERVER_BASE_URL=http://your-server-ip:3000
```

기존 `/machine`, `/rfid`, `/queue`, `/dispense` API는 호환성 유지 중입니다.

### 향후 `/dispenser` API 도입 (선택)

서버 문서(`API_CHANGES.md`)에 따르면 다음 API들이 추가 제공됩니다:
- `/dispenser/verify-uid` (← `/rfid/resolve` 대체)
- `/dispenser/dispense-list` (← `/queue/build` 대체)
- `/dispenser/dispense-result` (← `/dispense/report` 대체)
- `/dispenser/confirm` (새로운 복용 완료 확인)

**주의**: 현재 일부 엔드포인트는 구현 중일 수 있습니다. 프로덕션 환경에서는 기존 API 사용을 권장합니다.

## 서버 모듈 구조

```
src/
├── auth/           # JWT 인증 (모바일 앱용)
├── users/          # 사용자 관리
├── family/         # 가족/그룹 관리
├── device/         # 모바일 기기
├── dispenser/      # ★★ 라즈베리파이 통합 모듈 (신규)
├── machine/        # ★ 디스펜서 기기 (기존 API, 호환성 유지)
├── rfid/           # ★ RFID 태그 (기존 API, 호환성 유지)
├── queue/          # ★ 배출 큐 생성 (기존 API, 호환성 유지)
├── dispense/       # ★ 배출 기록 (기존 API, 호환성 유지)
├── dose-history/   # 복약 이력
├── medicine/       # 의약품 정보
├── supplement/     # 건강기능식품
├── schedule/       # 복약 스케줄
├── notification/   # 알림
└── entities/       # 공통 엔티티
```

**★ 표시**: 기존 Pi 클라이언트 API (현재 사용 중)
**★★ 표시**: 신규 통합 API (`/dispenser/*` 경로)

## 인증 및 보안

**이중 인증 구조**:

| 클라이언트 | 인증 방식 | 특징 |
|----------|----------|------|
| **모바일 앱** | JWT Bearer Token | 사용자 로그인 필수 |
| **라즈베리파이** | 인증 없음 | RFID UID 기반, IP 보안 권장 |

**기존 API (`/machine`, `/rfid`, `/queue`, `/dispense`)**:
- 현재 대부분 `@UseGuards` 주석 처리 상태
- 라즈베리파이 클라이언트는 **인증 없이** 호출 가능

**신규 API (`/dispenser/*`)**:
- 컨트롤러에는 `@UseGuards(AccessTokenGuard)` 설정되어 있음
- 실제 인증 활성화 여부는 서버 설정에 따라 다름

**보안 권장사항**:
1. 프로덕션 환경에서는 라즈베리파이 IP 화이트리스트 설정
2. 방화벽으로 `/dispenser` 경로 접근 제한
3. HTTPS/TLS 사용 필수 (HTTP는 개발용만)

**향후 인증 활성화 시 대응**:
- 서버에서 JWT 인증을 활성화할 경우:
  1. 기기 등록 시 토큰 발급 API 호출
  2. `services/api_client.py`의 `_session`에 `Authorization: Bearer <token>` 헤더 추가
  3. 토큰 만료 시 자동 재발급 로직 구현

## 데이터 흐름

```
1. 기기 시작
   → GET /machine/check (등록 확인)
   → 미등록 시 QR 표시 (machine_not_registered)

2. RFID 스캔
   → POST /rfid/resolve (사용자 확인)
   → 미등록 키트: QR 표시 (kit_not_registered)
   → took_today=1: 이미 복약 완료

3. 큐 생성
   → POST /queue/build (오늘의 스케줄 조회)
   → 요일별/시간대별 배출 항목 수신

4. 배출 진행
   → 아침/점심/저녁 각각 완료 시:
     POST /dispense/report

5. 주기적 하트비트
   → POST /machine/heartbeat (5분마다)
   → 오프라인 리포트 재전송 시도
```

## 로컬 테스트

### Mock 서버 (개발 초기)

클라이언트 저장소의 `dev/mock_server.py`:
- FastAPI 기반 간소화된 테스트 서버
- 실제 서버와 응답 형식 다름
- **개발 초기 단계에서만 사용**

```bash
cd dev
uvicorn mock_server:app --reload --port 8000
```

### 실제 NestJS 서버 실행

```bash
cd TDB_Server/TDB_Server

# 의존성 설치
npm install

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집 (MySQL 연결 정보 등)

# 개발 모드 (hot reload)
npm run start:dev

# 프로덕션 빌드 및 실행
npm run build
npm run start:prod
```

### Docker Compose (권장)

서버 + MySQL + phpMyAdmin 통합 스택:

```bash
cd TDB_Server/TDB_Server

# 컨테이너 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

**접속 정보**:
- 서버: http://localhost:3000
- phpMyAdmin: http://localhost:8080

### AWS 클라우드 배포

서버 저장소에 자동화 스크립트 제공:
- `deploy-ec2.sh`: EC2 인스턴스 배포
- `setup-rds.sh`: RDS MySQL 설정
- `ecosystem.config.js`: PM2 프로세스 관리

상세 가이드: `TDB_Server/EC2_RDS_SETUP.md` 참조

## 환경 변수 설정

서버 URL 및 기기 ID는 `config/.env`에 설정:
```bash
TDB_SERVER_BASE_URL=http://your-nest-server:3000
TDB_MACHINE_ID=MACHINE-0001
```

**주의사항**:
- 서버 포트는 기본적으로 3000 (NestJS 기본값)
- Mock 서버는 8000 포트 사용
- 프로덕션 환경에서는 HTTPS 사용 권장

## API 버전 관리

현재 API 엔드포인트는 버전 접두사 없음:
- `/machine/check` (버전 없음)
- 향후 `/v1/machine/check` 형태로 변경 가능성 있음
- 서버 업데이트 시 클라이언트 `api_client.py`의 URL 경로 확인 필요

## 에러 처리

**서버 응답 형식**:
- 성공: HTTP 200/201 + JSON body
- 실패: HTTP 4xx/5xx + 에러 상세 정보

**클라이언트 대응**:
- `requests.raise_for_status()` 사용 중
- 네트워크 오류 시 `offline_reports.jsonl`에 적재 후 재시도
- 3회 자동 재시도 (exponential backoff)

## 데이터베이스 스키마

서버는 다음 엔티티를 관리:
- **Machine**: 기기 정보 (machine_id, 슬롯 설정, 펌웨어 버전)
- **User**: 사용자 정보 (user_id, family_group)
- **RFID**: 카드 등록 (uid ↔ user_id 매핑)
- **Schedule**: 복약 스케줄 (요일별/시간대별)
- **DoseHistory**: 배출 이력 (dispense report 저장)
- **Medicine/Supplement**: 약품/영양제 정보
- **MachineSlot**: 기기별 슬롯-약품 매핑

## 문제 해결

**Queue format errors**:
- 서버 응답이 `{"queue": [...]}` 형식이 아닐 경우 발생
- `queue/queue.service.ts`의 `BuildQueueResponseDto` 확인 필요

**RFID resolve 실패**:
- 서버 DB에 uid가 등록되어 있는지 확인
- 응답에 `registered: true` 포함되어야 함

**Machine not registered**:
- 서버 DB의 Machine 테이블에 해당 machine_id 존재 여부 확인
- `/machine/check` 엔드포인트 로그 확인

**Heartbeat 실패**:
- 폴백 경로 시도 (`/machine/heartbeat` → `/machines/heartbeat`)
- 두 경로 모두 404면 서버 라우팅 설정 확인

---

# 백엔드 서버 연동 가이드 (한국어)

## ⚠️ 중요: 서버 API 변경 사항 (2025-11-11 업데이트)

서버가 **통합 서버 아키텍처**로 전면 개편되었습니다. 라즈베리파이 전용 API가 `/dispenser` 경로로 통합되었으며, 기존 클라이언트 코드는 **서버 URL만 변경하면 그대로 사용 가능**합니다.

**주요 변경사항**:
- 라즈베리파이 API: `/dispenser/*` 경로로 통합
- 모바일 앱 API: `/auth`, `/users`, `/medicine` 등 (JWT 인증 필수)
- 기존 엔드포인트 호환성 유지 중 (점진적 이전 예정)

---

## 서버 개요

**저장소**: https://github.com/wantraiseapomeranian/TDB_Server

**기술 스택**:
- **프레임워크**: NestJS 11.0.1 (TypeScript)
- **데이터베이스**: MySQL + TypeORM 0.3.24
- **인증**: 이중 구조 (모바일: JWT, 라즈베리파이: 없음)
- **언어**: TypeScript 5.7.3
- **배포**: Docker Compose, AWS EC2/RDS 지원

**아키텍처 특징**:
- **통합 서버**: React Native 앱 + 라즈베리파이 동시 지원
- **경로 분리**: 모바일용(`/auth`, `/users`) vs 하드웨어용(`/dispenser`)
- **100% 호환**: 기존 Python 클라이언트 코드 수정 불필요 (URL만 변경)

---

## 주요 API 엔드포인트

### 옵션 A: 기존 API (현재 사용 중)

**현재 클라이언트(`services/api_client.py`)가 사용하는 엔드포인트입니다.**

#### 1. 기기 관리 (`/machine`)

```
GET  /machine/check?machine_id=<id>
  → 기기 등록 여부 확인
  → 응답: { registered: boolean }

POST /machine/heartbeat
  → Body: { machine_id, status?, ts? }
  → 주기적 상태 전송 (5분마다)
```

#### 2. RFID 인증 (`/rfid`)

```
POST /rfid/resolve
  → Body: { uid: string }
  → RFID 카드 UID로 사용자 식별
  → 응답: { registered, user_id, group_id, took_today, ... }
```

#### 3. 배출 큐 생성 (`/queue`)

```
POST /queue/build
  → Body: {
      machine_id: string,
      user_id: string,
      weekday?: string,      # "mon"..."sun"
      client_ts?: number,    # 초 단위 타임스탬프
      tz_offset_min?: number # KST = 540 (UTC+9)
    }
  → 응답: {
      status: "ok",
      queue: [
        {
          time: "morning" | "afternoon" | "evening",
          items: [{ slot, medi_id, count }]
        }
      ]
    }
```

**중요**: 응답 구조가 시간대별 그룹화로 변경되었습니다. 각 item에 `slot` 필드가 포함됩니다.

#### 4. 배출 완료 보고 (`/dispense`)

```
POST /dispense/report
  → Body: {
      machine_id: string,
      user_id: string,
      time: "morning" | "afternoon" | "evening",
      items: [{ medi_id, count }],
      result: "completed" | "partial" | "failed"
    }
```

---

### 옵션 B: 신규 통합 API (`/dispenser` 경로)

**서버 측에서 추가된 라즈베리파이 전용 통합 엔드포인트입니다.**

#### 1. RFID 자동 배출 (신규 기능)

```
POST /dispenser/rfid-auto-dispense
  → Body: { k_uid: string, machine_id: string }
  → RFID 태그 인식 시 자동으로 오늘 스케줄 조회 + 약 배출
  → UID 검증 + 스케줄 조회 + 배출 지시를 하나의 API로 통합
```

#### 2. 기기 상태 조회

```
GET /dispenser/machine-status?machine_id=<id>
GET /dispenser/status/{machine_id}
  → 기기 정보 조회 (두 가지 경로 모두 지원)
```

#### 3. 배출 목록 조회

```
GET /dispenser/dispense-list?machine_id=<id>&userId=<id>
  → 특정 사용자의 배출 목록
```

#### 4. 슬롯 상태 조회

```
GET /dispenser/slot-status?machine_id=<id>
  → 슬롯별 약품 정보 및 잔량 확인
```

#### 5. 기기별 사용자 목록

```
GET /dispenser/users/by-machine?machine_id=<id>
  → 해당 기기에 연결된 사용자 목록
```

#### 6. 기기별 스케줄 조회

```
GET /dispenser/schedules-by-date?machine_id=<id>&date=YYYY-MM-DD
  → 특정 날짜의 스케줄
```

---

## 마이그레이션 가이드

### 현재 클라이언트 코드 유지 (권장)

**변경 필요 사항**: `config/.env`의 서버 주소만 수정

```bash
# 기존 (Mock 서버)
TDB_SERVER_BASE_URL=http://localhost:8000

# 신규 (통합 서버)
TDB_SERVER_BASE_URL=http://your-server-ip:3000
```

기존 `/machine`, `/rfid`, `/queue`, `/dispense` API는 호환성이 유지됩니다.

### 향후 `/dispenser` API 전환 (선택사항)

서버 문서(`RASPBERRY_PI_SETUP.md`, `API_CHANGES.md`)에서 안내하는 새로운 API:
- `/dispenser/verify-uid` (← `/rfid/resolve` 대체)
- `/dispenser/dispense-list` (← `/queue/build` 대체)
- `/dispenser/dispense-result` (← `/dispense/report` 대체)
- `/dispenser/confirm` (새로운 복용 완료 확인 API)

**주의**: 일부 엔드포인트는 구현 진행 중일 수 있습니다. 프로덕션에서는 기존 API 사용을 권장합니다.

## 서버 모듈 구조

```
src/
├── auth/           # JWT 인증 (모바일 앱용)
├── users/          # 사용자 관리
├── family/         # 가족/그룹 관리
├── device/         # 모바일 앱 기기
├── dispenser/      # ★★ 라즈베리파이 통합 모듈 (신규)
├── machine/        # ★ 디스펜서 기기 (기존 API)
├── rfid/           # ★ RFID 태그 (기존 API)
├── queue/          # ★ 배출 큐 생성 (기존 API)
├── dispense/       # ★ 배출 기록 (기존 API)
├── dose-history/   # 복약 이력
├── medicine/       # 의약품 정보
├── supplement/     # 건강기능식품
├── schedule/       # 복약 스케줄
├── notification/   # 알림
└── entities/       # 공통 엔티티
```

**★ 표시**: 기존 Pi 클라이언트 API (호환성 유지)
**★★ 표시**: 신규 통합 API (`/dispenser/*` 경로)

## 인증 및 보안

**이중 인증 구조 (2025년 기준)**:

| 클라이언트 | 인증 방식 | 설명 |
|----------|----------|------|
| **모바일 앱** | JWT Bearer Token | 사용자 로그인 필수 |
| **라즈베리파이** | 인증 없음 | RFID UID 기반, IP 보안 권장 |

**기존 API (`/machine`, `/rfid`, `/queue`, `/dispense`)**:
- 현재 대부분의 기기 API에서 `@UseGuards` 주석 처리
- 라즈베리파이 클라이언트는 **인증 없이 호출 가능**

**신규 API (`/dispenser/*`)**:
- 컨트롤러에 `@UseGuards(AccessTokenGuard)` 설정됨
- 실제 활성화 여부는 서버 구성에 따라 다름

**보안 권장사항**:
1. **프로덕션**: 라즈베리파이 IP를 화이트리스트에 등록
2. **방화벽**: `/dispenser` 경로에 접근 제어 적용
3. **HTTPS**: 반드시 TLS/SSL 사용 (HTTP는 개발 환경에서만)

**향후 인증 활성화 시 대응**:
서버에서 JWT 인증을 활성화할 경우:
1. 기기 등록 시 토큰 발급 API 호출
2. `services/api_client.py`의 `_session`에 `Authorization: Bearer <token>` 헤더 추가
3. 토큰 만료 시 자동 재발급 로직 구현 (`/auth/refresh`)

## 데이터 흐름

```
1. 시스템 부팅
   → GET /machine/check (기기 등록 확인)
   → 미등록: QR 코드 표시 (machine_not_registered)
   → 등록됨: waiting_uid 상태로 전환

2. RFID 카드 스캔
   → POST /rfid/resolve (사용자/키트 확인)
   → 미등록 키트: QR 코드 표시 (kit_not_registered)
   → took_today=1: "오늘 이미 복약 완료" 안내 (done)

3. 배출 큐 생성
   → POST /queue/build (오늘의 복약 스케줄 조회)
   → 요일별/시간대별 배출 항목 리스트 수신
   → 빈 큐: "오늘 실행할 항목 없음" 안내

4. 약 배출 진행
   → 아침 배출 완료: POST /dispense/report (time="morning")
   → 점심 배출 완료: POST /dispense/report (time="afternoon")
   → 저녁 배출 완료: POST /dispense/report (time="evening")
   → 각 시간대마다 개별 리포트 전송

5. 주기적 하트비트
   → POST /machine/heartbeat (5분마다, 설정 가능)
   → 오프라인 큐에 쌓인 리포트 재전송 시도 (flush_offline)
```

## 로컬 테스트

### Mock 서버 (개발 초기용)

클라이언트 저장소의 `dev/mock_server.py`:
- FastAPI 기반 간단한 테스트 서버
- 실제 서버와 응답 형식이 다름
- **개발 초기 단계에서만 사용**

```bash
cd dev
uvicorn mock_server:app --reload --port 8000
```

### 실제 NestJS 서버 실행

```bash
cd TDB_Server/TDB_Server

# 의존성 설치
npm install

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집 (MySQL 연결 정보 등)

# 개발 모드 (hot reload)
npm run start:dev

# 프로덕션 빌드 및 실행
npm run build
npm run start:prod
```

### Docker Compose (권장)

서버 + MySQL + phpMyAdmin 통합 스택:

```bash
cd TDB_Server/TDB_Server

# 컨테이너 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

**접속 정보**:
- 서버: http://localhost:3000
- phpMyAdmin: http://localhost:8080 (데이터베이스 관리)

### AWS 클라우드 배포

서버 저장소에 자동화 스크립트가 제공됩니다:
- `deploy-ec2.sh`: EC2 인스턴스 자동 배포
- `setup-rds.sh`: RDS MySQL 설정
- `ecosystem.config.js`: PM2 프로세스 관리

상세 가이드: 서버 저장소의 `EC2_RDS_SETUP.md` 참조

## 환경 변수 설정

`config/.env` 파일에서 서버 연결 설정:
```bash
TDB_SERVER_BASE_URL=http://your-nest-server:3000
TDB_MACHINE_ID=MACHINE-0001
TDB_DEVICE_UID=DEVICE-UUID-001  # 기기 등록용 UID
```

**포트 관련**:
- NestJS 서버 기본 포트: **3000**
- Mock 서버 (FastAPI) 포트: **8000**
- 프로덕션 환경: HTTPS (443) 사용 강력 권장

## API 버전 관리

**현재 상태**:
- 버전 접두사 없음: `/machine/check`, `/rfid/resolve` 등
- 향후 버전 관리 도입 가능성: `/v1/machine/check`, `/v2/...`

**서버 업데이트 시 주의**:
- API 경로 변경 시 `services/api_client.py`의 `_url()` 함수 수정 필요
- 서버 담당자와 API 변경 사항 사전 공유 필수

## 에러 처리 전략

**서버 응답 형식**:
- 성공: HTTP 200 (GET), 201 (POST) + JSON body
- 실패: HTTP 4xx (클라이언트 오류), 5xx (서버 오류) + 에러 상세 정보

**클라이언트 대응 로직**:
- `requests.raise_for_status()` 사용 → HTTP 오류 시 예외 발생
- 네트워크 오류/서버 다운: `data/offline_reports.jsonl`에 리포트 적재
- 하트비트 때마다 `flush_offline()` 호출 → 재전송 시도
- 자동 재시도: 3회, exponential backoff (0.5s 간격)

## 데이터베이스 스키마

서버가 관리하는 주요 엔티티:

| 엔티티 | 설명 |
|--------|------|
| **Machine** | 기기 정보 (machine_id, 슬롯 구성, 펌웨어 버전) |
| **User** | 사용자 계정 (user_id, 가족 그룹 소속) |
| **RFID** | RFID 카드 등록 (uid ↔ user_id 매핑) |
| **Schedule** | 복약 스케줄 (요일/시간대/약품) |
| **DoseHistory** | 배출 이력 (dispense report 저장) |
| **Medicine** | 의약품 마스터 정보 |
| **Supplement** | 건강기능식품 정보 |
| **MachineSlot** | 기기별 슬롯-약품 매핑 (물리적 배치) |

## 문제 해결

### Queue format errors
**증상**: `serial_reader.py`에서 "invalid queue format" 에러
**원인**: 서버 응답이 `{"queue": [...]}` 형식이 아님
**해결**:
- 서버 `queue/queue.service.ts`의 `BuildQueueResponseDto` 확인
- 응답에 `queue` 키가 있고, 배열인지 확인
- 클라이언트 `api_client.py:build_queue()` 파싱 로직 검토

### RFID resolve 실패
**증상**: 카드를 스캔해도 "미등록" 처리
**원인**: 서버 DB에 해당 uid가 없거나, 응답 형식 불일치
**해결**:
- MySQL에서 `SELECT * FROM rfid WHERE uid = '6CEFECBF'` 확인
- 서버 응답에 `registered: true` 포함되는지 확인
- 서버 로그에서 `/rfid/resolve` 요청 로그 확인

### Machine not registered
**증상**: 부팅 시 계속 기기 등록 QR 표시
**원인**: 서버 DB의 Machine 테이블에 해당 machine_id 미등록
**해결**:
- MySQL: `SELECT * FROM machine WHERE machine_id = 'MACHINE-0001'`
- 관리자 페이지에서 기기 등록 수행
- `/machine/check` 엔드포인트 로그 확인

### Heartbeat 실패
**증상**: 로그에 "HB failed" 반복
**원인**: 서버 다운 또는 라우팅 오류
**해결**:
- 클라이언트는 자동으로 폴백 시도: `/machine/heartbeat` → `/machines/heartbeat`
- 두 경로 모두 404면 서버의 `machine.controller.ts` 라우팅 확인
- 네트워크 연결 상태 확인: `ping <server-ip>`

### 오프라인 리포트 쌓임
**증상**: `data/offline_reports.jsonl` 파일 계속 커짐
**원인**: 서버 접속 불가 상태 지속
**해결**:
- 서버 재시작 후 자동으로 하트비트 때 재전송됨
- 수동 재전송: 코드에서 `flush_offline()` 직접 호출
- 파일 삭제 후 재시작 (데이터 손실 주의)

## 서버 개발 시 유의사항

**클라이언트 호환성 유지**:
1. API 응답 형식 변경 시 클라이언트 `api_client.py` 수정 필요
2. 필수 필드 추가 시 기존 클라이언트와 호환성 고려
3. 엔드포인트 경로 변경 시 사전 공지 필수

**요일 처리 정확성**:
- 클라이언트가 `client_ts`와 `tz_offset_min` 전송하도록 권장
- 서버 시간과 클라이언트 시간 불일치 시 잘못된 스케줄 조회 가능
- 타임존 처리 로직 테스트 필수 (한국 UTC+9)

**에러 응답 일관성**:
- 모든 에러는 일관된 형식으로 반환: `{ error: string, message: string, statusCode: number }`
- 클라이언트가 `raise_for_status()` 사용하므로 HTTP 상태 코드 정확히 설정