import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import settings

_session = None

def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        retry = Retry(total=3, connect=3, read=3, backoff_factor=0.5, status_forcelist=(500, 502, 503, 504))
        adapter = HTTPAdapter(max_retries=retry)
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)
        _session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    return _session

def _request(method, path, **kwargs):
    url = f"{settings.SERVER_BASE_URL}{path}"
    try:
        s = _get_session()
        # 타임아웃 10초로 증가 (네트워크 지연 대비)
        timeout = kwargs.pop('timeout', 10)
        res = s.request(method, url, timeout=timeout, **kwargs)
        res.raise_for_status()

        json_res = res.json()
        if json_res and "data" in json_res:
            return json_res["data"]
        return json_res

    except requests.exceptions.RequestException as e:
        print(f"[API_{method.upper()}_ERR] {path}: {e}")
        return None
    except Exception as e:
        print(f"[API_UNKNOWN_ERR] {path}: {e}")
        return None

def _get(path, **kwargs):
    return _request("get", path, **kwargs)

def _post(path, **kwargs):
    return _request("post", path, **kwargs)

# --- API 함수들 ---

def check_machine_registered(machine_id: str) -> bool:
    res = _get("/machine/check", params={"machine_id": machine_id})
    return res.get("registered", False) if isinstance(res, dict) else False

def resolve_uid(uid: str):
    return _post("/rfid/resolve", json={"uid": uid})

def build_queue(machine_id: str, user_id: str, weekday: str = None):
    """
    사용자 ID와 기기 ID로 오늘의 배출 큐를 생성합니다.
    서버는 시간대별로 그룹화된 큐를 반환합니다.
    (RFID 태그 시 사용)
    """
    import time
    payload = {
        "machine_id": machine_id,
        "user_id": user_id,
        "client_ts": int(time.time()),
        "tz_offset_min": 540,  # KST = +09:00
    }
    if weekday:
        payload["weekday"] = weekday

    return _post("/queue/build", json=payload)

def report_dispense(user_id: str, machine_id: str, items: list, time: str = None, result: str = "completed"):
    """
    배출 완료를 서버에 보고
    time: "morning" | "afternoon" | "evening" (시간대별 보고 시 필수)
    result: "completed" | "partial" | "failed"
    """
    payload = {
        "machine_id": machine_id,
        "user_id": user_id,
        "items": items,
        "result": result
    }
    if time:
        payload["time"] = time

    return _post("/dispense/report", json=payload)

def heartbeat(machine_id: str):
    return _post("/machine/heartbeat", json={"machine_id": machine_id})

def get_users_for_machine(machine_id: str):
    return _get(f"/machine/{machine_id}/users")

def get_slots_for_machine(machine_id: str):
    return _get(f"/machine/{machine_id}/slots")

def get_today_schedules_for_machine(machine_id: str):
    return _get(f"/machine/{machine_id}/schedules/today")

def get_dose_history_for_machine(machine_id: str, start_date: str):
    return _get(f"/dose-history/machine/{machine_id}", params={"start_date": start_date})