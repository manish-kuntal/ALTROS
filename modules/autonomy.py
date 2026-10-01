# ============================================================
#  ALTROS Module: Autonomy (Phase 6)
#  Daily tasks, reminders, proactive suggestions
# ============================================================

import json
import os
import threading
import time
from datetime import datetime, timedelta
from modules.base import BaseModule

TASKS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "memory", "tasks.json")


class AutonomyModule(BaseModule):
    name = "autonomy"
    description = "Daily tasks, reminders, proactive AI suggestions"

    def __init__(self):
        self._ready = False
        self._tasks: list[dict] = []
        self._callback = None
        self._thread = None

    def on_enable(self):
        self._tasks = self._load_tasks()
        self._ready = True
        print("     ✅ Autonomy module ready")

    def set_callback(self, callback):
        """Callback jab reminder fire ho."""
        self._callback = callback

    def start(self):
        if not self._ready:
            return
        self._thread = threading.Thread(target=self._reminder_loop, daemon=True)
        self._thread.start()
        print("     ⏰ Reminder system active")

    def can_handle(self, query: str, context: dict) -> bool:
        q = query.lower()
        return any(w in q for w in [
            "remind", "reminder", "yaad dilao", "task", "schedule",
            "alarm", "kal", "aaj", "tomorrow", "daily", "roz"
        ])

    def handle(self, query: str, context: dict) -> str:
        q = query.lower()

        if any(w in q for w in ["add task", "task add", "remind me", "yaad dilao"]):
            return ""  # Brain handle karega with context

        if any(w in q for w in ["tasks", "reminders", "kya karna hai", "list"]):
            return self._get_tasks_context()

        return ""

    def add_task(self, title: str, remind_at: str = None, priority: int = 5):
        task = {
            "id": len(self._tasks) + 1,
            "title": title,
            "remind_at": remind_at,
            "priority": priority,
            "done": False,
            "created": datetime.now().isoformat()
        }
        self._tasks.append(task)
        self._save_tasks()
        return f"Task add ho gaya: '{title}'"

    def get_pending_tasks(self) -> list:
        return [t for t in self._tasks if not t.get("done")]

    def _get_tasks_context(self) -> str:
        pending = self.get_pending_tasks()
        if not pending:
            return "Abhi koi pending task nahi hai."
        lines = ["Pending tasks:"]
        for t in sorted(pending, key=lambda x: x.get("priority", 5), reverse=True):
            lines.append(f"  [{t['priority']}/10] {t['title']}")
        return "\n".join(lines)

    def get_daily_briefing(self) -> str:
        now = datetime.now()
        pending = self.get_pending_tasks()
        briefing = f"Aaj ka din: {now.strftime('%A, %d %B %Y')}\n"
        if pending:
            briefing += f"\nPending tasks ({len(pending)}):\n"
            for t in pending[:5]:
                briefing += f"  - {t['title']}\n"
        else:
            briefing += "\nKoi pending task nahi — clean slate!"
        return briefing

    def _reminder_loop(self):
        while True:
            time.sleep(60)  # Check every minute
            now = datetime.now()
            for task in self._tasks:
                if task.get("done"):
                    continue
                remind_at = task.get("remind_at")
                if not remind_at:
                    continue
                try:
                    remind_time = datetime.fromisoformat(remind_at)
                    if abs((now - remind_time).total_seconds()) < 60:
                        if self._callback:
                            self._callback(f"⏰ Reminder: {task['title']}")
                        task["done"] = True
                        self._save_tasks()
                except Exception:
                    pass

    def _load_tasks(self) -> list:
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_tasks(self):
        os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._tasks, f, ensure_ascii=False, indent=2)
