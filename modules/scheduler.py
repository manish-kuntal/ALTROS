# ============================================================
#  ALTROS Module: Scheduler — "self controllable" PC actions
#  Lets ALTROS run PC Control commands on its own: on an
#  interval, at a daily time, or once after a delay. Runs in a
#  background daemon thread; survives restarts (saved to JSON).
#
#  Scheduled commands go through the SAME PermissionManager as
#  everything else — a scheduled "delete" still queues a
#  confirmation and waits for you to say 'haan', it does not
#  auto-approve itself just because no one typed the command.
# ============================================================

import os
import re
import json
import time
import threading
from datetime import datetime, timedelta
from modules.base import BaseModule
from core.action_logger import action_logger

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../modules/.. -> C:\ALTROS
TASKS_PATH = os.path.join(_ROOT, "data", "memory", "scheduled_tasks.json")
CHECK_EVERY = 20  # seconds between due-checks

TRIGGERS = [
    "schedule", "har roz", "daily", "har ghante", "har minute",
    "baad me karo", "minute baad", "ghante baad",
    "schedule dikhao", "schedule hatao", "task list",
]


class TaskScheduler:
    """Background loop that fires saved commands through `executor_fn`."""

    def __init__(self, executor_fn):
        self.executor_fn = executor_fn
        self.tasks = self._load()
        self._thread = None
        self._stop = threading.Event()

    def _load(self):
        if not os.path.exists(TASKS_PATH):
            return []
        try:
            with open(TASKS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self):
        os.makedirs(os.path.dirname(TASKS_PATH), exist_ok=True)
        try:
            with open(TASKS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, kind: str, value, command: str) -> str:
        """kind: 'interval_sec' | 'daily' (value 'HH:MM') | 'once' (value = seconds from now)"""
        task_id = str(int(time.time() * 1000))
        task = {"id": task_id, "kind": kind, "value": value, "command": command, "enabled": True}
        if kind == "once":
            task["fire_at"] = (datetime.now() + timedelta(seconds=value)).isoformat()
        elif kind == "interval_sec":
            task["next_fire"] = (datetime.now() + timedelta(seconds=value)).isoformat()
        self.tasks.append(task)
        self._save()
        return task_id

    def remove(self, task_id: str) -> bool:
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        self._save()
        return len(self.tasks) < before

    def list_tasks(self):
        return list(self.tasks)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            now = datetime.now()
            for task in list(self.tasks):
                if not task.get("enabled", True):
                    continue
                try:
                    if task["kind"] == "once":
                        if now >= datetime.fromisoformat(task["fire_at"]):
                            self._fire(task)
                            self.remove(task["id"])
                    elif task["kind"] == "interval_sec":
                        if now >= datetime.fromisoformat(task["next_fire"]):
                            self._fire(task)
                            task["next_fire"] = (now + timedelta(seconds=task["value"])).isoformat()
                            self._save()
                    elif task["kind"] == "daily":
                        hh, mm = map(int, task["value"].split(":"))
                        today_str = now.strftime("%Y-%m-%d")
                        if now.hour == hh and now.minute == mm and task.get("last_fired") != today_str:
                            self._fire(task)
                            task["last_fired"] = today_str
                            self._save()
                except Exception as e:
                    action_logger.log("scheduler_error", {"task": task}, str(e), False)
            time.sleep(CHECK_EVERY)

    def _fire(self, task):
        try:
            result = self.executor_fn(task["command"])
            action_logger.log("scheduled_task", {"command": task["command"]}, result or "(no output)", True)
        except Exception as e:
            action_logger.log("scheduled_task", {"command": task["command"]}, str(e), False)


class SchedulerModule(BaseModule):
    name = "scheduler"
    description = "Schedule PC Control commands to run on their own (interval/daily/once)"

    def __init__(self, executor_fn):
        self._ready = False
        self._scheduler = TaskScheduler(executor_fn)

    def on_enable(self):
        self._ready = True
        self._scheduler.start()
        print(f"     \u2705 Scheduler module ready — {len(self._scheduler.tasks)} saved task(s) loaded")

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready:
            return False
        q = query.lower()
        return any(t in q for t in TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        q = query.lower().strip()

        if "schedule dikhao" in q or "task list" in q:
            return self._list()

        if "schedule hatao" in q:
            m = re.search(r'(\d{6,})', q)
            if not m:
                return "PC Control: Kaunsa schedule ID hatana hai? 'schedule dikhao' se ID dekho."
            ok = self._scheduler.remove(m.group(1))
            return f"PC Control: Schedule {'hata diya' if ok else 'nahi mila'}. \u2705"

        command = self._extract_command(query)
        if not command:
            return ('PC Control: Format — \'har roz 9:00 baje "chrome kholo" schedule karo\', '
                    '\'har 30 minute baad "screenshot lo" schedule karo\', '
                    '\'5 minute baad "notepad kholo" schedule karo\'')

        if "har roz" in q or "daily" in q:
            m = re.search(r'(\d{1,2}):(\d{2})', q)
            if not m:
                return 'PC Control: Time batao HH:MM format mein — \'har roz 9:00 baje "..." schedule karo\''
            time_str = f"{int(m.group(1)):02d}:{m.group(2)}"
            task_id = self._scheduler.add("daily", time_str, command)
            return f'PC Control: Roz {time_str} baje chalega — "{command}" \u2705 (id: {task_id})'

        if "har" in q and ("minute" in q or "ghante" in q):
            m = re.search(r'(\d+)', q)
            if not m:
                return "PC Control: Kitne minute/ghante ka gap? e.g. 'har 30 minute baad ... schedule karo'"
            n = int(m.group(1))
            unit = "ghante" if "ghante" in q else "minute"
            seconds = n * 3600 if unit == "ghante" else n * 60
            task_id = self._scheduler.add("interval_sec", seconds, command)
            return f'PC Control: Har {n} {unit} chalega — "{command}" \u2705 (id: {task_id})'

        m = re.search(r'(\d+)\s*(minute|ghante)\s*baad', q)
        if m:
            n = int(m.group(1))
            seconds = n * 3600 if m.group(2) == "ghante" else n * 60
            task_id = self._scheduler.add("once", seconds, command)
            return f'PC Control: {n} {m.group(2)} baad chalega — "{command}" \u2705 (id: {task_id})'

        return "PC Control: Kab chalana hai? 'har roz 9:00 baje', 'har 30 minute', ya '5 minute baad' batao."

    def _list(self) -> str:
        tasks = self._scheduler.list_tasks()
        if not tasks:
            return "PC Control: Koi schedule set nahi hai."
        lines = ["PC Control: Scheduled tasks:"]
        labels = {"daily": lambda t: f"roz {t['value']} baje", "interval_sec": lambda t: f"har {t['value']}s",
                  "once": lambda t: "ek baar"}
        for t in tasks:
            lines.append(f"  \u23f0 [{t['id']}] {labels[t['kind']](t)} — \"{t['command']}\"")
        return "\n".join(lines)

    def _extract_command(self, query: str) -> str:
        m = re.search(r'"([^"]+)"', query)
        return m.group(1) if m else ""
