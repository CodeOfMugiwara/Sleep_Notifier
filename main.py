import json
import time
import datetime
import subprocess
import sys
import threading
import queue
import customtkinter as ctk
from pathlib import Path
from notifier import SleepNotifier, MorningGreeting, SleepStats


CONFIG_PATH = Path(__file__).parent / "config.json"
LOG_PATH = Path(__file__).parent / "notifier.log"
PID_PATH = Path(__file__).parent / "notifier.pid"
SKIP_TODAY_PATH = Path(__file__).parent / "skip_today.json"
STREAK_PATH = Path(__file__).parent / "streak.json"
SLEEP_LOG_PATH = Path(__file__).parent / "sleep_log.json"
MORNING_GREETED_PATH = Path(__file__).parent / "morning_greeted.json"

ui_queue = queue.Queue()
scheduler_ready = threading.Event()
ui_done = threading.Event()
skip_today_event = threading.Event()


def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def lock_pc():
    subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])


def is_already_running():
    if PID_PATH.exists():
        old_pid = PID_PATH.read_text().strip()
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {old_pid}", "/NH"],
                capture_output=True,
                text=True,
            )
            if old_pid in result.output:
                return True
        except Exception:
            pass
        PID_PATH.unlink(missing_ok=True)
    return False


def write_pid():
    PID_PATH.write_text(str(subprocess.os.getpid()))


def remove_pid():
    PID_PATH.unlink(missing_ok=True)


def is_skipped_today():
    if SKIP_TODAY_PATH.exists():
        try:
            data = json.loads(SKIP_TODAY_PATH.read_text())
            skip_date = datetime.date.fromisoformat(data["date"])
            return skip_date == datetime.date.today()
        except Exception:
            pass
    return False


def mark_skip_today():
    SKIP_TODAY_PATH.write_text(json.dumps({"date": datetime.date.today().isoformat()}))
    log_sleep_event("skip")


def cleanup_skip_if_old():
    if SKIP_TODAY_PATH.exists():
        try:
            data = json.loads(SKIP_TODAY_PATH.read_text())
            skip_date = datetime.date.fromisoformat(data["date"])
            if skip_date != datetime.date.today():
                SKIP_TODAY_PATH.unlink(missing_ok=True)
        except Exception:
            SKIP_TODAY_PATH.unlink(missing_ok=True)


# --- Streak ---

def load_streak():
    if STREAK_PATH.exists():
        try:
            return json.loads(STREAK_PATH.read_text())
        except Exception:
            pass
    return {"streak": 0, "last_sleep_date": None}


def save_streak(data):
    STREAK_PATH.write_text(json.dumps(data))


def record_sleep():
    today = datetime.date.today().isoformat()
    streak_data = load_streak()
    last = streak_data.get("last_sleep_date")

    if last == today:
        return streak_data["streak"]

    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    if last == yesterday:
        streak_data["streak"] += 1
    else:
        streak_data["streak"] = 1

    streak_data["last_sleep_date"] = today
    save_streak(streak_data)
    return streak_data["streak"]


def reset_streak():
    save_streak({"streak": 0, "last_sleep_date": None})


# --- Sleep Log ---

def load_sleep_log():
    if SLEEP_LOG_PATH.exists():
        try:
            return json.loads(SLEEP_LOG_PATH.read_text())
        except Exception:
            pass
    return []


def save_sleep_log(log_data):
    SLEEP_LOG_PATH.write_text(json.dumps(log_data, indent=2))


def log_sleep_event(method):
    now = datetime.datetime.now()
    entry = {
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M"),
        "method": method,
    }
    log_data = load_sleep_log()
    log_data.append(entry)
    if len(log_data) > 90:
        log_data = log_data[-90:]
    save_sleep_log(log_data)


def get_weekly_summary():
    log_data = load_sleep_log()
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)

    weekly = [
        e for e in log_data
        if datetime.date.fromisoformat(e["date"]) >= week_ago and e["method"] != "skip"
    ]

    if not weekly:
        return None

    total_minutes = 0
    for e in weekly:
        h, m = map(int, e["time"].split(":"))
        minutes = h * 60 + m
        if minutes < 360:
            minutes += 1440
        total_minutes += minutes

    avg_minutes = total_minutes // len(weekly)
    avg_h = (avg_minutes // 60) % 24
    avg_m = avg_minutes % 60

    nights_slept = len(weekly)
    skips = len([
        e for e in log_data
        if datetime.date.fromisoformat(e["date"]) >= week_ago and e["method"] == "skip"
    ])

    return {
        "avg_time": f"{avg_h:02d}:{avg_m:02d}",
        "nights_slept": nights_slept,
        "skips": skips,
    }


# --- Morning Greeting ---

def was_morning_greeted():
    if MORNING_GREETED_PATH.exists():
        try:
            data = json.loads(MORNING_GREETED_PATH.read_text())
            return data["date"] == datetime.date.today().isoformat()
        except Exception:
            pass
    return False


def mark_morning_greeted():
    MORNING_GREETED_PATH.write_text(
        json.dumps({"date": datetime.date.today().isoformat()})
    )


def get_last_sleep_time():
    log_data = load_sleep_log()
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    for entry in reversed(log_data):
        if entry["date"] in (today, yesterday) and entry["method"] != "skip":
            return entry["time"], entry["method"]
    return None, None


# --- Scheduler ---

class SleepScheduler:
    def __init__(self):
        self.config = load_config()
        self.current_level = 0
        self.running = True
        self.escalation_active = False
        self.triggered_today = False
        self.morning_handled_today = False

    def get_target_time(self):
        h, m = self.config["reminder_time"].split(":")
        return datetime.time(int(h), int(m))

    def seconds_until(self, target_time):
        now = datetime.datetime.now()
        target = datetime.datetime.combine(now.date(), target_time)
        if now >= target:
            target += datetime.timedelta(days=1)
        return (target - now).total_seconds()

    def is_within_active_hours(self):
        now = datetime.datetime.now().time()
        active = self.config.get("active_hours", [23, 4])
        start_h, end_h = active[0], active[1]
        if start_h > end_h:
            return now >= datetime.time(start_h) or now < datetime.time(end_h)
        else:
            return datetime.time(start_h) <= now < datetime.time(end_h)

    def run_escalation(self):
        gaps = self.config["escalation_gaps_min"]
        messages = self.config["messages"]
        colors = self.config["colors"]

        streak_data = load_streak()
        streak = streak_data.get("streak", 0)

        self.escalation_active = True

        for level in range(len(messages)):
            self.current_level = level

            if level > 0:
                wait_min = gaps[level]
                log(f"  Waiting {wait_min} min for next level...")
                time.sleep(wait_min * 60)

            if not self.running:
                return

            skip_today_event.clear()
            ui_done.clear()

            if level < 4:
                log(f"Level {level + 1}: {messages[level]}")
                ui_queue.put(("show", messages[level], colors[level], level, streak))
                ui_done.wait()

                if skip_today_event.is_set():
                    log("User skipped today. Resuming tomorrow.")
                    self.escalation_active = False
                    return
            else:
                log(f"FINAL: {messages[level]}")
                ui_queue.put(("countdown", messages[level], self.config["lock_countdown_sec"]))
                ui_done.wait()
                self.escalation_active = False
                return

        self.escalation_active = False
        self.current_level = 0

    def check_morning_greeting(self):
        if self.morning_handled_today:
            return

        if was_morning_greeted():
            self.morning_handled_today = True
            return

        sleep_time, method = get_last_sleep_time()
        summary = get_weekly_summary()
        mark_morning_greeted()
        log("Morning greeting shown.")
        self.morning_handled_today = True
        ui_queue.put(("morning", sleep_time, method, summary))

    def start(self):
        log("=" * 40)
        log("SLEEP NOTIFIER - Started")
        log("=" * 40)
        scheduler_ready.set()

        last_cleanup_date = None

        while self.running:
            today = datetime.date.today()
            if last_cleanup_date != today:
                cleanup_skip_if_old()
                last_cleanup_date = today
                self.triggered_today = False
                self.morning_handled_today = False

            self.check_morning_greeting()
            self.config = load_config()

            now = datetime.datetime.now()
            target_time = self.get_target_time()
            target = datetime.datetime.combine(now.date(), target_time)

            if self.is_within_active_hours() and not is_skipped_today() and now >= target and not self.triggered_today:
                log("SLEEP REMINDER TRIGGERED")
                self.run_escalation()
                self.current_level = 0
                self.triggered_today = True
                time.sleep(60)

            time.sleep(30)


class App:
    def __init__(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.root = ctk.CTk()
        self.root.after(0, self._hide_root)
        self.current_notifier = None
        self.notifier_windows = []

    def _hide_root(self):
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.geometry("1x1+9999+9999")

    def process_queue(self):
        try:
            while True:
                cmd = ui_queue.get_nowait()

                if cmd[0] == "show":
                    _, message, color, level, streak = cmd
                    self._show_notifier(message, color, level, streak)
                    return

                elif cmd[0] == "countdown":
                    _, message, seconds = cmd
                    self._show_countdown(message, seconds)
                    return

                elif cmd[0] == "morning":
                    _, sleep_time, method, summary = cmd
                    self._show_morning(sleep_time, method, summary)
                    return

                elif cmd[0] == "stop":
                    self.root.destroy()
                    return

        except queue.Empty:
            pass

        self.root.after(100, self.process_queue)

    def _show_notifier(self, message, color, level, streak):
        def on_dismiss():
            record_sleep()
            log_sleep_event("dismiss")
            ui_done.set()
            self.root.after(100, self.process_queue)

        def on_skip_today():
            mark_skip_today()
            reset_streak()
            skip_today_event.set()
            ui_done.set()
            self.root.after(100, self.process_queue)

        self.current_notifier = SleepNotifier(
            message=message,
            color=color,
            level=level,
            on_dismiss=on_dismiss,
            on_lock=lock_pc,
            on_skip_today=on_skip_today,
            streak=streak,
        )
        self.current_notifier.show()

    def _show_countdown(self, message, seconds):
        def on_lock_done():
            record_sleep()
            log_sleep_event("lock")
            ui_done.set()
            self.root.after(100, self.process_queue)

        original_lock = lock_pc

        def wrapped_lock():
            original_lock()
            on_lock_done()

        self.current_notifier = SleepNotifier(
            message=message,
            color="#000000",
            level=4,
            on_dismiss=lambda: None,
            on_lock=wrapped_lock,
            on_skip_today=None,
            streak=0,
        )
        self.current_notifier.show_countdown(seconds)

    def _show_morning(self, sleep_time, method, summary):
        def on_greeting_close():
            if summary:
                stats = SleepStats(weekly_summary=summary, on_close=self._on_stats_close)
                stats.show()
            else:
                self.root.after(100, self.process_queue)

        greeting = MorningGreeting(sleep_time=sleep_time, on_close=on_greeting_close)
        greeting.show()

    def _on_stats_close(self):
        self.root.after(100, self.process_queue)

    def run(self):
        self.root.after(100, self.process_queue)
        self.root.mainloop()


def main():
    if is_already_running():
        log("Already running. Exiting.")
        sys.exit(0)

    write_pid()

    scheduler = SleepScheduler()
    thread = threading.Thread(target=scheduler.start, daemon=True)
    thread.start()

    scheduler_ready.wait()

    app = App()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.running = False
        ui_queue.put(("stop",))
        remove_pid()
        log("Notifier stopped.")


if __name__ == "__main__":
    main()
