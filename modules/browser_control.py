# ============================================================
#  ALTROS Module: Browser Control (tabs, nav, search, forms)
#  pip install playwright
#  then run once:  playwright install chromium
#
#  Uses a dedicated persistent Chromium profile (separate from
#  your everyday Chrome) so automation doesn't fight your normal
#  browsing session. Log into sites once inside it; it remembers.
# ============================================================

import os
import re
import atexit
import urllib.parse
from modules.base import BaseModule

try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_OK = True
except ImportError:
    _PLAYWRIGHT_OK = False

from core.action_logger import action_logger

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../modules/.. -> C:\ALTROS
PROFILE_DIR = os.path.join(_ROOT, "data", "browser_profile")

TAB_COUNT_RE = re.compile(r'(\d+)\s*tabs?\b', re.IGNORECASE)

SEARCH_PHRASES = ["browser search", "browser me search", "google karo", "google pe search", "dhundo"]

TRIGGERS = [
    "new tab", "tab kholo", "close tab", "tab band",
    "switch tab", "go to", "navigate", "website kholo",
    "fill form", "click button", "click link",
] + SEARCH_PHRASES


class BrowserControlModule(BaseModule):
    name = "browser_control"
    description = "Browser tabs, navigation, search, form-fill (Playwright)"

    def __init__(self):
        self._ready = False
        self._pw = None
        self._browser_ctx = None
        self._pages = []

    def on_enable(self):
        if not _PLAYWRIGHT_OK:
            print("     \u26a0\ufe0f playwright missing — browser_control disabled. 'pip install playwright' + 'playwright install chromium'")
            self._ready = False
            return
        os.makedirs(PROFILE_DIR, exist_ok=True)
        self._ready = True
        atexit.register(self._shutdown)
        print("     \u2705 Browser Control module ready")

    def _ensure_browser(self):
        if self._browser_ctx is not None:
            return
        self._pw = sync_playwright().start()
        self._browser_ctx = self._pw.chromium.launch_persistent_context(
            PROFILE_DIR, headless=False, viewport=None
        )
        self._pages = list(self._browser_ctx.pages) or [self._browser_ctx.new_page()]

    def _shutdown(self):
        try:
            if self._browser_ctx:
                self._browser_ctx.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready:
            return False
        q = query.lower()
        if TAB_COUNT_RE.search(q):
            return True
        return any(t in q for t in TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        q = query.lower().strip()
        m = TAB_COUNT_RE.search(q)
        if m:
            return self._open_multiple_tabs(query, int(m.group(1)))
        try:
            self._ensure_browser()
            page = self._pages[-1]

            if "new tab" in q or "tab kholo" in q:
                page = self._browser_ctx.new_page()
                self._pages.append(page)
                target = self._extract_url_or_search(query)
                if target:
                    self._goto(page, target)
                result = f"Naya tab khola{(' aur ' + target + ' load kiya') if target else ''}. \u2705"

            elif "close tab" in q or "tab band" in q:
                if len(self._pages) > 1:
                    page.close()
                    self._pages.pop()
                    result = "Tab band kiya. \u2705"
                else:
                    result = "Sirf ek tab khula hai, band nahi kar sakta."

            elif "switch tab" in q:
                m = re.search(r'(\d+)', q)
                idx = int(m.group(1)) - 1 if m else -1
                if 0 <= idx < len(self._pages):
                    self._pages[idx].bring_to_front()
                    result = f"Tab {idx+1} pe switch kiya. \u2705"
                else:
                    result = f"Sirf {len(self._pages)} tabs khule hain."

            elif any(w in q for w in ["go to", "navigate", "website kholo"]):
                target = self._extract_url_or_search(query)
                self._goto(page, target)
                result = f"'{target}' pe navigate kiya. \u2705"

            elif any(k in q for k in SEARCH_PHRASES):
                term = self._term_after(query, SEARCH_PHRASES)
                self._goto(page, term, force_search=True)
                result = f"'{term}' search kiya. \u2705"

            elif "fill form" in q:
                result = self._fill_form(page, query)

            elif "click button" in q or "click link" in q:
                text = self._extract_quoted(query)
                if not text:
                    return 'PC Control: Kis button/link pe click karu? "text" batao.'
                page.get_by_text(text, exact=False).first.click(timeout=5000)
                result = f"'{text}' pe click kiya. \u2705"

            else:
                return ""

            action_logger.log("browser_control", {"query": query}, result, True)
            return f"PC Control: {result}"

        except Exception as e:
            action_logger.log("browser_control", {"query": query}, str(e), False)
            return f"PC Control: \u274c Browser error — {e}"

    def _goto(self, page, target: str, force_search: bool = False):
        if not target:
            return
        looks_like_url = re.match(r'^https?://', target) or ("." in target and " " not in target)
        if looks_like_url and not force_search:
            url = target if target.startswith("http") else f"https://{target}"
        else:
            url = f"https://www.google.com/search?q={urllib.parse.quote(target)}"
        page.goto(url, timeout=15000)

    def _open_multiple_tabs(self, query: str, count: int) -> str:
        # real Playwright pages, not a ctrl+t/type-url/enter hotkey loop --
        # doesn't depend on window focus timing and can't type into the
        # wrong window if something steals focus mid-loop.
        if count < 1:
            return "PC Control: Kitne tabs? e.g. '5 tabs kholo'"
        if count > 20:
            return "PC Control: Max 20 tabs ek saath — zyada se browser slow ho sakta hai."
        try:
            self._ensure_browser()
            target = self._extract_url_or_search(query)
            opened = 0
            for _ in range(count):
                page = self._browser_ctx.new_page()
                self._pages.append(page)
                if target:
                    try:
                        self._goto(page, target)
                    except Exception:
                        pass
                opened += 1
            suffix = f" — '{target}'" if target else ""
            result = f"{opened} tabs khol diye{suffix}. \u2705"
            action_logger.log("browser_multi_tab", {"count": opened, "target": target}, result, True)
            return f"PC Control: {result}"
        except Exception as e:
            action_logger.log("browser_multi_tab", {"count": count}, str(e), False)
            return f"PC Control: \u274c Multi-tab error — {e}"

    def _fill_form(self, page, query: str) -> str:
        # format: fill form "field label" with "value" [, "field2" with "value2"]
        pairs = re.findall(r'"([^"]+)"\s+(?:with|me)\s+"([^"]+)"', query, re.IGNORECASE)
        if not pairs:
            return 'Format: fill form "field name" with "value"'
        filled = 0
        for label, value in pairs:
            try:
                page.get_by_label(label, exact=False).fill(value, timeout=4000)
                filled += 1
            except Exception:
                try:
                    page.get_by_placeholder(label, exact=False).fill(value, timeout=4000)
                    filled += 1
                except Exception:
                    continue
        return f"{filled}/{len(pairs)} fields fill kiye. \u2705" if filled else "Koi field match nahi hua."

    def _extract_url_or_search(self, query: str) -> str:
        q = query.lower()
        for kw in ["new tab", "tab kholo", "go to", "navigate", "website kholo"]:
            if kw in q:
                idx = q.index(kw) + len(kw)
                return query[idx:].strip(' :"')
        return self._extract_quoted(query)

    def _term_after(self, query: str, keywords: list) -> str:
        q = query.lower()
        for kw in keywords:
            if kw in q:
                idx = q.index(kw) + len(kw)
                return query[idx:].strip(' :"')
        return self._extract_quoted(query)

    def _extract_quoted(self, query: str) -> str:
        m = re.search(r'"([^"]+)"', query)
        return m.group(1) if m else ""
