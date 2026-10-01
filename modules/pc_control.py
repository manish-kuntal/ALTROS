# ============================================================
#  ALTROS PC Control v4 — Advanced
#  Chrome search | Multi-tab | YouTube | Spotify | Adaptation
# ============================================================

import os
import re
import time
import json
import shutil
import subprocess
import urllib.parse
from datetime import datetime
from modules.base import BaseModule

USERNAME  = os.getenv("USERNAME", "manish kuntal")
DESKTOP   = f"C:\\Users\\{USERNAME}\\Desktop"
DOCS      = f"C:\\Users\\{USERNAME}\\Documents"
DOWNLOADS = f"C:\\Users\\{USERNAME}\\Downloads"
MUSIC     = f"C:\\Users\\{USERNAME}\\Music"
PICTURES  = f"C:\\Users\\{USERNAME}\\Pictures"

ADAPT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "memory", "pc_adapt.json"
)

BLOCKED = [
    "format c:", "del /f /s /q c:\\windows",
    "rd /s /q c:\\windows", "reg delete hklm\\sam",
]

APPS = {
    "chrome"        : "chrome",
    "google chrome" : "chrome",
    "brave"         : "brave",
    "edge"          : "msedge",
    "firefox"       : "firefox",
    "vs code"       : "code",
    "vscode"        : "code",
    "discord"       : "discord",
    "telegram"      : "telegram",
    "spotify"       : "spotify",
    "calculator"    : "calc",
    "notepad"       : "notepad",
    "paint"         : "mspaint",
    "explorer"      : "explorer",
    "file explorer" : "explorer",
    "task manager"  : "taskmgr",
    "settings"      : "ms-settings:",
    "cmd"           : "cmd",
    "powershell"    : "powershell",
    "word"          : "winword",
    "excel"         : "excel",
    "powerpoint"    : "powerpnt",
    "vlc"           : "vlc",
    "store"         : "ms-windows-store:",
    "photos"        : "ms-photos:",
}

WEBSITES = {
    "whatsapp"  : "https://web.whatsapp.com",
    "instagram" : "https://www.instagram.com",
    "facebook"  : "https://www.facebook.com",
    "twitter"   : "https://www.twitter.com",
    "github"    : "https://www.github.com",
    "gmail"     : "https://mail.google.com",
    "netflix"   : "https://www.netflix.com",
    "amazon"    : "https://www.amazon.in",
    "flipkart"  : "https://www.flipkart.com",
    "google"    : "https://www.google.com",
    "youtube"   : "https://www.youtube.com",
    "linkedin"  : "https://www.linkedin.com",
    "reddit"    : "https://www.reddit.com",
}

CONTROL_TRIGGERS = [
    "open", "kholo", "launch", "start", "chalu",
    "close", "band karo", "shutdown", "restart",
    "search", "dhundo", "google karo",
    "tab", "tabs",
    "volume", "mute", "screenshot",
    "create", "banao", "bana", "new",
    "delete", "hata", "remove", "mita",
    "copy", "move", "rename",
    "list", "dikhao", "files",
    "play", "bajao", "sunao", "song", "music",
    "youtube", "spotify", "netflix",
    "lock", "sleep", "minimize",
    "type", "likho", "press",
    "home screen", "desktop pe jao",
    "close window", "window band",
    "go back", "wapas jao",
    "refresh", "reload",
    "new tab", "naya tab",
    "fullscreen", "full screen",
    "zoom in", "zoom out",
    "select all", "paste karo",
    "task switch",
]

_pending_delete = {}


class PCControlModule(BaseModule):
    name = "pc_control"
    description = "Advanced PC control — apps, search, files, YouTube, Spotify"

    def __init__(self):
        self._ready = False
        self._adapt = self._load_adapt()

    def on_enable(self):
        self._ready = True
        print("     ✅ PC Control module ready")

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready:
            return False
        q = query.lower()
        return any(t in q for t in CONTROL_TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        q = query.lower().strip()

        for b in BLOCKED:
            if b in q:
                return "PC Control: Ye command blocked hai."

        self._track_command(query)

        # ── NEW FEATURES ─────────────────────────────────────

        # Home screen
        if any(w in q for w in ["home screen", "desktop pe jao", "show desktop"]):
            try:
                import pyautogui
                pyautogui.hotkey("win", "d")
                return "PC Control: Home screen. ✅"
            except Exception as e:
                return "PC Control: Error — " + str(e)

        # Close window
        if "close window" in q or "window band karo" in q:
            try:
                import pyautogui
                pyautogui.hotkey("alt", "f4")
                return "PC Control: Window band. ✅"
            except Exception as e:
                return "PC Control: Error — " + str(e)

        # Go back
        if any(w in q for w in ["go back", "wapas jao", "back karo", "peeche"]):
            try:
                import pyautogui
                pyautogui.hotkey("alt", "left")
                return "PC Control: Back. ✅"
            except Exception as e:
                return "PC Control: Error — " + str(e)

        # Refresh
        if any(w in q for w in ["refresh", "reload", "dobara load"]):
            try:
                import pyautogui
                pyautogui.press("f5")
                return "PC Control: Refresh. ✅"
            except Exception as e:
                return "PC Control: Error — " + str(e)

        # New tab
        if "new tab" in q or "naya tab" in q:
            try:
                import pyautogui
                pyautogui.hotkey("ctrl", "t")
                return "PC Control: Naya tab. ✅"
            except Exception as e:
                return "PC Control: Error — " + str(e)

        # Fullscreen
        if "fullscreen" in q or "full screen" in q or "pura screen" in q:
            try:
                import pyautogui
                pyautogui.press("f11")
                return "PC Control: Fullscreen toggle. ✅"
            except Exception as e:
                return "PC Control: Error — " + str(e)

        # Maximize
        if "maximize" in q or "bada kar window" in q:
            try:
                import pyautogui
                pyautogui.hotkey("win", "up")
                return "PC Control: Maximize. ✅"
            except Exception as e:
                return "PC Control: Error — " + str(e)

        # Zoom
        if "zoom in" in q:
            try:
                import pyautogui
                pyautogui.hotkey("ctrl", "+")
                return "PC Control: Zoom in. ✅"
            except Exception as e:
                return "PC Control: Error — " + str(e)

        if "zoom out" in q:
            try:
                import pyautogui
                pyautogui.hotkey("ctrl", "-")
                return "PC Control: Zoom out. ✅"
            except Exception as e:
                return "PC Control: Error — " + str(e)

        # Select all
        if "select all" in q or "sab select" in q:
            try:
                import pyautogui
                pyautogui.hotkey("ctrl", "a")
                return "PC Control: Select all. ✅"
            except Exception as e:
                return "PC Control: Error — " + str(e)

        # Paste
        if q.strip() in ["paste karo", "paste kar", "paste"]:
            try:
                import pyautogui
                pyautogui.hotkey("ctrl", "v")
                return "PC Control: Paste. ✅"
            except Exception as e:
                return "PC Control: Error — " + str(e)

        # Task switcher
        if "task switch" in q or "apps dikhao" in q:
            try:
                import pyautogui
                pyautogui.hotkey("alt", "tab")
                return "PC Control: Task switcher. ✅"
            except Exception as e:
                return "PC Control: Error — " + str(e)

        # ── END NEW FEATURES ──────────────────────────────────

        # Multi-step commands
        if (" aur " in q or " and " in q) and not "youtube" in q:
            return self._handle_multi_step(query)

        # YouTube
        if "youtube" in q:
            return self._youtube_action(query, q)

        # Spotify
        if "spotify" in q:
            return self._spotify_action(query, q)

        # Browser + search
        if any(b in q for b in ["chrome", "brave", "edge", "browser"]):
            if any(w in q for w in ["search", "dhundo", "google", "open"]):
                return self._browser_with_search(query, q)

        # Multi tab
        tab_match = re.search(r'(\d+)\s*tab', q)
        if tab_match:
            return self._open_multiple_tabs(query, q, int(tab_match.group(1)))

        # Google search
        if any(w in q for w in ["google karo", "google pe search", "search karo"]):
            return self._google_search(query, q)

        # System
        if "shutdown cancel" in q or "shutdown rok" in q:
            subprocess.Popen("shutdown /a", shell=True)
            return "PC Control: Shutdown cancel. ✅"
        if "shutdown" in q:
            subprocess.Popen("shutdown /s /t 15", shell=True)
            return "PC Control: 15s mein shutdown. 'shutdown cancel' se rokna."
        if "restart" in q:
            subprocess.Popen("shutdown /r /t 15", shell=True)
            return "PC Control: 15s mein restart."
        if "lock" in q:
            subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "PC Control: Screen locked. ✅"
        if "sleep" in q:
            subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return "PC Control: Sleep mode. ✅"
        if "screenshot" in q:
            return self._take_screenshot()
        if "volume" in q or "mute" in q:
            return self._volume_control(q)
        if "minimize" in q:
            try:
                import pyautogui
                pyautogui.hotkey('win', 'd')
                return "PC Control: Windows minimize. ✅"
            except Exception as e:
                return f"PC Control: Error — {e}"

        # Type text
        if any(w in q for w in ["type karo", "likho", "write karo"]):
            return self._type_text(query)

        # File/folder ops
        if any(w in q for w in ["create", "banao", "bana", "new folder", "new file"]):
            return self._create_item(query, q)
        if any(w in q for w in ["delete", "hata", "remove", "mita"]):
            return self._delete_handler(query, q)
        if "haan" in q and _pending_delete.get("default"):
            item = _pending_delete.pop("default")
            return self._do_delete(item["path"], item["name"])
        if "copy" in q:
            return self._copy_item(query, q)
        if "move" in q or "shift" in q:
            return self._move_item(query, q)
        if "rename" in q or "naam badlo" in q:
            return self._rename_item(query, q)
        if any(w in q for w in ["list", "dikhao", "files dikho"]):
            return self._list_files(q)

        # App open
        if any(w in q for w in ["open", "kholo", "launch", "start", "chalu"]):
            return self._open_app(query, q)

        return ""

    # ════════════════════════════════════════════════════════
    # YOUTUBE
    # ════════════════════════════════════════════════════════

    def _youtube_action(self, query: str, q: str) -> str:
        search = self._extract_youtube_query(query)
        should_play = any(w in q for w in ["play", "bajao", "sunao", "chalao", "lagao"])

        if search:
            encoded = urllib.parse.quote(search)
            url = "https://www.youtube.com/results?search_query=" + encoded
            subprocess.Popen("start chrome " + url, shell=True)

            if should_play:
                import threading
                def auto_play():
                    try:
                        import pyautogui
                        time.sleep(4)
                        for _ in range(8):
                            pyautogui.press("tab")
                            time.sleep(0.15)
                        pyautogui.press("enter")
                    except Exception:
                        pass
                threading.Thread(target=auto_play, daemon=True).start()
                return "PC Control: YouTube pe '" + search + "' - pehla video play ho raha hai. ✅"

            return "PC Control: YouTube pe '" + search + "' search kar diya. ✅"
        else:
            subprocess.Popen("start https://www.youtube.com", shell=True)
            return "PC Control: YouTube khol diya. ✅"

    def _extract_youtube_query(self, text: str) -> str:
        q = text.strip()
        q = re.sub(r'^altros\s+', '', q, flags=re.I)

        # Pattern 1: "youtube pe QUERY bajao/search karo/dekho"
        m = re.search(
            r'youtube\s+(?:pe|par|mein|on|me)?\s+(.+?)\s+'
            r'(?:search\s*karo|search\s*kar|bajao|sunao|dekho|play\s*karo|'
            r'dekhao|chalao|lagao|find|dhundo|play)$',
            q, re.I
        )
        if m:
            return m.group(1).strip()

        # Pattern 2: "play/search QUERY on youtube"
        m = re.search(
            r'(?:play|search|bajao|find|dhundo)\s+(.+?)\s+'
            r'(?:on|pe|par|in|mein)?\s*youtube',
            q, re.I
        )
        if m:
            return m.group(1).strip()

        # Pattern 3: "youtube QUERY" — remove trailing action words
        m = re.search(
            r'youtube\s+(?:pe|par|mein|on|me)?\s*(?:search\s+)?(.+)',
            q, re.I
        )
        if m:
            result = m.group(1).strip()
            result = re.sub(
                r'\s+(?:search\s*karo|search\s*kar|bajao|sunao|dekho|'
                r'play|karo|kar|do|lagao|chalao|dikha|dikhao|song|songs)$',
                '', result, flags=re.I
            )
            result = result.strip()
            if result and len(result) > 1:
                return result

        return ""

    # ════════════════════════════════════════════════════════
    # SPOTIFY
    # ════════════════════════════════════════════════════════

    def _spotify_action(self, query: str, q: str) -> str:
        search = self._extract_spotify_query(query)
        if search:
            encoded = urllib.parse.quote(search)
            url = "https://open.spotify.com/search/" + encoded
            subprocess.Popen("start chrome " + url, shell=True)
            return "PC Control: Spotify pe '" + search + "' search kar diya. ✅"
        else:
            subprocess.Popen("start spotify", shell=True)
            return "PC Control: Spotify khol diya. ✅"

    def _extract_spotify_query(self, text: str) -> str:
        q = text.strip()
        q = re.sub(r'^altros\s+', '', q, flags=re.I)

        m = re.search(
            r'spotify\s+(?:pe|par|mein|on|me)?\s+(.+?)\s+'
            r'(?:bajao|sunao|play|search|karo|chalao|lagao)$',
            q, re.I
        )
        if m:
            return m.group(1).strip()

        m = re.search(
            r'spotify\s+(?:pe|par|mein|on|me)?\s*(?:search|play)?\s+(.+)',
            q, re.I
        )
        if m:
            result = re.sub(
                r'\s+(?:bajao|sunao|play|karo|kar|do)$',
                '', m.group(1), flags=re.I
            )
            return result.strip()

        return ""

    # ════════════════════════════════════════════════════════
    # BROWSER
    # ════════════════════════════════════════════════════════

    def _browser_with_search(self, query: str, q: str) -> str:
        browser = "chrome"
        if "brave" in q:  browser = "brave"
        elif "edge" in q: browser = "msedge"

        skip = ["chrome","brave","edge","browser","kholo","open",
                "search","karo","pe","mein","aur","and","kar"]
        search = self._remove_words(query, skip)

        if search:
            encoded = urllib.parse.quote(search)
            url = "https://www.google.com/search?q=" + encoded
            subprocess.Popen("start " + browser + " " + url, shell=True)
            return "PC Control: " + browser + " mein '" + search + "' search kar diya. ✅"
        else:
            subprocess.Popen("start " + browser, shell=True)
            return "PC Control: " + browser + " khol diya. ✅"

    def _google_search(self, query: str, q: str) -> str:
        skip = ["google","karo","pe","search","dhundo","find","altros"]
        search = self._remove_words(query, skip)
        if search:
            encoded = urllib.parse.quote(search)
            url = "https://www.google.com/search?q=" + encoded
            subprocess.Popen("start chrome " + url, shell=True)
            return "PC Control: Google pe '" + search + "' search kar diya. ✅"
        return "PC Control: Kya search karna hai?"

    def _open_multiple_tabs(self, query: str, q: str, count: int) -> str:
        if count > 50:
            return "PC Control: Max 50 tabs allow hain."

        url = "https://www.google.com"
        if "youtube" in q:  url = "https://www.youtube.com"
        elif "github" in q: url = "https://www.github.com"

        search = self._extract_youtube_query(query)
        if not search:
            skip = ["tab","tabs","kholo","open","chrome","brave",
                    str(count),"browser","aur","and","karo"]
            search = self._remove_words(query, skip)
        if search:
            encoded = urllib.parse.quote(search)
            url = "https://www.google.com/search?q=" + encoded

        subprocess.Popen("start chrome " + url, shell=True)
        time.sleep(1.5)

        try:
            import pyautogui
            for i in range(count - 1):
                pyautogui.hotkey('ctrl', 't')
                time.sleep(0.3)
                pyautogui.hotkey('ctrl', 'l')
                time.sleep(0.2)
                pyautogui.write(url, interval=0.02)
                pyautogui.press('enter')
                time.sleep(0.4)
            return "PC Control: " + str(count) + " tabs khol diye. ✅"
        except Exception as e:
            return "PC Control: Pehla tab khola. Pyautogui error — " + str(e)

    # ════════════════════════════════════════════════════════
    # SYSTEM
    # ════════════════════════════════════════════════════════

    def _take_screenshot(self) -> str:
        try:
            import pyautogui
            ts = datetime.now().strftime('%H%M%S')
            path = os.path.join(DESKTOP, "screenshot_" + ts + ".png")
            pyautogui.screenshot(path)
            return "PC Control: Screenshot liya — " + path + " ✅"
        except Exception as e:
            return "PC Control: Screenshot error — " + str(e)

    def _volume_control(self, q: str) -> str:
        try:
            import pyautogui
            level_match = re.search(r'volume\s+(\d+)', q)
            if level_match:
                target = int(level_match.group(1))
                for _ in range(50): pyautogui.press("volumedown")
                for _ in range(target // 2): pyautogui.press("volumeup")
                return "PC Control: Volume " + str(target) + "% set kiya. ✅"
            if "up" in q or "badha" in q or "zyada" in q:
                for _ in range(5): pyautogui.press("volumeup")
                return "PC Control: Volume badha diya. ✅"
            elif "down" in q or "kam" in q:
                for _ in range(5): pyautogui.press("volumedown")
                return "PC Control: Volume kam kar diya. ✅"
            elif "mute" in q:
                pyautogui.press("volumemute")
                return "PC Control: Mute toggle. ✅"
            elif "max" in q or "full" in q:
                for _ in range(50): pyautogui.press("volumeup")
                return "PC Control: Volume max. ✅"
        except Exception as e:
            return "PC Control: Volume error — " + str(e)
        return ""

    def _type_text(self, query: str) -> str:
        m = re.search(r'"([^"]+)"', query)
        if not m:
            return 'PC Control: Kya type karna hai? Quotes mein — type karo "Hello World"'
        try:
            import pyautogui
            time.sleep(0.5)
            pyautogui.write(m.group(1), interval=0.05)
            return "PC Control: Text type kar diya. ✅"
        except Exception as e:
            return "PC Control: Type error — " + str(e)

    # ════════════════════════════════════════════════════════
    # FILE / FOLDER
    # ════════════════════════════════════════════════════════

    def _create_item(self, query: str, q: str) -> str:
        is_file = "file" in q and "folder" not in q
        name = self._extract_quoted(query) or self._last_word(query, skip=[
            "create","banao","bana","new","folder","file","desktop",
            "documents","downloads","pe","mein","karo","do","ka","ki"
        ])
        location = self._get_location(q)
        if is_file:
            if '.' not in name:
                name = name + '.txt'
            path = os.path.join(location, name)
            try:
                open(path, 'w').close()
                return "PC Control: File '" + name + "' ban gayi — " + path + " ✅"
            except Exception as e:
                return "PC Control: File error — " + str(e)
        else:
            path = os.path.join(location, name)
            try:
                os.makedirs(path, exist_ok=True)
                return "PC Control: Folder '" + name + "' ban gaya — " + path + " ✅"
            except Exception as e:
                return "PC Control: Folder error — " + str(e)

    def _delete_handler(self, query: str, q: str) -> str:
        if any(w in q for w in ["haan", "yes", "han", "confirm"]):
            if "default" in _pending_delete:
                item = _pending_delete.pop("default")
                return self._do_delete(item["path"], item["name"])
            return "PC Control: Kya delete karna hai?"

        name = self._extract_quoted(query) or self._last_word(query, skip=[
            "delete","hata","remove","mita","do","karo","file","folder","please"
        ])
        path = self._find_item(q, name)

        if not path:
            return "PC Control: '" + name + "' nahi mila."

        _pending_delete["default"] = {"path": path, "name": name}
        itype = "Folder" if os.path.isdir(path) else "File"
        return (
            "PC Control: " + itype + " delete karna chahte ho?\n" +
            "  " + path + "\n" +
            "  Bolo: 'haan delete karo'"
        )

    def _do_delete(self, path: str, name: str) -> str:
        try:
            if not os.path.exists(path):
                return "PC Control: '" + name + "' exist nahi karta."
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return "PC Control: '" + name + "' delete ho gaya. ✅"
        except PermissionError:
            return "PC Control: Permission denied — Admin rights chahiye."
        except Exception as e:
            return "PC Control: Delete error — " + str(e)

    def _copy_item(self, query: str, q: str) -> str:
        name = self._extract_quoted(query)
        if not name:
            return 'PC Control: Kya copy karna hai? Naam quotes mein — copy "filename"'
        src  = self._find_item(q, name)
        dest = self._get_location(q)
        if not src:
            return "PC Control: '" + name + "' nahi mila."
        try:
            dp = os.path.join(dest, os.path.basename(src))
            if os.path.isdir(src):
                shutil.copytree(src, dp)
            else:
                shutil.copy2(src, dp)
            return "PC Control: '" + name + "' copy ho gaya. ✅"
        except Exception as e:
            return "PC Control: Copy error — " + str(e)

    def _move_item(self, query: str, q: str) -> str:
        name = self._extract_quoted(query)
        if not name:
            return 'PC Control: Kya move karna hai? Naam quotes mein.'
        src  = self._find_item(q, name)
        dest = self._get_location(q)
        if not src:
            return "PC Control: '" + name + "' nahi mila."
        try:
            shutil.move(src, os.path.join(dest, os.path.basename(src)))
            return "PC Control: '" + name + "' move ho gaya. ✅"
        except Exception as e:
            return "PC Control: Move error — " + str(e)

    def _rename_item(self, query: str, q: str) -> str:
        parts = re.findall(r'"([^"]+)"', query)
        if len(parts) < 2:
            return 'PC Control: Format — rename "purana" "naya"'
        old = self._find_item(q, parts[0])
        if not old:
            return "PC Control: '" + parts[0] + "' nahi mila."
        new = os.path.join(os.path.dirname(old), parts[1])
        try:
            os.rename(old, new)
            return "PC Control: '" + parts[0] + "' renamed to '" + parts[1] + "' ✅"
        except Exception as e:
            return "PC Control: Rename error — " + str(e)

    def _list_files(self, q: str) -> str:
        loc = self._get_location(q)
        try:
            items = os.listdir(loc)
            folders = sorted([i for i in items if os.path.isdir(os.path.join(loc, i))])
            files   = sorted([i for i in items if os.path.isfile(os.path.join(loc, i))])
            lines   = ["PC Control: '" + loc + "' (" + str(len(items)) + " items):"]
            for f in folders[:15]: lines.append("  Folder: " + f)
            for f in files[:15]:   lines.append("  File: " + f)
            if len(items) > 30:
                lines.append("  ... aur " + str(len(items)-30) + " items")
            return "\n".join(lines)
        except Exception as e:
            return "PC Control: List error — " + str(e)

    def _open_app(self, query: str, q: str) -> str:
        for site, url in WEBSITES.items():
            if site in q:
                subprocess.Popen("start chrome " + url, shell=True)
                return "PC Control: " + site.title() + " khol diya. ✅"

        for app_name in sorted(APPS.keys(), key=len, reverse=True):
            if app_name in q:
                cmd = APPS[app_name]
                if ":" in cmd:
                    subprocess.Popen("start " + cmd, shell=True)
                else:
                    subprocess.Popen("start " + cmd, shell=True)
                return "PC Control: " + app_name.title() + " khol diya. ✅"

        loc = self._get_location(q)
        if os.path.exists(loc):
            subprocess.Popen('explorer "' + loc + '"', shell=True)
            return "PC Control: '" + loc + "' khola. ✅"

        return ""

    def _handle_multi_step(self, query: str) -> str:
        results = []
        parts = re.split(r'\s+aur\s+|\s+and\s+|,\s*', query, flags=re.I)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            q = part.lower()
            if "youtube" in q:
                results.append(self._youtube_action(part, q))
            elif "spotify" in q:
                results.append(self._spotify_action(part, q))
            elif re.search(r'\d+\s*tab', q):
                m = re.search(r'(\d+)', q)
                if m:
                    results.append(self._open_multiple_tabs(part, q, int(m.group(1))))
            elif "screenshot" in q:
                results.append(self._take_screenshot())
            elif "volume" in q or "mute" in q:
                results.append(self._volume_control(q))
            elif any(w in q for w in ["open","kholo","launch"]):
                results.append(self._open_app(part, q))
            time.sleep(0.4)
        return "\n".join(results) if results else "PC Control: Command samajh nahi aaya."

    # ════════════════════════════════════════════════════════
    # ADAPTATION
    # ════════════════════════════════════════════════════════

    def _track_command(self, query: str):
        key = query.lower().strip()[:50]
        self._adapt["commands"][key] = self._adapt["commands"].get(key, 0) + 1
        self._save_adapt()

    def _load_adapt(self) -> dict:
        if os.path.exists(ADAPT_FILE):
            try:
                with open(ADAPT_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"commands": {}, "shortcuts": {}}

    def _save_adapt(self):
        try:
            os.makedirs(os.path.dirname(ADAPT_FILE), exist_ok=True)
            with open(ADAPT_FILE, 'w') as f:
                json.dump(self._adapt, f, indent=2)
        except Exception:
            pass

    # ════════════════════════════════════════════════════════
    # HELPERS
    # ════════════════════════════════════════════════════════

    def _remove_words(self, text: str, skip: list) -> str:
        q = text.lower()
        for w in skip:
            q = re.sub(r'\b' + re.escape(w) + r'\b', ' ', q)
        return ' '.join(q.split()).strip()

    def _extract_quoted(self, query: str) -> str:
        m = re.search(r'"([^"]+)"', query)
        return m.group(1) if m else ""

    def _last_word(self, query: str, skip: list = []) -> str:
        words = [w for w in query.split() if w.lower() not in skip and len(w) > 1]
        return words[-1] if words else "new_item"

    def _get_location(self, q: str) -> str:
        if "desktop"   in q: return DESKTOP
        if "documents" in q: return DOCS
        if "downloads" in q: return DOWNLOADS
        if "music"     in q: return MUSIC
        if "pictures"  in q: return PICTURES
        if "d drive"   in q: return "D:\\"
        if "c drive"   in q: return "C:\\"
        m = re.search(r'([A-Za-z]:\\[^\s"]+)', q)
        if m: return m.group(1)
        return DESKTOP

    def _find_item(self, q: str, name: str) -> str:
        loc = self._get_location(q)
        for base in [loc, DESKTOP, DOCS, DOWNLOADS, MUSIC, PICTURES]:
            p = os.path.join(base, name)
            if os.path.exists(p):
                return p
        if os.path.exists(name):
            return name
        return ""