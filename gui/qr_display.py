# gui/qr_display.py
import json, time, threading
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from config import settings

import tkinter as tk
from PIL import Image, ImageTk
import qrcode

STATE_PATH = Path("data/state.json")

REG_MACHINE_PATH = "/register-dispenser"   # 프론트 라우트
REG_KIT_PATH     = "/register-daily-kit"   # 프론트 라우트
# 서버 담당과 합의 되면 경로/파라미터 맞춰 수정

POLL_MS = 500  # 상태 폴링 주기(ms)

@dataclass
class ViewState:
    status: str = "waiting_uid"
    last_uid: Optional[str] = None
    phase: Optional[str] = None
    progress: dict = None
    error: Optional[str] = None

def read_state() -> ViewState:
    try:
        d = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return ViewState(
            status=d.get("status","waiting_uid"),
            last_uid=d.get("last_uid"),
            phase=d.get("phase"),
            progress=d.get("progress") or {},
            error=d.get("error"),
        )
    except Exception:
        return ViewState()

# JSON QR 헬퍼
def make_qr_from_json(payload: dict, size: int = 320):
    s = json.dumps(payload, separators=(",", ":"))
    img = qrcode.make(s).resize((size, size))
    return ImageTk.PhotoImage(img)

def status_text(vs: ViewState) -> str:
    m = {
        "waiting_uid": "카드를 태그해 주세요.",
        "resolving_uid": "사용자 확인 중…",
        "kit_not_registered": "키트 미등록: 아래 QR로 등록해 주세요.",
        "queue_ready": "배출 준비 완료.",
        "moving": f"이동 중… ({vs.phase or ''})",
        "dispensing": f"배출 중… ({vs.phase or ''})",
        "returning": "원위치 복귀 중…",            # ★ 추가
        "done": "오늘 일정 완료!",
        "error": f"오류 발생: {vs.error or ''}",
    }
    return m.get(vs.status, vs.status)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TDB Dispenser")
        self.geometry("540x600")
        self.configure(bg="white")

        self.lbl_title = tk.Label(self, text="TDB Dispenser", font=("Arial", 20, "bold"), bg="white")
        self.lbl_title.pack(pady=10)

        self.lbl_status = tk.Label(self, text="", font=("Arial", 16), bg="white")
        self.lbl_status.pack(pady=10)

        self.canvas = tk.Label(self, bg="white")
        self.canvas.pack(pady=10)

        self.lbl_sub = tk.Label(self, text="", font=("Arial", 12), bg="white", fg="#555")
        self.lbl_sub.pack(pady=5)

        self.after(POLL_MS, self.tick)

    def tick(self):
        vs = read_state()
        self.lbl_status.config(text=status_text(vs))

        # 어떤 화면을 띄울지 결정
        base = settings.SERVER_BASE_URL.rstrip("/")
        show_qr = False
        sub_text = ""

        # kit_not_registered → 키트등록 QR(JSON)
        if vs.status == "kit_not_registered" and vs.last_uid:
            payload = {"uid": vs.last_uid.upper()}
            img = make_qr_from_json(payload, size=320)
            self.canvas.config(image=img); self.canvas.image = img
            self.lbl_title.config(text="키트 등록이 필요합니다")
            self.lbl_sub.config(text=f"K_UID: {vs.last_uid.upper()}")
        # machine_not_registered → 기기등록 QR(JSON)
        elif vs.status == "machine_not_registered":
            device_uid = (getattr(settings, "DEVICE_UID", None) or settings.MACHINE_ID).upper()
            payload = {getattr(settings, "QR_MACHINE_KEY", "uid"): device_uid}
            img = make_qr_from_json(payload, size=320)
            self.canvas.config(image=img); self.canvas.image = img
            self.lbl_title.config(text="기기 등록이 필요합니다")
            self.lbl_sub.config(text=f"UID: {device_uid}")
        elif vs.status == "waiting_uid":
            # 기존의 기기등록 QR 표시 코드 제거
            self.canvas.config(image=""); self.canvas.image = None
            self.lbl_title.config(text="카드를 태그해 주세요")
            self.lbl_sub.config(text=f"Machine: {settings.MACHINE_ID}")
        elif vs.status in ("dispensing","queue_ready","resolving_uid"):
            # 진행 중 화면(텍스트만)
            self.canvas.config(image=""); self.canvas.image = None
            prog = vs.progress or {}
            ticks = " / ".join([f"{k}:{'O' if prog.get(k) else '·'}" for k in ("morning","afternoon","evening")])
            self.lbl_sub.config(text=f"{ticks}  (배출 중: 키트 교체 금지)")
        elif vs.status == "done":
            self.canvas.config(image=""); self.canvas.image = None
            sub_text = "수고하셨습니다."
        elif vs.status == "error":
            self.canvas.config(image=""); self.canvas.image = None
            sub_text = vs.error or ""
        elif vs.status in ("dispensing","moving","queue_ready","resolving_uid"):
            # 진행 중 화면(텍스트만)
            self.canvas.config(image=""); self.canvas.image = None
            prog = vs.progress or {}
            ticks = " / ".join([f"{k}:{'O' if prog.get(k) else '·'}" for k in ("morning","afternoon","evening")])
            self.lbl_sub.config(text=f"{ticks}  (배출 중: 키트 교체 금지)")
        elif vs.status in ("dispensing","moving","returning","queue_ready","resolving_uid"):
            self.canvas.config(image=""); self.canvas.image = None
            prog = vs.progress or {}
            ticks = " / ".join([f"{k}:{'O' if prog.get(k) else '·'}" for k in ("morning","afternoon","evening")])
            self.lbl_sub.config(text=f"{ticks}  (배출 중: 키트 교체 금지)")
        else:
            self.canvas.config(image=""); self.canvas.image = None
            sub_text = ""

        self.lbl_sub.config(text=sub_text)
        self.after(POLL_MS, self.tick)

if __name__ == "__main__":
    App().mainloop()
