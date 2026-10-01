# ============================================================
#  ALTROS Module: Mouse + Keyboard Control
#  pip install pyautogui
# ============================================================

import re
from modules.base import BaseModule

try:
    import pyautogui
    pyautogui.FAILSAFE = True   # slam mouse to a screen corner to abort mid-action
    pyautogui.PAUSE = 0.05
except ImportError:
    pyautogui = None

from core.action_logger import action_logger

TRIGGERS = [
    "double click", "double-click", "right click", "right-click", "click",
    "mouse move", "cursor move", "drag",
    "type ", "likho", "press ", "dabao", "hotkey", "shortcut",
    "scroll",
]

NAMED_SHORTCUTS = {
    "copy": ["ctrl", "c"], "paste": ["ctrl", "v"], "cut": ["ctrl", "x"],
    "undo": ["ctrl", "z"], "save": ["ctrl", "s"], "select all": ["ctrl", "a"],
    "task manager": ["ctrl", "shift", "esc"], "alt tab": ["alt", "tab"],
    "new tab": ["ctrl", "t"], "close tab": ["ctrl", "w"], "refresh": ["f5"],
}

# Direct phrases -- no "press"/"hotkey" prefix needed, e.g. just "go back"
# or "select all" on their own. Deliberately excludes anything another
# module already owns more precisely: window_control.py handles
# "close window"/"maximize" via the actual window object, browser_control.py
# handles "new tab"/"close tab" via real Playwright pages, and
# system_control.py handles "paste" -- those stay there, not duplicated here.
QUICK_ACTIONS = {
    "home screen":  (["win", "d"], "Home screen"),
    "show desktop": (["win", "d"], "Home screen"),
    "go back":      (["alt", "left"], "Back gaya"),
    "wapas jao":    (["alt", "left"], "Back gaya"),
    "refresh":      (["f5"], "Refresh"),
    "reload":       (["f5"], "Refresh"),
    "fullscreen":   (["f11"], "Fullscreen toggle"),
    "full screen":  (["f11"], "Fullscreen toggle"),
    "zoom in":      (["ctrl", "+"], "Zoom in"),
    "zoom out":     (["ctrl", "-"], "Zoom out"),
    "select all":   (["ctrl", "a"], "Select all"),
    "task switch":  (["alt", "tab"], "Task switch"),
    "apps dikhao":  (["alt", "tab"], "Task switch"),
}


class MouseKeyboardModule(BaseModule):
    name = "mouse_keyboard"
    description = "Mouse move/click/drag/scroll + keyboard type/shortcuts"

    def __init__(self):
        self._ready = False

    def on_enable(self):
        self._ready = True
        print("     \u2705 Mouse/Keyboard module ready" if pyautogui else "     \u26a0\ufe0f pyautogui missing — mouse_keyboard limited")

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready:
            return False
        q = query.lower()
        if any(phrase in q for phrase in QUICK_ACTIONS):
            return True
        return any(t in q for t in TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        if pyautogui is None:
            return "PC Control: 'pip install pyautogui' karo."

        q = query.lower().strip()

        for phrase, (keys, label) in QUICK_ACTIONS.items():
            if phrase in q:
                try:
                    pyautogui.hotkey(*keys)
                    action_logger.log("quick_action", {"action": phrase}, label, True)
                    return f"PC Control: {label}. \u2705"
                except Exception as e:
                    action_logger.log("quick_action", {"action": phrase}, str(e), False)
                    return f"PC Control: \u274c {label} error — {e}"

        coords = re.search(r'(\d+)\s*[, ]\s*(\d+)', q)
        x, y = (int(coords.group(1)), int(coords.group(2))) if coords else (None, None)

        try:
            if "double click" in q or "double-click" in q:
                pyautogui.doubleClick(x, y) if x is not None else pyautogui.doubleClick()
                result = "Double click kiya. \u2705"
            elif "right click" in q or "right-click" in q:
                pyautogui.rightClick(x, y) if x is not None else pyautogui.rightClick()
                result = "Right click kiya. \u2705"
            elif "click" in q:
                pyautogui.click(x, y) if x is not None else pyautogui.click()
                result = "Click kiya. \u2705"
            elif "drag" in q and x is not None:
                pyautogui.dragTo(x, y, duration=0.3)
                result = f"Drag kiya ({x},{y}) tak. \u2705"
            elif "mouse move" in q or "cursor move" in q:
                if x is None:
                    return "PC Control: Coordinates batao — 'mouse move 500 300'"
                pyautogui.moveTo(x, y, duration=0.2)
                result = f"Mouse ({x},{y}) pe move kiya. \u2705"
            elif "scroll" in q:
                pyautogui.scroll(-500 if "down" in q else 500)
                result = "Scroll kiya. \u2705"
            elif "type" in q or "likho" in q:
                text = self._extract_text(query)
                if not text:
                    return 'PC Control: Kya type karna hai? "text" quotes mein batao.'
                pyautogui.typewrite(text, interval=0.02)
                result = f"Type kiya: '{text}' \u2705"
            elif any(w in q for w in ["hotkey", "shortcut", "press", "dabao"]):
                keys = self._extract_keys(q)
                if not keys:
                    return "PC Control: Konsi key/shortcut? e.g. 'press ctrl+c'"
                pyautogui.hotkey(*keys)
                result = f"Shortcut '{'+'.join(keys)}' dabaya. \u2705"
            else:
                return ""

            action_logger.log("mouse_keyboard", {"query": query}, result, True)
            return f"PC Control: {result}"

        except Exception as e:
            action_logger.log("mouse_keyboard", {"query": query}, str(e), False)
            return f"PC Control: \u274c Mouse/Keyboard error — {e}"

    def _extract_text(self, query: str) -> str:
        m = re.search(r'"([^"]+)"', query)
        if m:
            return m.group(1)
        low = query.lower()
        for kw in ["type", "likho"]:
            if kw in low:
                idx = low.index(kw) + len(kw)
                return query[idx:].strip(' :"')
        return ""

    def _extract_keys(self, q: str) -> list:
        m = re.search(r'([a-z0-9]+(?:\s*\+\s*[a-z0-9]+)+)', q)
        if m:
            return [k.strip() for k in m.group(1).split('+')]
        for phrase, keys in NAMED_SHORTCUTS.items():
            if phrase in q:
                return keys
        return []
