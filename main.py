import json
import time
import datetime
import subprocess
import sys
import threading
import queue
import customtkinter as ctk
from pathlib import Path
from notifier import SleepNotifier


CONFIG_PATH = Path(__file__).parent / "config.json"
LOG_PATH = Path(__file__).parent / "notifier.log"
PID_PATH = Path(__file__).parent / "notifier.pid"
SKIP_TODAY_PATH = Path(__file__).parent / "skip_today.json"

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


def cleanup_skip_if_old():
    if SKIP_TODAY_PATH.exists():
        try:
            data = json.loads(SKIP_TODAY_PATH.read_text())
            skip_date = datetime.date.fromisoformat(data["date"])
            if skip_date != datetime.date.today():
                SKIP_TODAY_PATH.unlink(missing_ok=True)
        except Exception:
            SKIP_TODAY_PATH.unlink(missing_ok=True)


class SleepScheduler:
    def __init__(self):
        self.config = load_config()
        self.current_level = 0
        self.running = True
        self.escalation_active = False

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
                ui_queue.put(("show", messages[level], colors[level], level))
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

            self.config = load_config()

            if not self.is_within_active_hours():
                target = self.get_target_time()
                wait = self.seconds_until(target)
                next_time = datetime.datetime.now() + datetime.timedelta(seconds=wait)
                log(f"Outside active hours. Next reminder at: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
                time.sleep(wait)
                continue

            if is_skipped_today():
                log("Today is skipped. Waiting for next day...")
                target = self.get_target_time()
                wait = self.seconds_until(target)
                next_time = datetime.datetime.now() + datetime.timedelta(seconds=wait)
                log(f"Next reminder at: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
                time.sleep(wait)
                continue

            log("SLEEP REMINDER TRIGGERED")
            self.run_escalation()
            self.current_level = 0
            time.sleep(60)


class App:
    def __init__(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.root = ctk.CTk()
        self.root.withdraw()
        self.current_notifier = None

    def process_queue(self):
        try:
            while True:
                cmd = ui_queue.get_nowait()

                if cmd[0] == "show":
                    _, message, color, level = cmd
                    self._show_notifier(message, color, level)
                    return

                elif cmd[0] == "countdown":
                    _, message, seconds = cmd
                    self._show_countdown(message, seconds)
                    return

                elif cmd[0] == "stop":
                    self.root.destroy()
                    return

        except queue.Empty:
            pass

        self.root.after(100, self.process_queue)

    def _show_notifier(self, message, color, level):
        def on_dismiss():
            ui_done.set()
            self.root.after(100, self.process_queue)

        def on_skip_today():
            mark_skip_today()
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
        )
        self.current_notifier.show()

    def _show_countdown(self, message, seconds):
        def on_lock_done():
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
        )
        self.current_notifier.show_countdown(seconds)

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
