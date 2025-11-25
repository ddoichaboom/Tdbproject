import tkinter as tk
from tkinter import ttk
from datetime import datetime
import platform
import qrcode
from PIL import Image, ImageTk

class DashboardApp(tk.Tk):
    def __init__(self, fullscreen=True):
        super().__init__()
        self.title("TDB 약 배출 시스템")

        self.BG_COLOR = '#1e1e1e'
        self.CARD_COLOR = '#2c2c2c'
        self.ACCENT_COLOR = '#76d7c4'
        self.TEXT_COLOR = '#e0e0e0'
        self.BORDER_COLOR = '#444444'
        self.FONT_BOLD = ('Helvetica', 26, 'bold')
        self.FONT_NORMAL = ('Helvetica', 20)
        self.FONT_DATE = ('Helvetica', 24)
        self.FONT_BIG_TIME = ('Helvetica', 60, 'bold')

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

        self._create_dashboard()
        self.update_time()

    def _create_dashboard(self):
        main_frame = ttk.Frame(self, style='TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        self.tiles = []
        titles = ["현재 시간", "약품 재고 현황", "오늘의 전체 스케줄", "약 배출 상태", "최근 배출 기록", "등록된 유저"]
        for i in range(6):
            row, col = divmod(i, 3)
            main_frame.grid_rowconfigure(row, weight=1)
            main_frame.grid_columnconfigure(col, weight=1)
            border_frame = tk.Frame(main_frame, background=self.BORDER_COLOR, borderwidth=0)
            border_frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
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
                    slot_frame.grid(row=0, column=slot_num - 1, sticky="nsew", padx=1)
                    ttk.Label(slot_frame, text=f"Slot {slot_num}", font=('Helvetica', 20, 'bold'), background=self.CARD_COLOR, foreground=self.ACCENT_COLOR, anchor="center").pack(pady=(5, 10), side=tk.TOP)
                    stock_label = ttk.Label(slot_frame, text="- / -", font=('Helvetica', 24, 'bold'), background=self.CARD_COLOR, foreground=self.TEXT_COLOR, anchor="center")
                    stock_label.pack(pady=(10, 5), side=tk.BOTTOM)
                    name_label = ttk.Label(slot_frame, text="-", font=('Helvetica', 16), background=self.CARD_COLOR, foreground=self.TEXT_COLOR, anchor="center")
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
                    ttk.Label(slot_frame_inner, text=name, font=('Helvetica', 18, 'bold'), background=self.CARD_COLOR, foreground=self.ACCENT_COLOR).pack(anchor='w', padx=10)
                    content_label = ttk.Label(slot_frame_inner, text="스케줄 없음", font=('Helvetica', 18), background=self.CARD_COLOR, foreground=self.TEXT_COLOR, justify=tk.LEFT)
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
            w, h = self.winfo_screenwidth(), self.winfo_screenheight()
            pop_w, pop_h = int(w * 0.6), int(h * 0.5)
            x, y = (w - pop_w) // 2, (h - pop_h) // 2
            self._popup.geometry(f"{pop_w}x{pop_h}+{x}+{y}")
            border_frame = tk.Frame(self._popup, background=self.ACCENT_COLOR, borderwidth=0)
            border_frame.pack(fill=tk.BOTH, expand=True)
            popup_frame = ttk.Frame(border_frame, style='Card.TFrame')
            popup_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            popup_frame.grid_rowconfigure(0, weight=0)
            popup_frame.grid_rowconfigure(1, weight=1)
            popup_frame.grid_rowconfigure(2, weight=0)
            popup_frame.grid_columnconfigure(0, weight=1)
            self._popup_title = ttk.Label(popup_frame, font=('Helvetica', 26, 'bold'), style='CardTitle.TLabel', anchor="center")
            self._popup_title.grid(row=0, column=0, sticky='ew', pady=(20, 10))
            self._popup_message_label = ttk.Label(popup_frame, font=('Helvetica', 16), style='CardContent.TLabel', anchor="center")
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
        container = self.tiles[5]
        for widget in container.winfo_children():
            widget.destroy()
        if not users:
            ttk.Label(container, text="등록된 사용자 없음", style='CardContent.TLabel', anchor="center").place(relx=0.5, rely=0.5, anchor='center')
            return
        users.sort(key=lambda u: u.get('role') != 'parent')
        for i, user in enumerate(users):
            user_frame = ttk.Frame(container, style='Card.TFrame')
            user_frame.place(x=0, y=i * 40, relwidth=1.0, height=40)
            user_name = user.get('name', '이름없음')
            if user.get('role') == 'parent':
                ttk.Label(user_frame, text=user_name, font=('Helvetica', 18, 'bold'), background=self.CARD_COLOR, foreground=self.TEXT_COLOR).pack(side=tk.LEFT, anchor='w', padx=(10, 5), pady=5)
                ttk.Label(user_frame, text="(보호자)", font=('Helvetica', 18, 'bold'), background=self.CARD_COLOR, foreground=self.ACCENT_COLOR).pack(side=tk.LEFT, anchor='w', padx=(0, 10), pady=5)
            else:
                ttk.Label(user_frame, text=user_name, font=('Helvetica', 18), background=self.CARD_COLOR, foreground=self.TEXT_COLOR).pack(anchor='w', padx=(25, 0), pady=5)

    def update_time(self):
        now = datetime.now()
        self.date_label.config(text=now.strftime(f'%Y년 %m월 %d일 ({["월", "화", "수", "목", "금", "토", "일"][now.weekday()]})'))
        self.time_label.config(text=now.strftime('%H:%M:%S'))
        self.after(1000, self.update_time)

if __name__ == '__main__':
    app = DashboardApp(fullscreen=False)
    app.mainloop()