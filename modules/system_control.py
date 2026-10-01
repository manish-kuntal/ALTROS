# ============================================================
#  ALTROS Module: System Control
#  Volume, brightness, Wi-Fi, Bluetooth, clipboard, media keys,
#  and search (files/folders/apps/settings).
#  pip install pycaw comtypes screen-brightness-control pyperclip psutil
# ============================================================

import os
import re
import glob
import subprocess
from modules.base import BaseModule

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    import screen_brightness_control as sbc
except ImportError:
    sbc = None

try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    _PYCAW_OK = True
except ImportError:
    _PYCAW_OK = False

from core.action_logger import action_logger
from core.permissions import permission_manager

DESKTOP   = os.path.join(os.path.expanduser("~"), "Desktop")
DOCUMENTS = os.path.join(os.path.expanduser("~"), "Documents")
DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")
SESSION = "default"

SETTINGS_MAP = {
    "wifi": "ms-settings:network-wifi", "wi-fi": "ms-settings:network-wifi",
    "bluetooth": "ms-settings:bluetooth", "display": "ms-settings:display",
    "sound": "ms-settings:sound", "battery": "ms-settings:batterysaver",
    "storage": "ms-settings:storagesense", "update": "ms-settings:windowsupdate",
    "apps": "ms-settings:appsfeatures", "privacy": "ms-settings:privacy",
    "accounts": "ms-settings:yourinfo",
}

TRIGGERS = [
    "set volume", "brightness", "wifi", "wi-fi", "bluetooth",
    "clipboard", "copy to clipboard", "paste",
    "search settings", "settings dhundo",
    "search app", "app dhundo", "find app",
    "search file", "file dhundo", "find file",
    "kill process", "process band", "force close",
    "media play", "pause music", "play music", "resume music",
    "next track", "next song", "previous track", "pichla gaana",
]


class SystemControlModule(BaseModule):
    name = "system_control"
    description = "Volume/brightness/wifi/bluetooth/clipboard/media/search/kill-process"

    def __init__(self):
        self._ready = False

    def on_enable(self):
        self._ready = True
        print("     \u2705 System Control module ready")

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready:
            return False
        q = query.lower()
        return any(t in q for t in TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        q = query.lower().strip()
        try:
            if "set volume" in q:
                return self._set_volume(q)
            if "brightness" in q:
                return self._brightness(q)
            if "wifi" in q or "wi-fi" in q:
                return self._wifi(q)
            if "bluetooth" in q:
                subprocess.Popen("start ms-settings:bluetooth", shell=True)
                return ("PC Control: Bluetooth settings khol diye — Python se seedha "
                        "reliably on/off nahi hota Windows pe, yahan se toggle karo. \U0001f535")
            if "clipboard" in q:
                return self._clipboard(query)
            if "paste" in q:
                return self._paste()
            if any(w in q for w in ["media play", "pause music", "play music", "resume music"]):
                return self._media("playpause", "Media play/pause toggle. \U0001f3b5")
            if "next track" in q or "next song" in q:
                return self._media("nexttrack", "Next track. \u23ed\ufe0f")
            if "previous track" in q or "pichla gaana" in q:
                return self._media("prevtrack", "Previous track. \u23ee\ufe0f")
            if "search settings" in q or "settings dhundo" in q:
                return self._search_settings(query)
            if any(w in q for w in ["search app", "app dhundo", "find app"]):
                return self._search_apps(query)
            if any(w in q for w in ["search file", "file dhundo", "find file"]):
                return self._search_files(query)
            if any(w in q for w in ["kill process", "process band", "force close"]):
                return self._request_kill(query)
        except Exception as e:
            action_logger.log("system_control", {"query": query}, str(e), False)
            return f"PC Control: \u274c Error — {e}"
        return ""

    def _set_volume(self, q: str) -> str:
        m = re.search(r'(\d{1,3})', q)
        if not m:
            return "PC Control: Kitna % volume? e.g. 'set volume 50'"
        target = max(0, min(100, int(m.group(1))))

        if _PYCAW_OK:
            level = target / 100.0
            speakers = AudioUtilities.GetSpeakers()
            interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level, None)
            result = f"Volume {target}% set kiya. \U0001f50a"
        elif pyautogui is not None:
            # approximate fallback when pycaw isn't installed: mute all the
            # way down then step back up -- each press is roughly 2%, so
            # this lands NEAR the target, not exactly on it like pycaw does.
            for _ in range(50): pyautogui.press("volumedown")
            for _ in range(target // 2): pyautogui.press("volumeup")
            result = f"Volume ~{target}% set kiya (approx — 'pip install pycaw comtypes' se exact hoga). \U0001f50a"
        else:
            return "PC Control: 'pip install pyautogui' ya 'pip install pycaw comtypes' karo."

        action_logger.log("set_volume", {"level": target}, result, True)
        return f"PC Control: {result}"

    def _brightness(self, q: str) -> str:
        if sbc is None:
            return "PC Control: 'pip install screen-brightness-control' karo."
        m = re.search(r'(\d{1,3})', q)
        if m:
            level = max(0, min(100, int(m.group(1))))
            sbc.set_brightness(level)
            result = f"Brightness {level}% set ki. \u2600\ufe0f"
        elif "up" in q or "badha" in q:
            cur = sbc.get_brightness()[0]
            sbc.set_brightness(min(100, cur + 15))
            result = "Brightness badha di. \u2600\ufe0f"
        elif "down" in q or "kam" in q:
            cur = sbc.get_brightness()[0]
            sbc.set_brightness(max(0, cur - 15))
            result = "Brightness kam kar di. \U0001f319"
        else:
            return "PC Control: Kitni brightness? e.g. 'brightness 70'"
        action_logger.log("brightness", {"query": q}, result, True)
        return f"PC Control: {result}"

    def _wifi(self, q: str) -> str:
        if "off" in q or "band" in q or "disable" in q:
            cmd, action = 'netsh interface set interface "Wi-Fi" admin=disable', "disable"
        elif "on" in q or "chalu" in q or "enable" in q:
            cmd, action = 'netsh interface set interface "Wi-Fi" admin=enable', "enable"
        else:
            subprocess.Popen("start ms-settings:network-wifi", shell=True)
            return "PC Control: Wi-Fi settings khol diye. \U0001f4f6"
        try:
            subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            result = f"Wi-Fi {action}d. \U0001f4f6 (admin terminal chahiye ho sakta hai)"
            action_logger.log("wifi", {"action": action}, result, True)
            return f"PC Control: {result}"
        except Exception as e:
            return f"PC Control: Wi-Fi error — {e}. CMD ko 'Run as Administrator' se chalao."

    def _clipboard(self, raw_query: str):
        if pyperclip is None:
            return "PC Control: 'pip install pyperclip' karo."
        m = re.search(r'"([^"]+)"', raw_query)
        if m:
            pyperclip.copy(m.group(1))
            return f"PC Control: Clipboard mein copy kiya: '{m.group(1)}' \u2705"
        current = pyperclip.paste()
        return f"PC Control: Clipboard mein abhi hai: '{current[:200]}'"

    def _paste(self) -> str:
        if pyautogui is None:
            return "PC Control: 'pip install pyautogui' karo."
        pyautogui.hotkey("ctrl", "v")
        return "PC Control: Paste kar diya. \u2705"

    def _media(self, key: str, label: str) -> str:
        if pyautogui is None:
            return "PC Control: 'pip install pyautogui' karo."
        pyautogui.press(key)
        action_logger.log("media_key", {"key": key}, label, True)
        return f"PC Control: {label}"

    def _search_settings(self, query: str) -> str:
        term = self._term_after(query, ["search settings", "settings dhundo"])
        for key, uri in SETTINGS_MAP.items():
            if key in term.lower():
                subprocess.Popen(f"start {uri}", shell=True)
                return f"PC Control: '{key}' settings khol diye. \u2699\ufe0f"
        return (f"PC Control: '{term}' settings nahi mile. Try: wifi, bluetooth, display, "
                "sound, battery, storage, update, apps, privacy, accounts.")

    def _search_apps(self, query: str) -> str:
        term = self._term_after(query, ["search app", "app dhundo", "find app"]).lower()
        if not term:
            return "PC Control: Konsi app dhundhu?"
        bases = [
            os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"),
                         "Microsoft\\Windows\\Start Menu\\Programs"),
            os.path.join(os.environ.get("APPDATA", ""),
                         "Microsoft\\Windows\\Start Menu\\Programs"),
        ]
        found = []
        for base in bases:
            if not os.path.isdir(base):
                continue
            for path in glob.glob(os.path.join(base, "**", "*.lnk"), recursive=True):
                if term in os.path.basename(path).lower():
                    found.append(os.path.splitext(os.path.basename(path))[0])
        if not found:
            return f"PC Control: '{term}' naam ki koi installed app nahi mili."
        lines = [f"PC Control: '{term}' se milti apps:"] + [f"  \U0001f680 {a}" for a in found[:10]]
        return "\n".join(lines)

    def _search_files(self, query: str) -> str:
        term = self._term_after(query, ["search file", "file dhundo", "find file"])
        if not term:
            return "PC Control: Konsi file/folder dhundhu?"
        found = []
        for root in (DESKTOP, DOCUMENTS, DOWNLOADS):
            if not os.path.isdir(root):
                continue
            for dirpath, dirnames, files in os.walk(root):
                for d in dirnames:
                    if term.lower() in d.lower():
                        found.append(f"{os.path.join(dirpath, d)}  (folder)")
                for f in files:
                    if term.lower() in f.lower():
                        found.append(os.path.join(dirpath, f))
                if len(found) >= 15:
                    break
        if not found:
            return f"PC Control: '{term}' naam ka kuch nahi mila (Desktop/Documents/Downloads mein dekha)."
        lines = [f"PC Control: '{term}' se milta:"] + [f"  \U0001f4c4 {p}" for p in found[:15]]
        return "\n".join(lines)

    def _request_kill(self, query: str) -> str:
        term = self._term_after(query, ["kill process", "process band", "force close"])
        if not term:
            return "PC Control: Konsa process band karna hai?"
        return permission_manager.request_confirmation(
            SESSION, "kill_process", {"name": term}, f"'{term}' process force-close karu"
        )

    def kill_process(self, name: str) -> str:
        """Actually kills the process. Called once a pending confirmation is accepted."""
        try:
            import psutil
        except ImportError:
            return "PC Control: 'pip install psutil' karo process control ke liye."
        killed = 0
        for proc in psutil.process_iter(["name"]):
            if name.lower() in (proc.info["name"] or "").lower():
                try:
                    proc.terminate()
                    killed += 1
                except Exception:
                    pass
        result = f"'{name}' — {killed} process band kiye. \u2705" if killed else f"'{name}' naam ka koi process nahi mila."
        action_logger.log("kill_process", {"name": name}, result, killed > 0)
        return f"PC Control: {result}"

    def _term_after(self, query: str, keywords: list) -> str:
        m = re.search(r'"([^"]+)"', query)
        if m:
            return m.group(1)
        low = query.lower()
        for kw in keywords:
            if kw in low:
                idx = low.index(kw) + len(kw)
                return query[idx:].strip(' :"')
        return ""
