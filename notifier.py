import customtkinter as ctk
import winsound
import threading
import time
import os
import datetime

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

UAC_SOUND = os.path.join(
    os.environ.get("SystemRoot", r"C:\Windows"),
    "Media",
    "Windows User Account Control.wav",
)

LEVEL_THEMES = [
    {"header": "#3b82f6", "accent": "#2563eb", "hover": "#1d4ed8", "skip": "#60a5fa", "skip_hover": "#3b82f6", "icon": "💤", "title": "GO TO SLEEP"},
    {"header": "#f59e0b", "accent": "#d97706", "hover": "#b45309", "skip": "#fbbf24", "skip_hover": "#f59e0b", "icon": "😤", "title": "GO TO SLEEP"},
    {"header": "#ef4444", "accent": "#dc2626", "hover": "#b91c1c", "skip": "#f87171", "skip_hover": "#ef4444", "icon": "🔥", "title": "GO TO SLEEP"},
    {"header": "#7f1d1d", "accent": "#991b1b", "hover": "#7f1d1d", "skip": "#b91c1c", "skip_hover": "#991b1b", "icon": "💀", "title": "GO TO SLEEP"},
]


class SleepNotifier:
    def __init__(self, message, color, level, on_dismiss, on_lock, on_skip_today=None, streak=0):
        self.message = message
        self.color = color
        self.level = level
        self.on_dismiss = on_dismiss
        self.on_lock = on_lock
        self.on_skip_today = on_skip_today
        self.streak = streak
        self.window = None
        self.countdown_value = None
        self.alarm_active = False

    def _play_appear_sound(self):
        try:
            winsound.PlaySound(UAC_SOUND, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            winsound.Beep(800, 200)

    def show(self):
        self._play_appear_sound()

        self.window = ctk.CTkToplevel()
        self.window.title("Sleep Notifier")
        self.window.configure(fg_color="#ffffff")
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)

        self.window.after(10, self._center_and_build)

    def _center_and_build(self):
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        w, h = 480, 400
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.window.geometry(f"{w}x{h}+{x}+{y}")

        self.window.protocol("WM_DELETE_WINDOW", self._on_close_attempt)

        theme = LEVEL_THEMES[min(self.level, len(LEVEL_THEMES) - 1)]

        header = ctk.CTkFrame(self.window, fg_color=theme["header"], corner_radius=0, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(expand=True)

        ctk.CTkLabel(
            title_frame,
            text=theme["icon"],
            font=ctk.CTkFont(size=32),
            text_color="white",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            title_frame,
            text=theme["title"],
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white",
        ).pack(side="left")

        if self.streak > 0:
            streak_label = ctk.CTkLabel(
                header,
                text=f"🔥 {self.streak} day streak",
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="#00000040",
                text_color="white",
                corner_radius=12,
                padx=10,
                pady=4,
            )
            streak_label.pack(side="right", padx=15)

        body = ctk.CTkFrame(self.window, fg_color="#ffffff", corner_radius=0)
        body.pack(fill="both", expand=True)

        ctk.CTkLabel(
            body,
            text=self.message,
            font=ctk.CTkFont(size=16),
            text_color="#1f2937",
            wraplength=400,
        ).pack(padx=35, pady=(28, 6), anchor="w")

        ctk.CTkLabel(
            body,
            text="Your health matters. Please go to bed.",
            font=ctk.CTkFont(size=13),
            text_color="#6b7280",
        ).pack(padx=35, pady=(0, 10), anchor="w")

        if self.level < 4:
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            day_name = tomorrow.strftime("%A")
            ctk.CTkLabel(
                body,
                text=f"Tomorrow is {day_name}, got any plans?",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=theme["accent"],
            ).pack(padx=35, pady=(0, 10), anchor="w")

        dismiss_btn = ctk.CTkButton(
            body,
            text="Yeah, I'm going to sleep",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=theme["accent"],
            hover_color=theme["hover"],
            text_color="white",
            height=44,
            corner_radius=8,
            command=self._dismiss,
            cursor="hand2",
        )
        dismiss_btn.pack(padx=35, fill="x")

        if self.on_skip_today:
            skip_btn = ctk.CTkButton(
                body,
                text="Skip today",
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                hover_color=theme["skip_hover"],
                text_color=theme["skip"],
                height=28,
                corner_radius=4,
                command=self._skip_today,
                cursor="hand2",
            )
            skip_btn.place(relx=1.0, rely=1.0, x=-20, y=-12, anchor="se")

            def on_skip_enter(e):
                skip_btn.configure(fg_color=theme["skip_hover"], text_color="white")

            def on_skip_leave(e):
                skip_btn.configure(fg_color="transparent", text_color=theme["skip"])

            skip_btn.bind("<Enter>", on_skip_enter)
            skip_btn.bind("<Leave>", on_skip_leave)

        bottom = ctk.CTkFrame(self.window, fg_color="#f3f4f6", corner_radius=0, height=3)
        bottom.pack(fill="x", side="bottom")

        if self.level == 2:
            self._start_alarm()

    def show_countdown(self, seconds):
        self._play_appear_sound()

        self.window = ctk.CTkToplevel()
        self.window.title("Locking PC")
        self.window.configure(fg_color="#ffffff")
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)

        self.window.after(10, lambda: self._center_and_build_countdown(seconds))

    def _center_and_build_countdown(self, seconds):
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        w, h = 480, 360
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.window.geometry(f"{w}x{h}+{x}+{y}")
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)

        self.countdown_value = seconds

        header = ctk.CTkFrame(self.window, fg_color="#dc2626", corner_radius=0, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(expand=True)

        ctk.CTkLabel(
            title_frame,
            text="⚠",
            font=ctk.CTkFont(size=32),
            text_color="white",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            title_frame,
            text="FINAL WARNING",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white",
        ).pack(side="left")

        body = ctk.CTkFrame(self.window, fg_color="#ffffff", corner_radius=0)
        body.pack(fill="both", expand=True)

        ctk.CTkLabel(
            body,
            text="That's it. I'm locking your PC.",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#dc2626",
        ).pack(padx=35, pady=(28, 6), anchor="w")

        self.countdown_label = ctk.CTkLabel(
            body,
            text=str(self.countdown_value),
            font=ctk.CTkFont(size=80, weight="bold"),
            text_color="#dc2626",
        )
        self.countdown_label.pack(expand=True)

        bottom = ctk.CTkFrame(self.window, fg_color="#f3f4f6", corner_radius=0, height=3)
        bottom.pack(fill="x", side="bottom")

        self._tick_countdown()

    def _tick_countdown(self):
        if self.countdown_value <= 0:
            self.window.destroy()
            self.on_lock()
            return

        self.countdown_label.configure(text=str(self.countdown_value))
        winsound.Beep(800, 300)
        self.countdown_value -= 1
        self.window.after(1000, self._tick_countdown)

    def _start_alarm(self):
        self.alarm_active = True
        threading.Thread(target=self._alarm_loop, daemon=True).start()

    def _alarm_loop(self):
        while self.alarm_active:
            if self.level == 2:
                winsound.Beep(600, 400)
            time.sleep(2)

    def _dismiss(self):
        self.alarm_active = False
        if self.window:
            self.window.destroy()
        self.on_dismiss()

    def _skip_today(self):
        self.alarm_active = False
        if self.window:
            self.window.destroy()
        if self.on_skip_today:
            self.on_skip_today()

    def _on_close_attempt(self):
        pass


class MorningGreeting:
    def __init__(self, sleep_time, on_close):
        self.sleep_time = sleep_time
        self.on_close = on_close
        self.window = None

    def show(self):
        self.window = ctk.CTkToplevel()
        self.window.title("Good Morning")
        self.window.configure(fg_color="#ffffff")
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)

        self.window.after(10, self._center_and_build)

    def _center_and_build(self):
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        w, h = 400, 220
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.window.geometry(f"{w}x{h}+{x}+{y}")

        self.window.protocol("WM_DELETE_WINDOW", self._dismiss)

        header = ctk.CTkFrame(self.window, fg_color="#10b981", corner_radius=0, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(expand=True)

        ctk.CTkLabel(
            title_frame,
            text="☀",
            font=ctk.CTkFont(size=28),
            text_color="white",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            title_frame,
            text="GOOD MORNING",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
        ).pack(side="left")

        body = ctk.CTkFrame(self.window, fg_color="#ffffff", corner_radius=0)
        body.pack(fill="both", expand=True)

        if self.sleep_time:
            msg = f"You went to sleep at {self.sleep_time} last night."
        else:
            msg = "Good morning! Hope you slept well."

        ctk.CTkLabel(
            body,
            text=msg,
            font=ctk.CTkFont(size=14),
            text_color="#1f2937",
        ).pack(padx=30, pady=(20, 5), anchor="w")

        ctk.CTkLabel(
            body,
            text="Have a great day ahead!",
            font=ctk.CTkFont(size=12),
            text_color="#6b7280",
        ).pack(padx=30, pady=(0, 15), anchor="w")

        dismiss_btn = ctk.CTkButton(
            body,
            text="Got it",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            text_color="white",
            height=34,
            corner_radius=6,
            command=self._dismiss,
            cursor="hand2",
        )
        dismiss_btn.pack(padx=30, fill="x")

        self.window.after(10000, self._dismiss)

    def _dismiss(self):
        if self.window:
            self.window.destroy()
        if self.on_close:
            self.on_close()


class SleepStats:
    def __init__(self, weekly_summary, on_close):
        self.weekly_summary = weekly_summary
        self.on_close = on_close
        self.window = None

    def show(self):
        self.window = ctk.CTkToplevel()
        self.window.title("Sleep Stats")
        self.window.configure(fg_color="#ffffff")
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)

        self.window.after(10, self._center_and_build)

    def _center_and_build(self):
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        w, h = 400, 260
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.window.geometry(f"{w}x{h}+{x}+{y}")

        self.window.protocol("WM_DELETE_WINDOW", self._dismiss)

        header = ctk.CTkFrame(self.window, fg_color="#6366f1", corner_radius=0, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(expand=True)

        ctk.CTkLabel(
            title_frame,
            text="📊",
            font=ctk.CTkFont(size=28),
            text_color="white",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            title_frame,
            text="SLEEP STATS",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
        ).pack(side="left")

        body = ctk.CTkFrame(self.window, fg_color="#ffffff", corner_radius=0)
        body.pack(fill="both", expand=True)

        if self.weekly_summary:
            ws = self.weekly_summary
            stats_text = f"Nights slept: {ws['nights_slept']}"
            ctk.CTkLabel(
                body,
                text=stats_text,
                font=ctk.CTkFont(size=14),
                text_color="#1f2937",
            ).pack(padx=30, pady=(20, 5), anchor="w")

            avg_text = f"Average sleep time: {ws['avg_time']}"
            ctk.CTkLabel(
                body,
                text=avg_text,
                font=ctk.CTkFont(size=14),
                text_color="#1f2937",
            ).pack(padx=30, pady=(0, 5), anchor="w")

            if ws["skips"] > 0:
                skip_text = f"Skipped: {ws['skips']} days"
                ctk.CTkLabel(
                    body,
                    text=skip_text,
                    font=ctk.CTkFont(size=14),
                    text_color="#ef4444",
                ).pack(padx=30, pady=(0, 10), anchor="w")
            else:
                ctk.CTkLabel(
                    body,
                    text="No skips this week! Keep it up.",
                    font=ctk.CTkFont(size=12),
                    text_color="#10b981",
                ).pack(padx=30, pady=(0, 10), anchor="w")
        else:
            ctk.CTkLabel(
                body,
                text="No sleep data yet.\nStart sleeping on time to track your stats!",
                font=ctk.CTkFont(size=13),
                text_color="#6b7280",
            ).pack(padx=30, pady=(25, 10), anchor="w")

        dismiss_btn = ctk.CTkButton(
            body,
            text="Got it",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6366f1",
            hover_color="#4f46e5",
            text_color="white",
            height=34,
            corner_radius=6,
            command=self._dismiss,
            cursor="hand2",
        )
        dismiss_btn.pack(padx=30, fill="x")

        self.window.after(15000, self._dismiss)

    def _dismiss(self):
        if self.window:
            self.window.destroy()
        if self.on_close:
            self.on_close()
