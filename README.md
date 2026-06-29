# Sleep Notifier

A Windows desktop app that forces you to sleep on time. It fires escalating pop-up reminders at your configured bedtime, and if you ignore them all, it locks your PC.

## Features

- **Escalating reminders** — Starts polite, gets angrier with each level
- **Un-closable pop-ups** — Always on top, no X button, you can't escape
- **Auto-lock** — Locks your PC after all warnings are ignored
- **Sleep streak** — Tracks consecutive nights you slept on time
- **Sleep log** — Records when you sleep for self-awareness
- **Weekly summary** — Shows your sleep average and patterns
- **Tomorrow reminder** — Tells you what day it is tomorrow so you can plan
- **Morning greeting** — Shows when you wake up, how long you slept
- **Skip today** — One-day pause when you really need to stay up
- **Auto-start** — Runs in background on Windows login, no terminal window

## Escalation Timeline

| Level | Time | Gap | Style |
|-------|------|-----|-------|
| 1 | 23:00 | — | Calm blue, polite message |
| 2 | 23:15 | +15 min | Orange, annoyed, alarm sounds |
| 3 | 23:25 | +10 min | Red, angry, urgent beeping |
| 4 | 23:30 | +5 min | Dark red, furious, relentless alarm |
| Lock | 23:32 | +2 min | 5-second countdown, then Windows lock |

## Setup

### Quick Start

```powershell
git clone https://github.com/CodeOfMugiwara/Sleep_Notifier.git
cd Sleep_Notifier
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\setup_task.ps1
```

### Manual Start

```
Double-click start.bat
```

### Stop

```
Double-click stop.bat
```

## Configuration

Edit `config.json` to customize:

```json
{
  "reminder_time": "23:00",
  "active_hours": [23, 4],
  "escalation_gaps_min": [0, 15, 10, 5, 2],
  "lock_countdown_sec": 5,
  "messages": [
    "Hey, it's late. Time to sleep!",
    "Seriously, GO TO SLEEP.",
    "SLEEP. NOW. This is your LAST warning.",
    "I'M NOT ASKING AGAIN.",
    "That's it. I'm locking your PC."
  ],
  "colors": ["#3498db", "#e67e22", "#e74c3c", "#8b0000", "#c0392b"]
}
```

| Setting | Description |
|---------|-------------|
| `reminder_time` | When the first reminder fires (24h format) |
| `active_hours` | Only fire between these hours (e.g., 23:00-04:00) |
| `escalation_gaps_min` | Minutes between each escalation level |
| `lock_countdown_sec` | Countdown before auto-lock on final warning |
| `messages` | Custom messages for each escalation level |
| `colors` | Header colors for each level |

## Files

```
Sleep_Notifier/
├── config.json          # Settings
├── main.py              # Scheduler + background logic
├── notifier.py          # GUI pop-ups (customtkinter)
├── requirements.txt     # Dependencies
├── setup_task.ps1       # Auto-start on Windows login
├── start.bat            # Manual start (no terminal)
├── stop.bat             # Kill the notifier
├── .gitignore           # venv, logs, runtime files
├── streak.json          # Sleep streak data (auto-created)
├── sleep_log.json       # Sleep history (auto-created)
└── morning_greeted.json # Morning greeting flag (auto-created)
```

## Requirements

- Windows 10/11
- Python 3.10+
- No extra system dependencies

## Tech Stack

- **Python** — Core language
- **customtkinter** — Modern GUI widgets
- **winsound** — Alarm sounds + UAC notification
- **Windows Task Scheduler** — Auto-start on login
- **json** — Config and data storage (no database needed)
