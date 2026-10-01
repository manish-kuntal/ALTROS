# ============================================================
#  ALTROS Module: Event Watcher — react to what happens, not
#  just the clock (that's the scheduler's job).
#
#  Two trigger types:
#    - folder_new_file   : a new file shows up in a watched folder
#    - process_started / process_stopped : a named process
#      transitions from not-running -> running, or vice versa
#
#  Like the scheduler, watched commands run through the SAME
#  handle() as everything typed — a fired "delete" still queues
#  a confirmation and waits, it doesn't auto-approve itself.
#
#  pip install psutil   (already needed by system_control.py)
# ============================================================

import os
import re
import json
import time
import threading
from modules.base import BaseModule
from core.action_logger import action_logger

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../modules/.. -> C:\ALTROS
WATCHES_PATH = os.path.join(_ROOT, "data", "memory", "event_watches.json")
CHECK_EVERY = 5  # seconds — snappier than the scheduler since these are reactive

TRIGGERS = [
    "naya file", "file aaye", "jab ",
    "watch dikhao", "events dikhao", "watch list", "watch hatao",
]


class EventWatcher:
    """Background loop: polls folders/processes, fires `executor_fn` on change."""

    def __init__(self, executor_fn):
        self.executor_fn = executor_fn
        self.watches = self._load()
        self._thread = None
        self._stop = threading.Event()
        self._known_files = {}    # watch_id -> set(filenames) as of last check
        self._known_running = {}  # watch_id -> bool, was the process running last check
        self._prime_baselines()

    def _load(self):
        if not os.path.exists(WATCHES_PATH):
            return []
        try:
            with open(WATCHES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self):
        os.makedirs(os.path.dirname(WATCHES_PATH), exist_ok=True)
        try:
            with open(WATCHES_PATH, "w", encoding="utf-8") as f:
                json.dump(self.watches, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _prime_baselines(self):
        """On (re)start, snapshot current state per watch so we only fire on
        CHANGES from here on, not on whatever already exists/is running."""
        for w in self.watches:
            if w["kind"] == "folder_new_file":
                folder = w.get("folder", "")
                try:
                    self._known_files[w["id"]] = set(os.listdir(folder)) if os.path.isdir(folder) else set()
                except Exception:
                    self._known_files[w["id"]] = set()
            elif w["kind"] in ("process_started", "process_stopped"):
                self._known_running[w["id"]] = self._is_process_running(w.get("process", ""))

    def add_folder_watch(self, folder: str, command: str) -> str:
        watch_id = str(int(time.time() * 1000))
        self.watches.append({"id": watch_id, "kind": "folder_new_file", "folder": folder,
                              "command": command, "enabled": True})
        try:
            self._known_files[watch_id] = set(os.listdir(folder)) if os.path.isdir(folder) else set()
        except Exception:
            self._known_files[watch_id] = set()
        self._save()
        return watch_id

    def add_process_watch(self, kind: str, process: str, command: str) -> str:
        watch_id = str(int(time.time() * 1000))
        self.watches.append({"id": watch_id, "kind": kind, "process": process,
                              "command": command, "enabled": True})
        self._known_running[watch_id] = self._is_process_running(process)
        self._save()
        return watch_id

    def remove(self, watch_id: str) -> bool:
        before = len(self.watches)
        self.watches = [w for w in self.watches if w["id"] != watch_id]
        self._save()
        return len(self.watches) < before

    def list_watches(self):
        return list(self.watches)

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
            for w in list(self.watches):
                if not w.get("enabled", True):
                    continue
                try:
                    if w["kind"] == "folder_new_file":
                        self._check_folder(w)
                    elif w["kind"] in ("process_started", "process_stopped"):
                        self._check_process(w)
                except Exception as e:
                    action_logger.log("event_watch_error", {"watch": w}, str(e), False)
            time.sleep(CHECK_EVERY)

    def _check_folder(self, w):
        folder = w["folder"]
        if not os.path.isdir(folder):
            return
        current = set(os.listdir(folder))
        new_files = current - self._known_files.get(w["id"], current)
        self._known_files[w["id"]] = current
        if new_files:
            self._fire(w, extra=f"naya: {', '.join(list(new_files)[:3])}")

    def _is_process_running(self, name: str) -> bool:
        if not name:
            return False
        try:
            import psutil
        except ImportError:
            return False
        for proc in psutil.process_iter(["name"]):
            if name.lower() in (proc.info["name"] or "").lower():
                return True
        return False

    def _check_process(self, w):
        running_now = self._is_process_running(w["process"])
        was_running = self._known_running.get(w["id"], running_now)
        self._known_running[w["id"]] = running_now
        if w["kind"] == "process_started" and running_now and not was_running:
            self._fire(w)
        elif w["kind"] == "process_stopped" and not running_now and was_running:
            self._fire(w)

    def _fire(self, w, extra: str = ""):
        try:
            result = self.executor_fn(w["command"])
            action_logger.log("event_triggered", {"watch": w, "extra": extra}, result or "(no output)", True)
        except Exception as e:
            action_logger.log("event_triggered", {"watch": w}, str(e), False)


class EventWatcherModule(BaseModule):
    name = "event_watcher"
    description = "Watches folders/processes and reacts automatically when something changes"

    def __init__(self, executor_fn):
        self._ready = False
        self._watcher = EventWatcher(executor_fn)

    def on_enable(self):
        self._ready = True
        self._watcher.start()
        print(f"     \u2705 Event Watcher ready — {len(self._watcher.watches)} saved watch(es) loaded")

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready:
            return False
        q = query.lower()
        return any(t in q for t in TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        q = query.lower().strip()

        if "watch dikhao" in q or "events dikhao" in q or "watch list" in q:
            return self._list()

        if "watch hatao" in q:
            m = re.search(r'(\d{6,})', q)
            if not m:
                return "PC Control: Kaunsa watch ID hatana hai? 'watch dikhao' se ID dekho."
            ok = self._watcher.remove(m.group(1))
            return f"PC Control: Watch {'hata diya' if ok else 'nahi mila'}. \u2705"

        if "naya file" in q or "file aaye" in q:
            quotes = re.findall(r'"([^"]+)"', query)
            command = quotes[-1] if quotes else ""
            if not command:
                return 'PC Control: Format — \'desktop mein naya file aaye to "screenshot lo" karo\''
            folder = self._extract_location(q)
            watch_id = self._watcher.add_folder_watch(folder, command)
            return f'PC Control: Ab {folder} watch ho raha hai — naya file aaye to "{command}" chalega \u2705 (id: {watch_id})'

        if "jab" in q.split() or q.startswith("jab"):
            kind, process, command = self._parse_process_trigger(query)
            if not kind or not process or not command:
                return ('PC Control: Format — \'jab "chrome" band ho to "notepad kholo" karo\' '
                        'ya \'jab "spotify" start ho to "..." karo\'')
            watch_id = self._watcher.add_process_watch(kind, process, command)
            trig = "start ho" if kind == "process_started" else "band ho"
            return f'PC Control: Ab watch ho raha hai — jab "{process}" {trig} to "{command}" chalega \u2705 (id: {watch_id})'

        return ""

    def _list(self) -> str:
        watches = self._watcher.list_watches()
        if not watches:
            return "PC Control: Koi event watch set nahi hai."
        lines = ["PC Control: Active event watches:"]
        for w in watches:
            if w["kind"] == "folder_new_file":
                desc = f"naya file in {w['folder']}"
            elif w["kind"] == "process_started":
                desc = f'"{w["process"]}" start hone par'
            else:
                desc = f'"{w["process"]}" band hone par'
            lines.append(f"  \U0001f440 [{w['id']}] {desc} \u2192 \"{w['command']}\"")
        return "\n".join(lines)

    def _parse_process_trigger(self, query: str):
        q = query.lower()
        is_start = any(w in q for w in ["start ho", "khule", "chalu ho"])
        is_stop = any(w in q for w in ["band ho", "close ho"])
        kind = "process_started" if is_start else ("process_stopped" if is_stop else None)
        if not kind:
            return None, None, None
        quotes = re.findall(r'"([^"]+)"', query)
        if len(quotes) >= 2:
            process, command = quotes[0], quotes[-1]
        elif len(quotes) == 1:
            command = quotes[0]
            m = re.search(r'jab\s+(\S+)', q)
            process = m.group(1) if m else ""
        else:
            return None, None, None
        return kind, process.strip(), command.strip()

    def _extract_location(self, q: str) -> str:
        home = os.path.expanduser("~")
        if "desktop" in q:   return os.path.join(home, "Desktop")
        if "documents" in q: return os.path.join(home, "Documents")
        if "downloads" in q: return os.path.join(home, "Downloads")
        if "pictures" in q:  return os.path.join(home, "Pictures")
        m = re.search(r'([A-Za-z]:\\[^\s"]+)', q)
        if m: return m.group(1)
        return os.path.join(home, "Desktop")
