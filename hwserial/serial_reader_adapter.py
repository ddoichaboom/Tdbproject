import threading
from .serial_reader import main as serial_main

class SerialReaderAdapter:
    def __init__(self, on_waiting=None, on_uid=None, on_error=None, on_unregistered=None, on_kit_unregistered=None, on_status_update=None, on_user_list_update=None, on_slot_list_update=None, on_schedule_list_update=None, on_history_list_update=None):
        self.on_waiting = on_waiting
        self.on_uid = on_uid
        self.on_error = on_error
        self.on_unregistered = on_unregistered
        self.on_kit_unregistered = on_kit_unregistered
        self.on_status_update = on_status_update
        self.on_user_list_update = on_user_list_update
        self.on_slot_list_update = on_slot_list_update
        self.on_schedule_list_update = on_schedule_list_update
        self.on_history_list_update = on_history_list_update
        
        self._thread = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()

    def notify_waiting(self):
        if self.on_waiting: self.on_waiting()
        self._ready_event.set()

    def notify_uid(self, uid):
        if self.on_uid: self.on_uid(uid)

    def notify_error(self, message):
        if self.on_error: self.on_error(message)
        self._ready_event.set()

    def notify_unregistered(self, device_id):
        if self.on_unregistered: self.on_unregistered(device_id)
        self._ready_event.set()

    def notify_kit_unregistered(self, uid):
        if self.on_kit_unregistered: self.on_kit_unregistered(uid)

    def notify_status_update(self, tile_index, message):
        if self.on_status_update:
            self.on_status_update(tile_index, message)

    def notify_user_list_update(self, users: list):
        if self.on_user_list_update:
            self.on_user_list_update(users)

    def notify_slot_list_update(self, slots: list):
        if self.on_slot_list_update:
            self.on_slot_list_update(slots)

    def notify_schedule_list_update(self, schedules: list):
        if self.on_schedule_list_update:
            self.on_schedule_list_update(schedules)

    def notify_history_list_update(self, history: list):
        if self.on_history_list_update:
            self.on_history_list_update(history)

    def _run_serial_main(self):
        try:
            serial_main(self)
        except Exception as e:
            print(f"[FATAL] 시리얼 리더 스레드 오류: {e}")
            self.notify_error(f"시리얼 스레드 오류: {e}")
        finally:
            self._ready_event.set()

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._run_serial_main)
            self._thread.daemon = True
            self._thread.start()

    def is_ready(self):
        return self._ready_event.is_set() and (self._thread is None or self._thread.is_alive())

    def stop(self):
        print("Adapter stopping...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)