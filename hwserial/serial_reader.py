import os
import time
import logging
from logging.handlers import RotatingFileHandler
import json
from pathlib import Path
from datetime import datetime, timedelta
from config import settings
from hwserial.arduino_link import (
    open_serial,
    read_uid_once,
    dispense,
    step_next,
    step_home,
    step_next_n
)
from services.api_client import (
    check_machine_registered,
    resolve_uid,
    build_queue,
    report_dispense,
    heartbeat,
    get_users_for_machine
)

# 세션 락 & 키트 고정
_session_user_id = None
_active_kit_uid = None

# 중복 UID 쿨다운용 상태
_last_uid = None
_last_ts = 0.0

# ---------------------------
# 로깅 설정
# ---------------------------
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("serial_reader")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("logs/serial_reader.log", maxBytes=2_000_000, backupCount=3)
fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(fmt)
logger.addHandler(handler)

def logi(msg):
    print(msg)
    logger.info(msg)

def loge(msg):
    print(msg)
    logger.error(msg)

# ---------------------------
# 오프라인 적치 & 상태 파일
# ---------------------------
STATE_PATH = Path("data/state.json")
OFFLINE_PATH = Path("data/offline_reports.jsonl")
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
OFFLINE_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------
# 헬퍼 함수들
# ---------------------------
def _t():
    """타이밍 측정용 시작 시간"""
    return time.monotonic()

def _dt(t0):
    """경과 시간 포맷팅 (ms)"""
    return f"{(time.monotonic() - t0) * 1000:.0f}ms"

def _time_bucket_now() -> str:
    """현재 시각 기준으로 서버 보고용 time 키 산출"""
    h = datetime.now().hour
    if 5 <= h < 11:
        return "morning"
    if 11 <= h < 17:
        return "afternoon"
    return "evening"

def get_current_time_slot() -> tuple:
    """
    현재 시간대 판별 및 배출 가능 여부 확인

    Returns:
        (time_slot, message)
        - time_slot: "morning" | "afternoon" | "evening" | None
        - message: 사용자 안내 메시지

    시간대:
        - 아침: 06:00 ~ 12:00
        - 점심: 12:00 ~ 18:00
        - 저녁: 18:00 ~ 00:00 (24:00)
        - 불가: 00:00 ~ 06:00
    """
    h = datetime.now().hour

    # 아침: 06:00 ~ 12:00
    if 6 <= h < 12:
        return "morning", "아침 배출 시간입니다"

    # 점심: 12:00 ~ 18:00
    elif 12 <= h < 18:
        return "afternoon", "점심 배출 시간입니다"

    # 저녁: 18:00 ~ 00:00 (24:00)
    elif 18 <= h < 24:
        return "evening", "저녁 배출 시간입니다"

    # 배출 불가: 00:00 ~ 06:00
    else:
        return None, "약물 복용 시간대가 아닙니다 (배출 가능 시간: 06:00~24:00)"

def filter_phases_by_time(phases: list, current_slot: str) -> list:
    """
    현재 시간대에 따라 배출할 시간대 필터링

    Args:
        phases: 서버에서 받은 전체 큐 [{"time": "morning", "items": [...]}, ...]
        current_slot: 현재 시간대 ("morning" | "afternoon" | "evening")

    Returns:
        필터링된 phases 리스트

    배출 규칙:
        - 아침(06:00~12:00): morning, afternoon, evening 모두 배출
        - 점심(12:00~18:00): afternoon, evening 배출
        - 저녁(18:00~00:00): evening만 배출
    """
    if current_slot == "morning":
        # 아침 시간대 → 모든 시간대 배출
        allowed = ["morning", "afternoon", "evening"]
    elif current_slot == "afternoon":
        # 점심 시간대 → 점심, 저녁 배출
        allowed = ["afternoon", "evening"]
    elif current_slot == "evening":
        # 저녁 시간대 → 저녁만 배출
        allowed = ["evening"]
    else:
        # 배출 불가 시간대
        return []

    # 허용된 시간대만 필터링
    filtered = [p for p in phases if p.get("time") in allowed]
    return filtered

def _stage_for_time_key(time_key: str) -> int:
    """
    물리 맵:
      stage 0 : 아침(초기 위치)
      stage 1 : 점심 (앞으로 2000ms → STEP_NEXT 1회)
      stage 2 : 저녁 (점심에서 추가로 2500ms → STEP_NEXT 1회)
    """
    return {"morning": 0, "afternoon": 1, "evening": 2}.get(time_key, 0)

def write_state(status: str, **kwargs):
    """GUI가 읽을 state.json 파일 업데이트"""
    state = {
        "status": status,
        "last_uid": kwargs.get("last_uid"),
        "phase": kwargs.get("phase"),
        "progress": kwargs.get("progress", {}),
        "error": kwargs.get("error"),
        "ts": time.time(),
    }
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)

def store_offline(payload: dict):
    """서버 전송 실패 시 JSONL로 1줄 적치"""
    with OFFLINE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    logger.info(f"[OFFLINE] stored -> {payload.get('time')} items={len(payload.get('items', []))}")

def flush_offline() -> int:
    """적치분 재전송. 성공 건수 반환"""
    if not OFFLINE_PATH.exists():
        return 0
    sent = 0
    keep: list[str] = []

    with OFFLINE_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                # report_dispense를 직접 호출
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

    with OFFLINE_PATH.open("w", encoding="utf-8") as f:
        for line in keep:
            f.write(line + "\n")

    return sent

def process_queue(machine_id: str, user_id: str, phases: list, ser, adapter=None):
    """
    시간대별로 회전판을 이동하며 약을 배출하는 핵심 로직
    phases: [{"time": "morning", "items": [...]}, ...]
    """
    progress = {"morning": False, "afternoon": False, "evening": False}
    all_ok = True
    current_stage = 0  # 아침(초기)에서 시작

    # 필수: 아침→점심→저녁 순으로 정렬
    order = {"morning": 0, "afternoon": 1, "evening": 2}
    phases = sorted(phases, key=lambda p: order.get(p.get("time", ""), 99))

    for phase in phases:
        time_key = phase.get("time", "")  # "morning" | "afternoon" | "evening"
        items = phase.get("items", [])
        if not items:
            continue

        # 1) 목표 스테이지로 이동
        target = _stage_for_time_key(time_key)
        if target < current_stage:
            # 뒤로 가야 하면 HOME으로 리셋 후 다시 전진
            logi(f"  [RESET] Returning to HOME before moving to {time_key}")
            ok, msg = step_home(ser)
            logi(f"  HOME(reset): {msg}")
            if not ok:
                all_ok = False
            current_stage = 0

        need = target - current_stage
        if need > 0:
            # ★ 이동 시작 알림
            write_state(status="moving", last_uid=_active_kit_uid, phase=time_key, progress=progress)
            if adapter:
                adapter.notify_status_update(3, f"{time_key} 위치로 이동 중...")

            tmv = _t()
            logi(f"  [MOVE] stage {current_stage} → {target} ({time_key})")
            ok, msg = step_next_n(ser, need)
            logi(f"  STEP: {msg} [{_dt(tmv)}]")
            if not ok:
                all_ok = False
                loge(f"[ERR] Failed to move carousel: {msg}")
                if adapter:
                    adapter.notify_error(f"회전판 이동 실패: {msg}")
                break
            current_stage = target

        # ★ 배출 시작 알림
        write_state(status="dispensing", last_uid=_active_kit_uid, phase=time_key, progress=progress)

        # 2) 해당 시간대 아이템 전부 배출
        phase_ok = True
        for it in items:
            slot = int(it.get("slot", 1))
            count = int(it.get("count", 1))

            if adapter:
                adapter.notify_status_update(3, f"{time_key} - 슬롯 {slot}에서 {count}개 배출 중...")

            logi(f"  [DISPENSE] {time_key} - slot {slot}, count {count}")
            ok, msg = dispense(ser, slot, count) if not settings.DRY_RUN else (True, "OK,DRY")
            logi(f"  -> {msg}")

            if not ok:
                loge(f"[FAIL] dispense failed for slot {slot}: {msg}")
                if adapter:
                    adapter.notify_error(f"슬롯 {slot} 배출 실패!")
                phase_ok = False
                # 재시도 1회
                if not settings.DRY_RUN:
                    logi(f"  [RETRY] Retrying slot {slot}...")
                    ok2, msg2 = dispense(ser, slot, count)
                    logi(f"  (retry)-> {msg2}")
                    if ok2:
                        phase_ok = True

            time.sleep(0.1)

        # 3) 시간대별 서버 리포트 (slot 정보 포함)
        payload_items = [
            {
                "medi_id": it.get("medi_id"),
                "slot": int(it.get("slot", 1)),
                "count": int(it.get("count", 1))
            }
            for it in items if it.get("medi_id")
        ]

        # 3) 시간대별 서버 리포트 (오프라인 처리 포함)
        if payload_items:
            result_status = "completed" if phase_ok else "partial"
            payload = {
                "machine_id": machine_id,
                "user_id": user_id,
                "time": time_key,
                "items": payload_items,
                "result": result_status
            }

            try:
                trep = _t()
                logi(f"[REPORT] {time_key} - {len(payload_items)} items")
                report_dispense(
                    user_id=user_id,
                    machine_id=machine_id,
                    items=payload_items,
                    time=time_key,
                    result=result_status
                )
                logi(f"[REPORT_OK] {time_key} - {result_status} [{_dt(trep)}]")
            except Exception as e:
                loge(f"[ERR] report failed: {e}")
                # 오프라인에 저장 (디스크 오류 방어)
                try:
                    store_offline(payload)
                except Exception as offline_err:
                    loge(f"[ERR] Failed to store offline report: {offline_err}")
                phase_ok = False

        # 진행 상황 업데이트
        progress[time_key] = phase_ok
        write_state(status="dispensing", last_uid=_active_kit_uid, phase=time_key, progress=progress)

        if not phase_ok:
            all_ok = False

    # 4) 전 타임 끝나면 원위치 복귀
    write_state(status="returning", last_uid=_active_kit_uid, phase="evening", progress=progress)

    if adapter:
        adapter.notify_status_update(3, "HOME 위치로 복귀 중...")

    logi("[HOME] Returning to initial position")
    if settings.DRY_RUN:
        logi("[DRY] HOME")
    else:
        thm = _t()
        ok, msg = step_home(ser)
        logi(f"  HOME(final): {msg} [{_dt(thm)}]")
        if not ok:
            all_ok = False
            loge(f"[ERR] Failed to return HOME: {msg}")
            if adapter:
                adapter.notify_error(f"HOME 복귀 실패: {msg}")

    return all_ok, progress

def main(adapter=None):
    global _last_uid, _last_ts, _session_user_id, _active_kit_uid
    machine_id = settings.MACHINE_ID

    # --- (A) 등록될 때까지 대기 ---
    while True:
        registered = check_machine_registered(machine_id)
        if registered:
            write_state(status="waiting_uid")  # 등록 완료되면 대기 화면
            if adapter:
                adapter.notify_waiting()
            break
        # 미등록 상태 → 기기 등록 QR 표시
        write_state(status="machine_not_registered", last_uid=settings.DEVICE_UID)
        if adapter:
            adapter.notify_unregistered(settings.DEVICE_UID)
        time.sleep(5)  # 5초마다 재확인

    try:
        ser = open_serial(baud_rate=9600)
    except Exception as e:
        loge(f"[ERR] Serial open failed: {e}")
        if adapter: adapter.notify_error(f"시리얼 포트 열기 실패: {e}")
        return

    with ser:
        logi("[INFO] Serial ready. Waiting UID...")
        if adapter: adapter.notify_waiting()
        last_hb = time.monotonic() - settings.HEARTBEAT_SEC
    
        while True:
            try:
                now = time.monotonic()
    
                if settings.HEARTBEAT_SEC > 0 and (now - last_hb > settings.HEARTBEAT_SEC):
                    try:
                        heartbeat(machine_id)
                        # 하트비트 성공 시 오프라인 리포트 재전송 시도
                        sent = flush_offline()
                        if sent > 0:
                            logi(f"[OFFLINE] Flushed {sent} reports")
                    except Exception as e:
                        loge(f"[HB] failed: {e}")
                    last_hb = now
    
                uid = read_uid_once(ser)
                if not uid:
                    continue
    
                if uid == _last_uid and (now - _last_ts) < settings.UID_COOLDOWN_SEC:
                    continue
                _last_uid, _last_ts = uid, now
    
                if _session_user_id is not None:
                    continue

                logi(f"[UID] {uid}")
                write_state(status="resolving_uid", last_uid=uid)
                if adapter:
                    adapter.notify_uid(uid)
                    adapter.notify_status_update(3, f"UID {uid} 확인 중...")

                res = resolve_uid(uid)

                if not res:
                    if adapter: adapter.notify_error("UID를 해석할 수 없습니다.")
                    continue
    
                if not res.get("registered"):
                    logi(f"[ACTION] KIT_NOT_REGISTERED → UID={uid} QR 표시 필요")
                    write_state(status="kit_not_registered", last_uid=uid)
                    if adapter: adapter.notify_kit_unregistered(uid)
                    continue

                user_id = str(res.get("user_id"))
                took_today = int(res.get("took_today", 0))

                logi(f"[OK] user={user_id}, took_today={took_today}")

                # ===== 1) 현재 시간대 확인 =====
                current_slot, time_message = get_current_time_slot()

                if current_slot is None:
                    # 배출 불가 시간대 (00:00~06:00)
                    logi(f"[REJECT] 배출 불가 시간대: {datetime.now().hour}시")
                    write_state(status="out_of_time", last_uid=uid)
                    if adapter:
                        adapter.notify_status_update(3, time_message)
                        adapter.notify_error(time_message)
                    time.sleep(3)
                    if adapter:
                        adapter.notify_waiting()
                    continue

                # ===== 2) took_today 확인 (이미 복용 완료) =====
                if took_today == 1:
                    logi(f"[INFO] 이미 오늘 복용 완료 (user={user_id})")
                    write_state(status="already_taken", last_uid=uid)

                    # user_name 찾기
                    users = get_users_for_machine(machine_id)
                    user_name = "알 수 없는 사용자"
                    if users:
                        for user in users:
                            if str(user.get("user_id")) == user_id:
                                user_name = user.get("name")
                                break

                    if adapter:
                        adapter.notify_status_update(3, f"오늘 이미 복용하셨습니다 ({user_name}님)")
                    time.sleep(3)
                    if adapter:
                        adapter.notify_waiting()
                    continue

                # ===== 3) user_name 찾기 =====
                users = get_users_for_machine(machine_id)
                user_name = "알 수 없는 사용자"
                if users:
                    for user in users:
                        if str(user.get("user_id")) == user_id:
                            user_name = user.get("name")
                            break

                # ===== 4) 스케줄 조회 =====
                logi(f"[SCHEDULE] 현재 시간대: {current_slot} ({datetime.now().hour}시)")
                if adapter:
                    adapter.notify_status_update(3, f"{user_name}님 스케줄 조회 중... ({time_message})")

                _session_user_id = user_id
                _active_kit_uid = uid

                # build_queue 호출 (서버가 시간대별로 그룹화된 큐 반환)
                queue_response = build_queue(machine_id, user_id)
                if not queue_response:
                    loge(f"[ERR] 서버 응답 없음 (user={user_id})")
                    if adapter:
                        adapter.notify_waiting()
                        adapter.notify_error("서버 연결 오류")
                    time.sleep(3)
                    _session_user_id = _active_kit_uid = None
                    continue

                # 응답 파싱: {"status": "ok", "queue": [...]} 또는 직접 배열
                if isinstance(queue_response, dict) and "queue" in queue_response:
                    phases = queue_response["queue"] or []
                elif isinstance(queue_response, list):
                    phases = queue_response
                else:
                    loge(f"[ERR] invalid queue format: {queue_response}")
                    if adapter: adapter.notify_error("큐 형식 오류")
                    time.sleep(3)
                    _session_user_id = _active_kit_uid = None
                    if adapter: adapter.notify_waiting()
                    continue

                # ===== 5) 현재 시간대에 맞게 필터링 =====
                filtered_phases = filter_phases_by_time(phases, current_slot)
                logi(f"[FILTER] 전체={len(phases)}, 필터링 후={len(filtered_phases)}, 시간대={current_slot}")

                # ===== 6) 필터링 후 비어있는지 확인 =====
                if not filtered_phases or all(not p.get("items") for p in filtered_phases):
                    logi(f"[INFO] 현재 시간대({current_slot})에 배출할 약이 없음")
                    write_state(status="no_schedule", last_uid=uid)

                    # 원래 phases에는 있었는지 확인
                    has_any_schedule = any(p.get("items") for p in phases)

                    if has_any_schedule:
                        # 스케줄은 있지만 현재 시간대가 지나서 배출할 수 없음
                        msg = f"현재 시간대({current_slot})에 배출할 약이 없습니다"
                        logi(f"[INFO] {msg}")
                    else:
                        # 아예 스케줄이 없음
                        msg = "오늘 배출할 스케줄이 없습니다"
                        logi(f"[INFO] {msg}")

                    if adapter:
                        adapter.notify_status_update(3, msg)

                    time.sleep(3)
                    _session_user_id = _active_kit_uid = None
                    if adapter:
                        adapter.notify_waiting()
                    continue

                # ★★★ process_queue 호출 (시간대별 회전판 이동 + 배출) ★★★
                # 필터링된 시간대 목록
                filtered_times = [p.get("time") for p in filtered_phases if p.get("items")]
                first_phase = filtered_phases[0].get("time") if filtered_phases else "morning"

                write_state(status="queue_ready", last_uid=uid, phase=first_phase)
                logi(f"[QUEUE] 배출 시작: {user_name}님 - {filtered_times}")
                if adapter:
                    adapter.notify_status_update(3, f"{user_name}님 약 배출 시작... ({', '.join(filtered_times)})")

                progress = {}  # 예외 발생 시에도 안전하도록 초기화
                all_success, progress = process_queue(machine_id, user_id, filtered_phases, ser, adapter)

                if all_success:
                    logi("[OK] Dispense completed successfully")
                    write_state(status="done", last_uid=uid, progress=progress)
                    if adapter:
                        adapter.notify_status_update(3, "배출 완료!")
                else:
                    loge("[WARN] Dispense completed with errors")
                    write_state(status="error", last_uid=uid, progress=progress, error="일부 배출 실패")
                    if adapter:
                        adapter.notify_status_update(3, "배출 완료 (일부 오류)")

                time.sleep(3)
                _session_user_id = _active_kit_uid = None
                write_state(status="waiting_uid")
                if adapter: adapter.notify_waiting()

            except Exception as e:
                loge(f"[FATAL] unhandled exception in main loop: {e}")
                write_state(status="error", error=str(e))
                if adapter:
                    adapter.notify_waiting()
                    adapter.notify_error(f"오류: {e}")
                _session_user_id = _active_kit_uid = None
                time.sleep(5)
                continue

if __name__ == '__main__':
    main()