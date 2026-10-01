# ============================================================
#  ALTROS Module: Window Control
#  pip install pygetwindow
# ============================================================

import re
from modules.base import BaseModule

try:
    import pygetwindow as gw
except ImportError:
    gw = None

from core.action_logger import action_logger

TRIGGERS = [
    "minimize", "maximize", "bada kar", "switch window", "switch to",
    "close window", "window band", "window close",
    "focus window", "bring to front", "list windows", "windows dikhao",
]


class WindowControlModule(BaseModule):
    name = "window_control"
    description = "Window minimize/maximize/switch/close/list"

    def __init__(self):
        self._ready = False

    def on_enable(self):
        self._ready = True
        print("     \u2705 Window Control module ready" if gw else "     \u26a0\ufe0f pygetwindow missing — window_control limited")

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready:
            return False
        q = query.lower()
        return any(t in q for t in TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        if gw is None:
            return "PC Control: 'pip install pygetwindow' karo window control ke liye."

        q = query.lower().strip()
        try:
            if "list windows" in q or "windows dikhao" in q:
                titles = [w.title for w in gw.getAllWindows() if w.title.strip()]
                if not titles:
                    return "PC Control: Koi open window nahi mila."
                lines = ["PC Control: Open windows:"] + [f"  \U0001fa9f {t}" for t in titles[:15]]
                return "\n".join(lines)

            name = self._extract_window_name(query)
            win = self._find_window(name) if name else gw.getActiveWindow()
            if not win:
                return f"PC Control: '{name or 'active'}' window nahi mila."

            if "minimize" in q:
                win.minimize()
                result = f"'{win.title}' minimize kiya. \u2705"
            elif "maximize" in q or "bada kar" in q:
                win.maximize()
                result = f"'{win.title}' maximize kiya. \u2705"
            elif "close" in q or "band" in q:
                result = self._close_window(win)
            elif any(w in q for w in ["switch", "focus", "bring to front"]):
                win.activate()
                result = f"'{win.title}' pe switch kiya. \u2705"
            else:
                return ""

            action_logger.log("window_control", {"query": query, "window": win.title}, result, True)
            return f"PC Control: {result}"

        except Exception as e:
            action_logger.log("window_control", {"query": query}, str(e), False)
            return f"PC Control: \u274c Window error — {e}"

    def _close_window(self, win) -> str:
        try:
            win.close()
            return f"'{win.title}' close kiya. \u2705"
        except Exception:
            return f"'{win.title}' close nahi ho paya — 'kill process' try karo (force-close, confirmation maangega)."

    def _extract_window_name(self, query: str) -> str:
        m = re.search(r'"([^"]+)"', query)
        if m:
            return m.group(1)
        low = query.lower()
        for kw in ["switch to", "close window", "minimize", "maximize", "focus window"]:
            if kw in low:
                idx = low.index(kw) + len(kw)
                return query[idx:].strip(' :"')
        return ""

    def _find_window(self, name: str):
        if not name:
            return None
        matches = gw.getWindowsWithTitle(name)
        return matches[0] if matches else None
