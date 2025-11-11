# /home/tdb/Tdbproject/services/api_client.py
from __future__ import annotations
import time
from typing import Optional, List, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import settings

# ---------- 공통 세션 ----------
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

_session = _build_session()

def _url(path: str) -> str:
    base = settings.SERVER_BASE_URL.rstrip("/")
    return f"{base}{path}"

DEFAULT_GET_TO   = 5
DEFAULT_POST_TO  = 7


# ---------- 기기 등록 여부 ----------
def check_machine_registered(machine_id: str) -> bool:
    """
    서버 경로가 구축되기 전/후 혼선을 대비해 폴백 순서대로 체크:
    1) GET  /machine/check?machine_id=...
    2) GET  /machines/check?machine_id=...
    3) POST /machine/check          {"machine_id": ...}
    4) POST /machines/check         {"machine_id": ...}
    응답이 404 이거나 네트워크 오류면 False(미등록)로 본다.
    """
    get_paths  = ("/machine/check", "/machines/check")
    post_paths = ("/machine/check", "/machines/check")

    # GET 방식
    for p in get_paths:
        try:
            r = _session.get(_url(p), params={"machine_id": machine_id}, timeout=DEFAULT_GET_TO)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            data = r.json()
            return bool(data.get("registered", False))
        except requests.RequestException:
            # 다음 폴백 시도
            continue
        except ValueError:
            # JSON 파싱 실패
            continue

    # POST 방식
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


# ---------- RFID/큐/리포트/하트비트 ----------
def resolve_uid(uid: str) -> Optional[Dict[str, Any]]:
    """POST /rfid/resolve  body: {uid}  -> {registered: bool, user_id, group_id, took_today, ...}"""
    r = _session.post(_url("/rfid/resolve"),
                      json={"uid": uid},
                      timeout=DEFAULT_POST_TO)
    r.raise_for_status()
    return r.json()

def build_queue(machine_id: str, user_id: str, *, weekday: str | None = None) -> list[dict]:
    payload = {
        "machine_id": machine_id,
        "user_id": user_id,
        # 요일 자동 판정을 서버에 정확히 돕기 위해 권장
        "client_ts": int(time.time()),   # 초 단위
        "tz_offset_min": 540,            # KST = +09:00
    }
    if weekday:
        payload["weekday"] = weekday  # "mon".."sun"

    r = _session.post(_url("/queue/build"), json=payload, timeout=DEFAULT_POST_TO)
    r.raise_for_status()

    # --- 응답 검증/파싱: dict → list[dict] ---
    data = r.json()  # dict여야 함
    if not isinstance(data, dict):
        raise RuntimeError(f"Invalid response (not a JSON object): {str(data)[:500]}")
    queue = data.get("queue", [])
    if not isinstance(queue, list):
        raise RuntimeError(f"Invalid 'queue' type: {type(queue).__name__} (body={str(data)[:500]})")

    # 안전장치: 혹시 문자열/숫자 섞여오면 최소 형태로 정규화
    norm = []
    for item in queue:
        if isinstance(item, dict):
            norm.append(item)
        elif isinstance(item, (str, int)):
            try:
                norm.append({"slot": int(item), "count": 1})
            except Exception:
                # 형식 불명 → 무시/로그
                continue
    return norm


def report_dispense(
    machine_id: str,
    user_id: str,
    time_key: str,                      # "morning" | "afternoon" | "evening"
    items: List[Dict[str, Any]],        # [{"medi_id":..., "count":...}, ...]
    result: str,                        # "completed" | "partial" | "failed"
    client_tx_id: Optional[str] = None,
) -> Dict[str, Any]:
    """POST /dispense/report"""
    payload = {
        "machine_id": machine_id,
        "user_id": user_id,
        "time": time_key,
        "items": items,
        "result": result,
    }
    if client_tx_id:
        payload["client_tx_id"] = client_tx_id

    r = _session.post(_url("/dispense/report"),
                      json=payload,
                      timeout=DEFAULT_POST_TO)
    r.raise_for_status()
    return r.json()

def heartbeat(machine_id: str, status: str = "idle", extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    POST /machine/heartbeat (404면 폴백으로 /machines/heartbeat 시도)
    payload: {machine_id, status, ts, ...extra}
    """
    payload = {"machine_id": machine_id, "status": status, "ts": time.time()}
    if extra:
        payload.update(extra)

    # 1차: /machine/heartbeat
    r = _session.post(_url("/machine/heartbeat"), json=payload, timeout=DEFAULT_POST_TO)
    if r.status_code == 404:
        # 2차: /machines/heartbeat
        r = _session.post(_url("/machines/heartbeat"), json=payload, timeout=DEFAULT_POST_TO)
    r.raise_for_status()
    return r.json()


__all__ = [
    "check_machine_registered",
    "resolve_uid",
    "build_queue",
    "report_dispense",
    "heartbeat",
]
