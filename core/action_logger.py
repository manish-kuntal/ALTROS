# ============================================================
#  ALTROS Core: Action Logger + Undo Stack
#  Every PC Control action gets logged here. Reversible actions
#  (rename, move, create) go on an undo stack so 'undo' can
#  reverse the last one.
# ============================================================

import os
import json
import shutil
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../core/.. -> C:\ALTROS
LOG_PATH = os.path.join(_ROOT, "data", "memory", "action_log.jsonl")
MAX_UNDO = 20


class ActionLogger:
    def __init__(self, log_path: str = LOG_PATH):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self._undo_stack = []

    def log(self, action: str, payload: dict, result: str, success: bool = True):
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "payload": payload,
            "result": str(result)[:300],
            "success": success,
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass  # logging must never crash the assistant

    def recent(self, n: int = 10):
        if not os.path.exists(self.log_path):
            return []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-n:]
            return [json.loads(l) for l in lines]
        except Exception:
            return []

    def push_undo(self, kind: str, data: dict):
        self._undo_stack.append({"kind": kind, "data": data, "ts": datetime.now().isoformat(timespec="seconds")})
        if len(self._undo_stack) > MAX_UNDO:
            self._undo_stack.pop(0)

    def undo_last(self) -> str:
        if not self._undo_stack:
            return "PC Control: Undo karne ke liye kuch nahi hai."
        item = self._undo_stack.pop()
        kind, data = item["kind"], item["data"]
        try:
            if kind == "rename":
                os.rename(data["to"], data["from"])
                return f"PC Control: Undo — '{os.path.basename(data['to'])}' wapas '{os.path.basename(data['from'])}' ho gaya. \u2705"
            if kind == "move":
                shutil.move(data["to"], data["from"])
                return f"PC Control: Undo — wapas {data['from']} pe move ho gaya. \u2705"
            if kind in ("create_file", "create_folder"):
                path = data["path"]
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.exists(path):
                    os.remove(path)
                return f"PC Control: Undo — '{os.path.basename(path)}' remove kar diya. \u2705"
            if kind == "delete":
                return (
                    "PC Control: Delete ka undo automatic nahi hota — "
                    f"par '{data.get('name', 'item')}' Recycle Bin mein hoga, "
                    "wahan se restore kar sakte ho."
                )
        except Exception as e:
            return f"PC Control: Undo fail ho gaya — {e}"
        return "PC Control: Ye action undo nahi ho sakta."


action_logger = ActionLogger()
