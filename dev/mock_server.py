from fastapi import FastAPI, Body
from pydantic import BaseModel
import time
from datetime import date

app = FastAPI()

class HeartbeatIn(BaseModel):
    machine_id: str
    status: str | None = "idle"
    ts: float | None = None

# 데모 상태 저장소(메모리)
registered_machines = {"MACHINE-0001": True}
users = {  # UID -> user info (원하는 UID로 바꿔도 됨)
    "6CEFECBF": {"user_id": 12, "group_id": 3, "took_today": 0}
}

@app.post("/machine/heartbeat")
def machine_heartbeat(body: HeartbeatIn):
    # 필요한 경우 서버 담당 스펙에 맞춰 필드 검증/저장/응답 조정
    return {
        "status": "ok",
        "machine_id": body.machine_id,
        "server_ts": time.time(),
        "echo_status": body.status,
    }

@app.get("/machine/check")
def machine_check(machine_id: str):
    return {"registered": registered_machines.get(machine_id, False)}

@app.post("/rfid/resolve")
def rfid_resolve(payload: dict = Body(...)):
    uid = (payload.get("uid") or "").upper()
    u = users.get(uid)
    if not u:
        # 데모: 미등록으로 처리 (원하면 자동 등록 True로 바꿔도 됨)
        return {"registered": False}
    return {"registered": True, **u}

@app.post("/queue/build")
def queue_build(payload: dict = Body(...)):
    # 데모: 고정 큐 반환(아침1, 점심1, 저녁1)
    # 실제에선 DB에서 schedule+machine_slot 조합
    return {
        "status": "ok",
        "took_today": 0,
        "queue": [
            {"time": "morning",   "items": [{"slot": 1, "medi_id": 7, "count": 1}]},
            {"time": "afternoon", "items": [{"slot": 2, "medi_id": 9, "count": 1}]},
            {"time": "evening",   "items": [{"slot": 3, "medi_id": 5, "count": 1}]},
        ],
        "date": str(date.today())
    }

@app.post("/dispense/report")
def dispense_report(payload: dict = Body(...)):
    # 데모: 저녁 보고 오면 took_today = 1
    time_key = payload.get("time")
    # 편의상 가장 처음 유저 하나만 토글 (실환경은 user_id별로 갱신)
    for u in users.values():
        if time_key == "evening":
            u["took_today"] = 1
    return {"status": "ok", "took_today": 1 if time_key == "evening" else 0}
