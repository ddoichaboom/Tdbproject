import tkinter as tk
from tkinter import ttk
from datetime import datetime
import platform
import qrcode
from PIL import Image, ImageTk
import time
import sys
import subprocess
import os

class DashboardApp(tk.Tk):
    def __init__(self, fullscreen=True):
        super().__init__()
        self.title("TDB 약 배출 시스템")

        # ✅ 초기화 중에는 윈도우 숨기기 (깜박임 방지)
        self.withdraw()

        self.BG_COLOR = '#1e1e1e'
        self.CARD_COLOR = '#2c2c2c'
        self.ACCENT_COLOR = '#76d7c4'
        self.TEXT_COLOR = '#e0e0e0'
        self.BORDER_COLOR = '#444444'
        self.FONT_BOLD = ('Helvetica', 30, 'bold')
        self.FONT_NORMAL = ('Helvetica', 24)
        self.FONT_DATE = ('Helvetica', 28)
        self.FONT_BIG_TIME = ('Helvetica', 70, 'bold')

        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.configure(background=self.BG_COLOR)
        self.style.configure('TFrame', background=self.BG_COLOR)
        self.style.configure('Card.TFrame', background=self.CARD_COLOR, relief='solid', borderwidth=1)
        self.style.configure('CardTitle.TLabel', foreground=self.ACCENT_COLOR, background=self.CARD_COLOR, font=self.FONT_BOLD)
        self.style.configure('CardContent.TLabel', foreground=self.TEXT_COLOR, background=self.CARD_COLOR, font=self.FONT_NORMAL)

        if fullscreen and platform.system() != "Windows":
            self.attributes('-fullscreen', True)
        else:
            self.geometry("800x480")

        self._popup = None
        self._popup_qr_label = None
        self._popup_message_label = None
        self._qr_photo_image = None
        self._inventory_images = []

        # ✅ 깜박임 방지를 위한 캐시 (모든 타일)
        self._cached_users = None
        self._cached_slots = None
        self._cached_schedules = None
        self._cached_history = None
        self._popup_geometry_set = False

        # ✅ 위젯 재사용을 위한 프레임 캐시
        self._user_frames = []

        # ✅ Watchdog 변수 (GUI 자가 진단용)
        self._last_heartbeat = time.time()
        self._last_watchdog_log = 0  # 마지막 로그 시간 (0으로 초기화 → 첫 체크에서 즉시 로그)
        self._watchdog_enabled = True

        self._create_dashboard()
        self.update_time()

        # ✅ 레이아웃 계산 완료 후 윈도우 표시
        self.update_idletasks()  # 모든 pending 작업 완료
        self.deiconify()  # 윈도우 표시

        # ✅ F12 키로 스크린샷 기능 바인딩
        self.bind('<F12>', self.take_screenshot)

        # ✅ Watchdog 시작 (GUI 자가 진단)
        self._start_watchdog()

    def _create_dashboard(self):
        main_frame = ttk.Frame(self, style='TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.tiles = []
        titles = ["현재 시간", "약품 재고 현황", "오늘의 전체 스케줄", "약 배출 상태", "최근 배출 기록", "등록된 유저"]
        for i in range(6):
            row, col = divmod(i, 3)
            # ✅ 반응형 유지: weight=1, uniform으로 균등 분할
            main_frame.grid_rowconfigure(row, weight=1, minsize=150, uniform="row")
            main_frame.grid_columnconfigure(col, weight=1, minsize=200, uniform="col")

            # ✅ border_frame: sticky="nsew"로 확장, propagate는 False로 내부 안정화
            border_frame = tk.Frame(main_frame, background=self.BORDER_COLOR, borderwidth=0)
            border_frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            border_frame.grid_propagate(False)  # ✅ 내용에 따라 크기 변경 방지
            border_frame.pack_propagate(False)  # ✅ pack도 무시

            card = ttk.Frame(border_frame, style='Card.TFrame')
            card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
            title_label = ttk.Label(card, text=titles[i], style='CardTitle.TLabel', anchor="center")
            title_label.pack(pady=(15, 10))
            if i == 0:
                self.date_label = ttk.Label(card, text="", font=self.FONT_DATE, background=self.CARD_COLOR, foreground=self.TEXT_COLOR)
                self.date_label.pack(pady=5)
                self.time_label = ttk.Label(card, text="", font=self.FONT_BIG_TIME, background=self.CARD_COLOR, foreground=self.TEXT_COLOR)
                self.time_label.pack(pady=5, expand=True)
                self.tiles.append(None)
            elif i == 1:
                inventory_container = ttk.Frame(card, style='Card.TFrame')
                inventory_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                inventory_container.grid_columnconfigure([0, 1, 2], weight=1)
                inventory_container.grid_rowconfigure(0, weight=1)
                self.inventory_labels = []
                for slot_num in range(1, 4):
                    slot_frame = ttk.Frame(inventory_container, style='Card.TFrame')
                    slot_frame.grid(row=0, column=slot_num - 1, sticky="nsew", padx=0)
                    ttk.Label(slot_frame, text=f"Slot {slot_num}", font=('Helvetica', 24, 'bold'), background=self.CARD_COLOR, foreground=self.ACCENT_COLOR, anchor="center").pack(pady=(5, 10), side=tk.TOP)
                    stock_label = ttk.Label(slot_frame, text="- / -", font=('Helvetica', 28, 'bold'), background=self.CARD_COLOR, foreground=self.TEXT_COLOR, anchor="center")
                    stock_label.pack(pady=(10, 5), side=tk.BOTTOM)
                    name_label = ttk.Label(slot_frame, text="-", font=('Helvetica', 20), background=self.CARD_COLOR, foreground=self.TEXT_COLOR, anchor="center", wraplength=150, justify=tk.CENTER)
                    name_label.pack(pady=0, side=tk.BOTTOM)
                    img_label = ttk.Label(slot_frame, background=self.CARD_COLOR)
                    img_label.pack(pady=5, expand=True)
                    self.inventory_labels.append({'name': name_label, 'stock': stock_label, 'img': img_label})
                self.tiles.append(inventory_container)
            elif i == 2:
                schedule_frame = ttk.Frame(card, style='Card.TFrame')
                schedule_frame.pack(pady=5, padx=15, fill=tk.BOTH, expand=True)
                self.schedule_labels = {}
                for slot, name in {"morning": "아침", "afternoon": "점심", "evening": "저녁"}.items():
                    slot_frame_inner = ttk.Frame(schedule_frame, style='Card.TFrame')
                    slot_frame_inner.pack(fill=tk.BOTH, expand=True)
                    ttk.Label(slot_frame_inner, text=name, font=('Helvetica', 22, 'bold'), background=self.CARD_COLOR, foreground=self.ACCENT_COLOR).pack(anchor='w', padx=10)
                    content_label = ttk.Label(slot_frame_inner, text="스케줄 없음", font=('Helvetica', 22), background=self.CARD_COLOR, foreground=self.TEXT_COLOR, justify=tk.LEFT)
                    content_label.pack(anchor='w', padx=10, pady=(0, 5))
                    self.schedule_labels[slot] = content_label
                self.tiles.append(schedule_frame)
            elif i == 5:
                user_list_frame = ttk.Frame(card, style='Card.TFrame')
                user_list_frame.pack(pady=5, padx=15, fill=tk.BOTH, expand=True)
                self.tiles.append(user_list_frame)
            else:
                content_label = ttk.Label(card, text="-", style='CardContent.TLabel', anchor="center")
                content_label.pack(pady=10, padx=15, fill=tk.BOTH, expand=True)
                self.tiles.append(content_label)

    def _create_popup_if_needed(self):
        if self._popup is None:
            self._popup = tk.Toplevel(self)
            if platform.system() != "Windows":
                self._popup.overrideredirect(True)
                self._popup.attributes('-topmost', True)

            # ✅ geometry는 최초 1회만 계산 (캐싱)
            if not self._popup_geometry_set:
                w, h = self.winfo_screenwidth(), self.winfo_screenheight()
                pop_w, pop_h = int(w * 0.6), int(h * 0.5)
                x, y = (w - pop_w) // 2, (h - pop_h) // 2
                self._popup.geometry(f"{pop_w}x{pop_h}+{x}+{y}")
                self._popup_geometry_set = True

            border_frame = tk.Frame(self._popup, background=self.ACCENT_COLOR, borderwidth=0)
            border_frame.pack(fill=tk.BOTH, expand=True)
            popup_frame = ttk.Frame(border_frame, style='Card.TFrame')
            popup_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            popup_frame.grid_rowconfigure(0, weight=0)
            popup_frame.grid_rowconfigure(1, weight=1)
            popup_frame.grid_rowconfigure(2, weight=0)
            popup_frame.grid_columnconfigure(0, weight=1)
            self._popup_title = ttk.Label(popup_frame, font=('Helvetica', 30, 'bold'), style='CardTitle.TLabel', anchor="center")
            self._popup_title.grid(row=0, column=0, sticky='ew', pady=(20, 10))
            self._popup_message_label = ttk.Label(popup_frame, font=('Helvetica', 20), style='CardContent.TLabel', anchor="center")
            self._popup_qr_label = ttk.Label(popup_frame, background=self.CARD_COLOR)

    def show_popup(self, title="카드를 태그해주세요", message="RFID 카드를 리더기에 가까이 대세요"):
        self._create_popup_if_needed()
        if self._popup_qr_label.winfo_ismapped():
            self._popup_qr_label.grid_remove()
        self._popup_message_label.grid(row=1, column=0, sticky='nsew', padx=20, pady=(0, 20))
        self._popup_message_label.config(text=message)
        self._popup_title.config(text=title)
        self._popup.deiconify()

    def show_qr_popup(self, qr_data, title, message):
        self._create_popup_if_needed()
        if self._popup_message_label.winfo_ismapped():
            self._popup_message_label.grid_remove()
        qr_img = qrcode.make(qr_data).resize((300, 300), Image.Resampling.LANCZOS)
        self._qr_photo_image = ImageTk.PhotoImage(qr_img)
        self._popup_qr_label.grid(row=1, column=0, pady=(10, 0))
        self._popup_qr_label.config(image=self._qr_photo_image)
        self._popup_message_label.grid(row=2, column=0, sticky='s', padx=20, pady=(10, 20))
        self._popup_message_label.config(text=message)
        self._popup_title.config(text=title)
        self._popup.deiconify()

    def hide_popup(self):
        if self._popup:
            self._popup.withdraw()

    def is_popup_visible(self):
        return self._popup and self._popup.winfo_viewable()

    def ui_call(self, func, *args, **kwargs):
        self.after(0, lambda: func(*args, **kwargs))

    def update_tile_content(self, tile_index, content):
        if tile_index > 0 and tile_index < len(self.tiles):
            if tile_index != 2:
                self.tiles[tile_index].config(text=str(content))

    def update_schedule_tile(self, schedules: list):
        # ✅ 캐싱: 데이터 동일 시 렌더링 스킵
        import json
        schedules_json = json.dumps(schedules, sort_keys=True)
        if self._cached_schedules == schedules_json:
            return
        self._cached_schedules = schedules_json

        schedules_by_time = {"morning": [], "afternoon": [], "evening": []}
        for s in schedules:
            time_of_day = s.get("time_of_day")
            if time_of_day in schedules_by_time:
                dose = s.get('dose', '?')
                schedules_by_time[time_of_day].append(f"{s.get('user_name')} ({s.get('medicine_name')}) - {dose}정")
        for slot, schedule_list in schedules_by_time.items():
            content = "\n".join(schedule_list) if schedule_list else "스케줄 없음"
            if slot in self.schedule_labels:
                self.schedule_labels[slot].config(text=content)

    def update_inventory_tile(self, slots: list):
        # ✅ 캐싱: 데이터 동일 시 렌더링 스킵
        import json
        slots_json = json.dumps(slots, sort_keys=True)
        if self._cached_slots == slots_json:
            return
        self._cached_slots = slots_json

        slot_data_map = {s.get('slot_number'): s for s in slots}
        self._inventory_images.clear()
        for i in range(3):
            slot_num = i + 1
            labels = self.inventory_labels[i]
            data = slot_data_map.get(slot_num)
            if data and data.get('name') != '(약 미등록)':
                name = data.get('name', '미지정')
                remain = data.get('remain', 0)
                total = data.get('total', 0)
                stock_color = self.TEXT_COLOR
                if total > 0:
                    percentage = (remain / total) * 100
                    if percentage >= 50: stock_color = '#388E3C'
                    elif 20 <= percentage < 50: stock_color = '#FFA000'
                    else: stock_color = '#D32F2F'
                else: stock_color = '#D32F2F'
                labels['name'].config(text=name)
                labels['stock'].config(text=f"{remain} / {total}", foreground=stock_color)
                try:
                    img_path = f"gui/assets/images/slot_{slot_num}.png"
                    img = Image.open(img_path).resize((80, 80), Image.Resampling.LANCZOS)
                    photo_img = ImageTk.PhotoImage(img)
                    labels['img'].config(image=photo_img)
                    self._inventory_images.append(photo_img)
                except FileNotFoundError:
                    labels['img'].config(image='')
            else:
                labels['name'].config(text="비어있음")
                labels['stock'].config(text="- / -", foreground=self.TEXT_COLOR)
                labels['img'].config(image='')

    def update_user_tile(self, users: list):
        # ✅ 데이터 변경 감지: 이전과 동일하면 업데이트하지 않음
        import json
        users_json = json.dumps(users, sort_keys=True)
        if self._cached_users == users_json:
            return  # 변경 없음, 다시 그리지 않음

        self._cached_users = users_json
        container = self.tiles[5]

        # 빈 상태 처리
        if not users:
            # 모든 프레임 숨기기
            for frame in self._user_frames:
                frame.place_forget()
            # 빈 상태 라벨 표시
            if not hasattr(self, '_empty_user_label'):
                self._empty_user_label = ttk.Label(container, text="등록된 사용자 없음",
                                                   style='CardContent.TLabel', anchor="center")
            self._empty_user_label.place(relx=0.5, rely=0.5, anchor='center')
            return

        # 빈 상태 라벨 숨기기
        if hasattr(self, '_empty_user_label'):
            self._empty_user_label.place_forget()

        users.sort(key=lambda u: u.get('role') != 'parent')

        # ✅ 유저 수만큼 프레임 생성/재사용 (destroy 제거)
        for i, user in enumerate(users):
            if i < len(self._user_frames):
                # ✅ 기존 프레임 재사용 - 라벨만 업데이트 (destroy 제거!)
                user_frame = self._user_frames[i]
                labels = [w for w in user_frame.winfo_children() if isinstance(w, ttk.Label)]

                user_name = user.get('name', '이름없음')
                is_parent = user.get('role') == 'parent'

                # 기존 라벨 업데이트
                if labels:
                    # 기존 구조와 다르면 재생성
                    if (is_parent and len(labels) != 2) or (not is_parent and len(labels) != 1):
                        for child in user_frame.winfo_children():
                            child.destroy()
                        self._create_user_labels(user_frame, user_name, is_parent)
                    else:
                        # 라벨 텍스트만 업데이트
                        labels[0].config(text=user_name)
                        if is_parent and len(labels) > 1:
                            labels[1].config(text="(보호자)")
                else:
                    # 라벨이 없으면 생성
                    self._create_user_labels(user_frame, user_name, is_parent)
            else:
                # ✅ 새 프레임 생성 (최초 1회만)
                user_frame = ttk.Frame(container, style='Card.TFrame')
                self._user_frames.append(user_frame)
                user_name = user.get('name', '이름없음')
                is_parent = user.get('role') == 'parent'
                self._create_user_labels(user_frame, user_name, is_parent)

            # 프레임 위치 설정
            user_frame.place(x=0, y=i * 45, relwidth=1.0, height=45)

        # 사용하지 않는 프레임 숨기기
        for i in range(len(users), len(self._user_frames)):
            self._user_frames[i].place_forget()

    def _create_user_labels(self, parent_frame, user_name, is_parent):
        """✅ 유저 라벨 생성 헬퍼 함수"""
        if is_parent:
            ttk.Label(parent_frame, text=user_name, font=('Helvetica', 22, 'bold'),
                     background=self.CARD_COLOR, foreground=self.TEXT_COLOR).pack(
                side=tk.LEFT, anchor='w', padx=(10, 5), pady=5)
            ttk.Label(parent_frame, text="(보호자)", font=('Helvetica', 22, 'bold'),
                     background=self.CARD_COLOR, foreground=self.ACCENT_COLOR).pack(
                side=tk.LEFT, anchor='w', padx=(0, 10), pady=5)
        else:
            ttk.Label(parent_frame, text=user_name, font=('Helvetica', 22),
                     background=self.CARD_COLOR, foreground=self.TEXT_COLOR).pack(
                anchor='w', padx=(25, 0), pady=5)

    def _start_watchdog(self):
        """
        ✅ GUI Watchdog: 주기적으로 GUI 건강 상태 점검

        점검 항목:
        1. GUI 응답 확인 (heartbeat 타이밍)
        2. 타일 구조 검증
        3. 메인 윈도우 존재 확인

        문제 발견 시 프로세스 종료 → systemd가 자동 재시작
        """
        if not self._watchdog_enabled:
            return

        try:
            current_time = time.time()
            elapsed = current_time - self._last_heartbeat

            # 체크 1: GUI 응답 확인 (60초 이상 heartbeat 없으면 비정상)
            if elapsed > 60:
                print(f"[WATCHDOG] ❌ GUI 응답 없음! (마지막 heartbeat: {elapsed:.0f}초 전)")
                print("[WATCHDOG] 시스템 재시작 요청...")
                sys.exit(1)  # systemd가 5초 후 재시작

            # 체크 2: 타일 구조 검증 (6개 타일이 유지되는지)
            if not hasattr(self, 'tiles') or len(self.tiles) < 6:
                print("[WATCHDOG] ❌ 타일 구조 손상! (tiles 개수 부족)")
                print("[WATCHDOG] 시스템 재시작 요청...")
                sys.exit(1)

            # 체크 3: 메인 윈도우 존재 확인
            if not self.winfo_exists():
                print("[WATCHDOG] ❌ 메인 윈도우가 파괴됨!")
                print("[WATCHDOG] 시스템 재시작 요청...")
                sys.exit(1)

            # 체크 4: 정상 상태 로깅 (5분마다)
            time_since_last_log = current_time - self._last_watchdog_log
            if time_since_last_log >= 300:  # 5분(300초) 경과 시
                print(f"[WATCHDOG] ✅ GUI 정상 작동 중 (heartbeat: {elapsed:.1f}초 전)")
                self._last_watchdog_log = current_time

        except Exception as e:
            # Watchdog 자체 오류는 무시 (GUI가 정상이면 계속 실행)
            print(f"[WATCHDOG_ERROR] 점검 중 오류 발생: {e}")
            # Watchdog 오류로 인한 재시작은 하지 않음

        # 30초마다 재실행
        self.after(30000, self._start_watchdog)

    def update_time(self):
        now = datetime.now()
        self.date_label.config(text=now.strftime(f'%Y년 %m월 %d일 ({["월", "화", "수", "목", "금", "토", "일"][now.weekday()]})'))
        self.time_label.config(text=now.strftime('%H:%M:%S'))

        # ✅ Watchdog heartbeat 갱신 (GUI가 정상 작동 중임을 표시)
        self._last_heartbeat = time.time()

        self.after(1000, self.update_time)

    def take_screenshot(self, event=None):
        """F12 키로 스크린샷 저장 (grim 사용)"""
        try:
            # 스크린샷 저장 디렉토리
            screenshot_dir = os.path.expanduser("~/screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)

            # 타임스탬프 파일명
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            filename = os.path.join(screenshot_dir, f"{timestamp}_tdb_gui.png")

            # grim으로 스크린샷 캡처 (Wayland)
            result = subprocess.run(['grim', filename],
                                  capture_output=True,
                                  text=True,
                                  timeout=5)

            if result.returncode == 0:
                print(f"✅ 스크린샷 저장: {filename}")
                self.show_popup("스크린샷 저장 완료",
                              f"저장 위치:\n{filename}")
                # 3초 후 팝업 자동 닫기
                self.after(3000, self.hide_popup)
            else:
                raise Exception(f"grim 실행 실패: {result.stderr}")

        except FileNotFoundError:
            print("❌ grim이 설치되어 있지 않습니다")
            self.show_popup("스크린샷 실패",
                          "grim이 설치되어 있지 않습니다.\nsudo apt install grim")
        except subprocess.TimeoutExpired:
            print("❌ 스크린샷 타임아웃")
            self.show_popup("스크린샷 실패", "스크린샷 캡처 시간 초과")
        except Exception as e:
            print(f"❌ 스크린샷 실패: {e}")
            self.show_popup("스크린샷 실패", f"오류 발생:\n{str(e)}")

if __name__ == '__main__':
    app = DashboardApp(fullscreen=False)
    app.mainloop()