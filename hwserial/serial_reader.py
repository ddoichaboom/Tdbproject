import os
import time
import logging
from logging.handlers import RotatingFileHandler
import requests
import json
from pathlib import Path
from config import settings
from datetime import datetime

# 시리얼 헬퍼
from hwserial.arduino_link import (
    open_serial, 
    read_uid_once, 
    dispense, 
    step_next, 
    step_home, 
    step_next_n
)

# 하트비트
from services.api_client import (
    check_machine_registered,
    resolve_uid,
    build_queue,
    report_dispense,
    heartbeat,
)

# serial_reader.py 상단 import들 아래 아무 데나
def _t(): 
    import time
    return time.monotonic()

def _dt(t0):
    import time
    return f"{(time.monotonic()-t0)*1000:.0f}ms"


# 세션 락 & 키트 고정
_session_user_id = None
_active_kit_uid = None

# ---------------------------
# 중복 UID 쿨다운용 상태
# ---------------------------
_last_uid = None
_last_ts  = 0.0

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

def logi(msg): print(msg); logger.info(msg)
def loge(msg): print(msg); logger.error(msg)

# ---------------------------
# 오프라인 적치 & 상태 파일
# ---------------------------
STATE_PATH   = Path("data/state.json")
OFFLINE_PATH = Path("data/offline_reports.jsonl")
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
OFFLINE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _time_bucket_now() -> str:
    """현재 시각 기준으로 서버 보고용 time 키 산출."""
    h = datetime.now().hour
    if 5 <= h < 11:
        return "morning"
    if 11 <= h < 17:
        return "afternoon"
    return "evening"

def _stage_for_time_key(time_key: str) -> int:
    """
    물리 맵:
      stage 0 : 아침(초기 위치)
      stage 1 : 점심 (앞으로 2000ms → STEP_NEXT 1회)
      stage 2 : 저녁 (점심에서 추가로 2500ms → STEP_NEXT 1회)
    """
    return {"morning": 0, "afternoon": 1, "evening": 2}.get(time_key, 0)

def write_state(status: str, **kwargs):
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
    """서버 전송 실패 시 JSONL로 1줄 적치."""
    with OFFLINE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    logger.info(f"[OFFLINE] stored -> {payload.get('time')} items={len(payload.get('items', []))}")


def flush_offline() -> int:
    """적치분 재전송. 성공 건수 반환."""
    if not OFFLINE_PATH.exists():
        return 0
    sent = 0
    keep: list[str] = []
    url = settings.SERVER_BASE_URL.rstrip("/") + "/dispense/report"
    with OFFLINE_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                r = requests.post(url, json=payload, timeout=5)
                r.raise_for_status()
                sent += 1
            except Exception:
                keep.append(line)
    with OFFLINE_PATH.open("w", encoding="utf-8") as f:
        for line in keep:
            f.write(line + "\n")
    return sent


# ---------------------------
# 큐 처리 (아침→점심→저녁)
# ---------------------------
def process_queue(base_url: str, machine_id: str, user_id: str, phases: list, ser):
    progress = {"morning": False, "afternoon": False, "evening": False}
    all_ok = True

    current_stage = 0  # 아침(초기)에서 시작

    # 필수: 아침→점심→저녁 순으로 정렬
    order = {"morning": 0, "afternoon": 1, "evening": 2}
    phases = sorted(phases, key=lambda p: order.get(p["time"], 99))

    for phase in phases:
        time_key = phase["time"]                  # "morning" | "afternoon" | "evening"
        items    = phase["items"]
        if not items:
            continue

        # 1) 목표 스테이지로 이동
        target = _stage_for_time_key(time_key)
        if target < current_stage:
            # 뒤로 가야 하면 HOME으로 리셋 후 다시 전진 (이 케이스는 정렬했으면 안 나옴, 그래도 방어)
            ok, msg = step_home(ser)
            logi(f"  HOME(reset): {msg}")
            if not ok: all_ok = False
            current_stage = 0

        need = target - current_stage
        if need > 0:
            # ★ 이동 시작 알림 (GUI에 '이동 중')
            write_state(status="moving", last_uid=_active_kit_uid,
                    phase=time_key, progress=progress)

            tmv = _t()
            ok, msg = step_next_n(ser, need)                # ← 이동(2000ms/2500ms)
            logi(f"  STEP: {msg} (stage {current_stage}->{target}) [{_dt(tmv)}]")
            if not ok: all_ok = False
            current_stage = target

        # ★ 이동 완료 → 곧 배출 시작 알림 (GUI에 '배출 중')
        write_state(status="dispensing", last_uid=_active_kit_uid,
                phase=time_key, progress=progress)

        # 해당 시간대 아이템 전부 배출
        phase_ok = True
        for it in items:
            slot, count = int(it["slot"]), int(it["count"])
            tdisp = _t()
            ok, msg = dispense(ser, slot, count) if not settings.DRY_RUN else (True, "OK,DRY")
            logi(f"  -> {msg} [{_dt(tdisp)}]")
            if not ok:
                if not settings.DRY_RUN:
                    ok2, msg2 = dispense(ser, slot, count)
                    logi(f"  (retry)-> {msg2} [{_dt(tdisp)}]")
                    if not ok2:
                        phase_ok = False
                else:
                    phase_ok = False

        # 3) 서버 리포트 (시간대 정확히 명시)
        payload_items = [
            {"medi_id": it.get("medi_id"), "count": int(it["count"])}
            for it in items if it.get("medi_id")
        ]
        try:
            trep = _t()
            rep = report_dispense(machine_id, user_id, time_key,
                                  payload_items, "completed" if phase_ok else "partial")
            logi(f"[REPORT] {rep} [{_dt(trep)}]")
        except Exception as e:
            loge(f"[ERR] report failed: {e}")
            phase_ok = False

        progress[time_key] = phase_ok
        write_state(status="dispensing", last_uid=_active_kit_uid,
                    phase=time_key, progress=progress)

        if not phase_ok:
            all_ok = False

    write_state(status="returning", last_uid=_active_kit_uid,
            phase="evening", progress=progress)
            
    # 4) 전 타임 끝나면 원위치 복귀 (저녁까지 갔으면 4500ms역행)
    if settings.DRY_RUN:
        logi("[DRY] HOME")
    else:
        thm = _t()
        ok, msg = step_home(ser)
        logi(f"  HOME(final): {msg} [{_dt(thm)}]")
        if not ok: 
            all_ok = False

    return all_ok, progress



def _weekday_key_now() -> str:
    # 월=0..일=6 → "mon".."sun"
    return ["mon","tue","wed","thu","fri","sat","sun"][datetime.now().weekday()]


# ---------------------------
# 메인 루프
# ---------------------------
def main():
    global _session_user_id, _active_kit_uid, _last_uid, _last_ts
    global _session_user_id, _active_kit_uid

    base = settings.SERVER_BASE_URL.rstrip("/")
    machine_id = settings.MACHINE_ID

    # --- (A) 등록될 때까지 대기 ---
    while True:
        registered = check_machine_registered(machine_id)
        if registered:
            write_state(status="waiting_uid")  # 등록 완료되면 대기 화면
            break
        # 미등록 상태 → 기기 등록 QR 표시
        write_state(status="machine_not_registered", last_uid=settings.DEVICE_UID)
        time.sleep(5)  # 5초마다 재확인

    # 1) 시리얼 열기
    try:
        ser = open_serial()
    except Exception as e:
        loge(f"[ERR] Serial open failed: {e}")
        return

    with ser:
        logi("[INFO] Serial ready. Waiting UID...")
        write_state(status="waiting_uid")
        last_hb = time.monotonic() - settings.HEARTBEAT_SEC
    
        while True:
            try:
                now = time.monotonic()
    
                # 0) HEARTBEAT + OFFLINE FLUSH
                if settings.HEARTBEAT_SEC > 0 and (now - last_hb > settings.HEARTBEAT_SEC):
                    try:
                        heartbeat(machine_id)
                        sent = flush_offline()
                        if sent:
                            logi(f"[OFFLINE] flushed {sent} report(s)")
                    except Exception as e:
                        loge(f"[HB] failed: {e}")
                    last_hb = now
    
                # 1) UID 대기
                uid = read_uid_once(ser)
                if not uid:
                    continue
    

                if uid == _last_uid and (now - _last_ts) < settings.UID_COOLDOWN_SEC:
                    continue
                _last_uid, _last_ts = uid, now
    

                # === 엄격 모드: 세션 중엔 어떤 UID도 처리하지 않음 ===
                if _session_user_id is not None:
                    if _active_kit_uid and uid != _active_kit_uid:
                        loge(f"[LOCK] KIT SWAP attempt during dispensing: active={_active_kit_uid}, new={uid} -> ignored")
                        # (선택) state.json에 안내 상태 반영 가능
                    # 같든 다르든 세션 중엔 그냥 무시
                    continue

                logi(f"[UID] {uid}")
                write_state(status="resolving_uid", last_uid=uid)
    
                # 3) UID → 사용자
                res = resolve_uid(uid)
                if not res:
                    write_state(status="error", last_uid=uid, error="resolve_uid failed")
                    continue
    
                if not res.get("registered"):
                    logi(f"[ACTION] KIT_NOT_REGISTERED → UID={uid} QR 표시 필요")
                    write_state(status="kit_not_registered", last_uid=uid)
                    continue
    
                user_id = str(res.get("user_id"))
                took_today = int(res.get("took_today", 0))
                logi(f"[OK] user={user_id}, took_today={took_today}")
                if took_today == 1:
                    logi("[INFO] 이미 오늘 수령 완료")
                    write_state(status="done", last_uid=uid, progress={"morning":True,"afternoon":True,"evening":True})
                    continue
    
                # 4) 큐 생성
                wk  = _weekday_key_now()
                raw = build_queue(machine_id, user_id, weekday=wk)
                logi(f"[DBG] raw queue type={type(raw).__name__} sample={str(raw)[:800]}")


                # ★ 응답 형태: list 또는 dict(queue 키) 모두 허용
                if isinstance(raw, list):
                    phases_in = raw
                elif isinstance(raw, dict) and "queue" in raw:
                    phases_in = raw["queue"] or []
                else:
                    loge(f"[ERR] invalid queue response: {raw}")
                    write_state(status="error", last_uid=uid, error="invalid queue format")
                    continue

                # 서버 phase 배열 그대로 파싱(+정규화)
                phases = []
                for p in phases_in:
                    t = (p.get("time") or p.get("time_of_day"))
                    its = p.get("items") or []
                    if t not in ("morning","afternoon","evening"):
                        continue
                    items_norm = []
                    for it in its:
                        try:
                            items_norm.append({
                                "slot": int(it["slot"]),
                                "count": int(it.get("count", 1)),
                                "medi_id": it.get("medi_id"),
                            })
                        except Exception:
                            loge(f"[ERR] bad queue item: {it}")
                    if items_norm:
                        phases.append({"time": t, "items": items_norm})


                if not phases:
                    logi("[INFO] 오늘 실행할 항목 없음")
                    write_state(status="waiting_uid", last_uid=uid)
                    continue

                write_state(status="queue_ready", last_uid=uid)

                # === 세션 잠금 시작 ===
                _session_user_id = user_id
                _active_kit_uid  = uid
                try:
                    init_progress = {"morning": False, "afternoon": False, "evening": False}
                    write_state(status="dispensing", last_uid=uid, progress=init_progress)

                    # → 아침(0)→점심(1)→저녁(2) 순, 마지막에 HOME
                    all_ok, progress = process_queue(base, machine_id, user_id, phases, ser)

                    write_state(status="done", last_uid=uid, progress=progress)
                finally:
                    _session_user_id = None
                    _active_kit_uid  = None


    
            except KeyboardInterrupt:
                logi("Bye.")
                break
            except Exception as e:
                loge(f"[ERR] Loop error: {e}")
                write_state(status="error", error=str(e))
                time.sleep(1)


if __name__ == "__main__":
    main()
