import sys
import threading
import time
from datetime import datetime, timedelta
from gui.gui_app import DashboardApp
from hwserial.serial_reader_adapter import SerialReaderAdapter
from config import settings
from services.api_client import (
    get_users_for_machine,
    get_slots_for_machine,
    get_today_schedules_for_machine,
    get_dose_history_for_machine,
)

def main():
    is_demo_mode = '--demo' in sys.argv
    app = DashboardApp(fullscreen=not is_demo_mode)

    app.update_tile_content(3, "시스템 초기화 중...")

    def on_unregistered(device_id):
        app.ui_call(app.show_qr_popup, 
                    qr_data=device_id, 
                    title="기기 등록 필요", 
                    message="앱에서 이 QR 코드를 스캔하여 기기를 등록하세요.")

    def on_waiting():
        app.ui_call(app.hide_popup)  # 팝업 숨기기
        app.ui_call(app.update_tile_content, 3, "RFID 대기 중...")

    def on_uid(uid):
        app.ui_call(app.hide_popup)

    def on_error(message):
        app.ui_call(app.update_tile_content, 3, f"오류: {message}")
        app.ui_call(app.show_popup, "오류 발생", message)

    def on_kit_unregistered(uid):
        app.ui_call(app.show_qr_popup,
                    qr_data=f"TDB_KIT_{uid}",
                    title="미등록 카드",
                    message="앱에서 이 QR 코드를 스캔하여 카드를 등록하세요.")
        app.ui_call(app.update_tile_content, 3, "미등록 카드")

    def on_status_update(tile_index, message):
        app.ui_call(app.update_tile_content, tile_index, message)

    def on_user_list_update(users: list):
        app.ui_call(app.update_user_tile, users)

    def on_slot_list_update(slots: list):
        app.ui_call(app.update_inventory_tile, slots)

    def on_schedule_list_update(schedules: list):
        app.ui_call(app.update_schedule_tile, schedules)

    def on_history_list_update(history: list):
        if history:
            processed_entries = set()
            history_lines = []
            history.sort(key=lambda x: x.get('dispensed_at', ''), reverse=True)
            for item in history:
                user_name = item.get('user_name', '알 수 없는 사용자')
                dispensed_at_str = item.get('dispensed_at', '')
                try:
                    utc_time = datetime.fromisoformat(dispensed_at_str.replace('Z', '+00:00'))
                    local_dt = utc_time.astimezone()
                    entry_key = (user_name, local_dt.strftime('%Y-%m-%d'))
                    if entry_key not in processed_entries:
                        summary = f"{user_name}님 - {local_dt.strftime('%m월 %d일')} 복용 완료"
                        history_lines.append(summary)
                        processed_entries.add(entry_key)
                except (ValueError, TypeError):
                    history_lines.append(f"{user_name} - 시간 정보 오류")
            app.ui_call(app.update_tile_content, 4, "\n".join(history_lines))
        else:
            app.ui_call(app.update_tile_content, 4, "최근 기록 없음")

    stop_polling = threading.Event()
    polling_thread = None

    def poll_server_data():
        time.sleep(1)
        while not stop_polling.is_set():
            print("[POLLING] 서버에서 최신 정보를 가져옵니다...")
            try:
                machine_id = settings.MACHINE_ID
                if not machine_id:
                    time.sleep(10)
                    continue
                
                users = get_users_for_machine(machine_id)
                if users is not None: app.ui_call(on_user_list_update, users)
                
                slots = get_slots_for_machine(machine_id)
                if slots is not None: app.ui_call(on_slot_list_update, slots)
                
                schedules = get_today_schedules_for_machine(machine_id)
                if schedules is not None: app.ui_call(on_schedule_list_update, schedules)
                
                yesterday = datetime.now() - timedelta(days=1)
                start_date_str = yesterday.strftime('%Y-%m-%d')
                history = get_dose_history_for_machine(machine_id, start_date=start_date_str)
                if history is not None: app.ui_call(on_history_list_update, history)

            except Exception as e:
                print(f"[POLLING_ERROR] 데이터 업데이트 중 오류 발생: {e}")
            time.sleep(10)

    adapter = SerialReaderAdapter(
        on_waiting=on_waiting,
        on_uid=on_uid,
        on_error=on_error,
        on_unregistered=on_unregistered,
        on_kit_unregistered=on_kit_unregistered,
        on_status_update=on_status_update,
        on_user_list_update=on_user_list_update,
        on_slot_list_update=on_slot_list_update,
        on_schedule_list_update=on_schedule_list_update,
        on_history_list_update=on_history_list_update
    )

    def start_polling_when_ready():
        nonlocal polling_thread
        if adapter.is_ready():
            print("시리얼 준비 완료. 주기적 폴링을 시작합니다.")
            if polling_thread is None:
                polling_thread = threading.Thread(target=poll_server_data, daemon=True)
                polling_thread.start()
        else:
            app.after(100, start_polling_when_ready)

    try:
        if is_demo_mode:
            print("--- DEMO MODE ---")
            polling_thread = threading.Thread(target=poll_server_data, daemon=True)
            polling_thread.start()
        else:
            print("--- SERIAL MODE ---")
            adapter.start()
            app.after(100, start_polling_when_ready)
        
        app.mainloop()

    finally:
        stop_polling.set()
        if adapter:
            adapter.stop()
        print("Application finished.")

if __name__ == "__main__":
    main()
