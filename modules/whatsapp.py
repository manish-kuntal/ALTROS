# ============================================================
#  ALTROS Module: WhatsApp Integration v2
#  Talks to whatsapp_bridge.js on localhost:8001.
#
#  Fixes the core bug in v1: message text no longer needs to be
#  in quotes, and contact names are resolved without needing
#  "ko"/"se" specifically -- "keshav pe msg karo kaha ho" works.
#
#  New: read messages from a chat, AI summaries via your local
#  Ollama (no new dependency -- you already run it for brain.py),
#  and a local alias file for contacts that don't match cleanly.
# ============================================================

import os
import re
import json
import time
import requests
from modules.base import BaseModule
from core.permissions import permission_manager
from core.action_logger import action_logger

BRIDGE_URL = "http://localhost:8001"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3"

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../modules/.. -> C:\ALTROS
ALIASES_PATH = os.path.join(_ROOT, "data", "memory", "whatsapp_aliases.json")
CONTACTS_CACHE_PATH = os.path.join(_ROOT, "data", "memory", "whatsapp_contacts_cache.json")
CONTACTS_CACHE_TTL = 3600  # re-fetch contacts from the bridge at most hourly
SESSION = "whatsapp"  # separate from pc_control's "default" -- a pending
                       # WhatsApp confirmation must never clobber, or be
                       # clobbered by, a pending PC Control one

CONNECTOR_WORDS = ["ke liye", "ke", "pe", "ko", "se"]

SAVE_VERBS = ["ka number save karo", "ka number add karo", "number save karo", "number add karo"]
SUMMARY_VERBS = ["ki summary do", "ka summary do", "summary do", "summary batao", "summarize kar"]
READ_VERBS = ["messages padho", "message padho", "padh ke suna", "padh ke batao",
              "chat dikhao", "messages dikhao", "padho"]
SEND_VERBS = ["message bhej do", "msg bhej do", "message bhejo", "msg bhejo",
              "message karo", "msg karo", "message kar", "msg kar",
              "bata do", "bata de", "send karo", "send kar",
              "bhej do", "bhejo", "bolo", "likho"]

WA_TRIGGERS = [
    "whatsapp", "msg kar", "message kar", "bhej do", "send kar",
    "bata do", "bata de", "bolo", "likho", "forward", "reply kar",
    "file bhej", "photo bhej", "contact", "chat", "padho", "padh ke",
    "summary", "status", "number save", "number add",
]


class WhatsAppModule(BaseModule):
    name = "whatsapp"
    description = "WhatsApp -- send/read messages by contact name, AI summaries, contacts"

    def __init__(self):
        self._ready = False
        self._pending_messages = []

    def on_enable(self):
        try:
            r = requests.get(f"{BRIDGE_URL}/status", timeout=3)
            self._ready = (r.status_code == 200)
        except Exception:
            self._ready = False
        print("     \u2705 WhatsApp module ready" if self._ready else
              "     \u26a0\ufe0f WhatsApp bridge nahi mila -- 'cd whatsapp && node whatsapp_bridge.js' chalao")

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready:
            return False
        if permission_manager.has_pending(SESSION):
            return True
        q = query.lower()
        return any(t in q for t in WA_TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        q = query.lower()

        if permission_manager.has_pending(SESSION):
            reply = permission_manager.check_confirmation_reply(SESSION, query)
            if reply == "CANCELLED":
                return "WhatsApp: Cancel kar diya. \u2705"
            if reply is not None:
                return self._execute_confirmed(reply[0], reply[1])

        if any(v in q for v in SAVE_VERBS):
            return self._handle_save_alias(query)

        if any(v in q for v in SUMMARY_VERBS):
            return self._handle_summary(query)

        if "status" in q and any(w in q for w in ["kya lagaya", "dekho", "batao", "kisne", "check"]):
            return self._handle_status()

        if any(v in q for v in READ_VERBS):
            return self._handle_read(query)

        if any(v in q for v in SEND_VERBS):
            return self._handle_send(query)

        if any(w in q for w in ["file bhej", "photo bhej", "send file"]):
            return self._handle_send_file(query)

        if "contact" in q:
            return self._get_contacts_display()

        return ""

    # ── SEND ──────────────────────────────────────────────────
    def _handle_send(self, query: str) -> str:
        name, direct_number = self._extract_target(query, SEND_VERBS)
        message = self._extract_message(query, SEND_VERBS)

        number, display = self._resolve(name, direct_number)
        if number == "AMBIGUOUS":
            opts = ", ".join(f"{c['name']} ({c['number']})" for c in display)
            return f"WhatsApp: '{name}' jaisi kai contacts hain -- {opts}. Poora number de do."
        if not number:
            if name:
                return (f"WhatsApp: '{name}' contacts mein nahi mila. Number se try karo, "
                        f"ya '{name} ka number save karo <number>' bolke ek baar save kar do.")
            return "WhatsApp: Kis ko message karna hai?"
        if not message:
            return f"WhatsApp: {display} ko kya bolu?"

        wa_id = self._to_wa_id(number)
        return permission_manager.request_confirmation(
            SESSION, "send_whatsapp_message",
            {"wa_id": wa_id, "message": message, "display": display},
            f'{display} ko bhejun -- "{message}"', label="WhatsApp"
        )

    def _execute_confirmed(self, action_type: str, payload: dict) -> str:
        if action_type == "send_whatsapp_message":
            return self._send_message(payload["wa_id"], payload["message"], payload["display"])
        if action_type == "send_whatsapp_file":
            return self._send_file(payload["wa_id"], payload["filepath"], payload["caption"], payload["display"])
        return "WhatsApp: Confirm mila, par action pehchana nahi. \u2753"

    def _send_message(self, wa_id: str, message: str, display: str) -> str:
        try:
            r = requests.post(f"{BRIDGE_URL}/send", json={"number": wa_id, "message": message}, timeout=15)
            if r.status_code == 200:
                action_logger.log("whatsapp_send", {"to": display, "message": message}, "sent", True)
                return f"WhatsApp: {display} ko bhej diya \u2705\n\"{message}\""
            action_logger.log("whatsapp_send", {"to": display, "message": message}, r.text, False)
            return f"WhatsApp: Send error -- {r.text}"
        except Exception as e:
            action_logger.log("whatsapp_send", {"to": display, "message": message}, str(e), False)
            return f"WhatsApp: Bridge se connect nahi ho paya -- {e}"

    # ── SEND FILE ─────────────────────────────────────────────
    def _handle_send_file(self, query: str) -> str:
        name, direct_number = self._extract_target(query, ["file bhej", "photo bhej", "send file"])
        number, display = self._resolve(name, direct_number)
        if number == "AMBIGUOUS":
            opts = ", ".join(f"{c['name']} ({c['number']})" for c in display)
            return f"WhatsApp: '{name}' jaisi kai contacts hain -- {opts}."
        if not number:
            return "WhatsApp: Kis ko file bhejni hai?"

        path_match = re.search(r'[A-Za-z]:\\[^\s"]+', query)
        filepath = path_match.group() if path_match else None
        if not filepath:
            return 'WhatsApp: Kaunsi file? Path batao, e.g. C:\\Users\\...\\photo.jpg'

        caption_match = re.search(r'"([^"]+)"', query)
        caption = caption_match.group(1) if caption_match else ""

        wa_id = self._to_wa_id(number)
        return permission_manager.request_confirmation(
            SESSION, "send_whatsapp_file",
            {"wa_id": wa_id, "filepath": filepath, "caption": caption, "display": display},
            f'{display} ko file bhejun -- {filepath}', label="WhatsApp"
        )

    def _send_file(self, wa_id: str, filepath: str, caption: str, display: str) -> str:
        try:
            r = requests.post(f"{BRIDGE_URL}/send-file",
                               json={"number": wa_id, "filepath": filepath, "caption": caption},
                               timeout=30)
            if r.status_code == 200:
                action_logger.log("whatsapp_send_file", {"to": display, "path": filepath}, "sent", True)
                return f"WhatsApp: File {display} ko bhej di \u2705"
            action_logger.log("whatsapp_send_file", {"to": display, "path": filepath}, r.text, False)
            return f"WhatsApp: File error -- {r.text}"
        except Exception as e:
            action_logger.log("whatsapp_send_file", {"to": display, "path": filepath}, str(e), False)
            return f"WhatsApp: Error -- {e}"

    # ── READ ──────────────────────────────────────────────────
    def _handle_read(self, query: str) -> str:
        name, direct_number = self._extract_target(query, READ_VERBS)
        number, display = self._resolve(name, direct_number)
        if number == "AMBIGUOUS":
            opts = ", ".join(f"{c['name']} ({c['number']})" for c in display)
            return f"WhatsApp: '{name}' jaisi kai contacts hain -- {opts}."
        if not number:
            return f"WhatsApp: '{name or 'kiske'}' messages? Naam ya number saaf batao."

        msgs = self._fetch_messages(number, limit=10)
        if msgs is None:
            return "WhatsApp: Messages fetch nahi ho paye -- bridge chal raha hai check karo."
        if not msgs:
            return f"WhatsApp: {display} ke saath koi recent messages nahi mile."

        lines = [f"WhatsApp: {display} ke last {len(msgs)} messages:"]
        for m in msgs:
            who = "Aap" if m.get("fromMe") else display
            lines.append(f"  {who}: {m.get('body', '')[:150]}")
        return "\n".join(lines)

    def _fetch_messages(self, number: str, limit: int = 10):
        try:
            r = requests.get(f"{BRIDGE_URL}/messages",
                              params={"number": self._to_wa_id(number), "limit": limit}, timeout=15)
            if r.status_code != 200:
                return None
            return r.json().get("messages", [])
        except Exception:
            return None

    # ── SUMMARY (via your local Ollama, not the bridge) ─────────
    def _handle_summary(self, query: str) -> str:
        name, direct_number = self._extract_target(query, SUMMARY_VERBS)

        if name or direct_number:
            number, display = self._resolve(name, direct_number)
            if number == "AMBIGUOUS":
                opts = ", ".join(f"{c['name']} ({c['number']})" for c in display)
                return f"WhatsApp: '{name}' jaisi kai contacts hain -- {opts}."
            if not number:
                return f"WhatsApp: '{name}' nahi mila."
            msgs = self._fetch_messages(number, limit=25)
            if not msgs:
                return f"WhatsApp: {display} ke saath summarize karne ke liye kuch nahi mila."
            transcript = "\n".join(
                f"{'Me' if m.get('fromMe') else display}: {m.get('body', '')}" for m in msgs
            )
            label = display
        else:
            unread = self._fetch_unread()
            if not unread:
                return "WhatsApp: Koi unread chats nahi hain summarize karne ko."
            transcript = "\n".join(
                f"{c['name']} ({c['unreadCount']} unread) -- last: {c.get('lastMessage', '')}"
                for c in unread
            )
            label = "unread chats"

        summary = self._summarize_with_ollama(transcript, label)
        return f"WhatsApp: {label} ka summary:\n{summary}"

    def _fetch_unread(self):
        try:
            r = requests.get(f"{BRIDGE_URL}/unread", timeout=15)
            if r.status_code != 200:
                return []
            return r.json().get("chats", [])
        except Exception:
            return []

    def _summarize_with_ollama(self, transcript: str, label: str) -> str:
        prompt = (
            f"Summarize this WhatsApp conversation ({label}) in 3-4 short bullet "
            f"points -- questions asked, plans made, anything that needs a reply. "
            f"Hinglish is fine, keep it short.\n\n{transcript[:4000]}"
        )
        try:
            r = requests.post(f"{OLLAMA_URL}/api/generate",
                               json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                               timeout=60)
            if r.status_code == 200:
                return r.json().get("response", "").strip()
            return "(Ollama se summary nahi mila -- model sahi hai check karo.)"
        except Exception as e:
            return f"(Summary error -- {e}. 'ollama serve' chal raha hai?)"

    # ── STATUS ────────────────────────────────────────────────
    def _handle_status(self) -> str:
        return (
            "WhatsApp: Status/Stories padhna whatsapp-web.js (jo bridge use kar raha hai) "
            "abhi reliably support nahi karta -- ye khud library ka gap hai, saalon se open "
            "feature request pada hai unke GitHub pe, isliye maine fake/tuta hua code nahi diya. "
            "Agar genuinely chahiye to ek paid cloud API (Wassenger/Whapi.Cloud jaisa) use karna "
            "padega -- par wo tumhare 100% local/free setup se compromise hoga. Bolo agar wo route "
            "lena hai, wo bhi bana dunga."
        )

    # ── CONTACTS ──────────────────────────────────────────────
    def _get_contacts_display(self) -> str:
        contacts = self._get_contact_list(force_refresh=True)
        if not contacts:
            return "WhatsApp: Koi contact nahi mila."
        lines = [f"WhatsApp Contacts ({len(contacts)}):"]
        for c in contacts[:20]:
            lines.append(f"  - {c['name']}: {c['number']}")
        return "\n".join(lines)

    def _handle_save_alias(self, query: str) -> str:
        number_match = re.search(r'\b(?:\+?91[\s-]?)?([6-9]\d{9})\b', query)
        if not number_match:
            return "WhatsApp: Number nahi mila. Format -- 'keshav ka number save karo 9876543210'"
        number = number_match.group(1)
        name, _ = self._extract_target(query, SAVE_VERBS)
        if not name:
            return "WhatsApp: Kis naam se save karu?"
        aliases = self._load_json(ALIASES_PATH, {})
        aliases[name.lower()] = {"number": number, "display": name}
        self._save_json(ALIASES_PATH, aliases)
        return f"WhatsApp: '{name}' \u2192 {number} save kar diya. \u2705 Ab bas '{name} pe msg karo ...' bolna."

    # ── Contact resolution ───────────────────────────────────────
    def _resolve(self, name: str, direct_number: str):
        """Returns (number, display_name), (None, None) if nothing
        found, or ("AMBIGUOUS", [matches]) if more than one contact
        matches the name."""
        if direct_number:
            return direct_number, direct_number
        if not name:
            return None, None
        low = name.lower().strip()

        aliases = self._load_json(ALIASES_PATH, {})
        if low in aliases:
            return aliases[low]["number"], aliases[low].get("display", name)

        contacts = self._get_contact_list()
        exact = [c for c in contacts if c.get("name", "").lower() == low]
        if len(exact) == 1:
            return exact[0]["number"], exact[0]["name"]

        partial = [c for c in contacts if low in c.get("name", "").lower()]
        if len(partial) == 1:
            return partial[0]["number"], partial[0]["name"]
        if len(partial) > 1:
            return "AMBIGUOUS", partial[:5]

        return None, None

    def _get_contact_list(self, force_refresh: bool = False) -> list:
        cache = self._load_json(CONTACTS_CACHE_PATH, {"ts": 0, "contacts": []})
        if force_refresh or (time.time() - cache.get("ts", 0) > CONTACTS_CACHE_TTL):
            try:
                r = requests.get(f"{BRIDGE_URL}/contacts", timeout=10)
                if r.status_code == 200:
                    contacts = r.json().get("contacts", [])
                    cache = {"ts": time.time(), "contacts": contacts}
                    self._save_json(CONTACTS_CACHE_PATH, cache)
            except Exception:
                pass  # fall back to whatever's cached, even if stale
        return cache.get("contacts", [])

    # ── Incoming-message hooks (unchanged -- for main.py/server.py) ──
    def add_incoming_message(self, sender: str, message: str, is_owner: bool):
        self._pending_messages.append({"sender": sender, "message": message, "is_owner": is_owner})
        if len(self._pending_messages) > 50:
            self._pending_messages = self._pending_messages[-50:]

    def get_pending_summary(self) -> str:
        if not self._pending_messages:
            return ""
        msgs = self._pending_messages[-5:]
        lines = [f"\U0001f4f1 {len(self._pending_messages)} WhatsApp messages aaye:"]
        for m in msgs:
            lines.append(f"  - {m['sender']}: {m['message'][:50]}")
        self._pending_messages = []
        return "\n".join(lines)

    # ── Parsing helpers ───────────────────────────────────────────
    def _extract_target(self, query: str, verbs: list):
        """Name/number the command is aimed at -- 'keshav pe msg karo
        ...' or 'keshav ke messages padho' -> ('keshav', None)."""
        quoted = re.findall(r'"([^"]+)"', query)
        number_match = re.search(r'\b(?:\+?91[\s-]?)?([6-9]\d{9})\b', query)
        direct_number = number_match.group(1) if number_match else None

        if quoted:
            return quoted[0], direct_number

        q = re.sub(r'^\s*(?:whatsapp|altros)\s+(?:pe|par)?\s*', '', query, flags=re.IGNORECASE)
        low = q.lower()
        idx, verb = None, None
        for v in sorted(verbs, key=len, reverse=True):
            i = low.find(v)
            if i != -1:
                idx, verb = i, v
                break
        if idx is None:
            return None, direct_number

        before = self._strip_connector(q[:idx])
        if before:
            return before, direct_number

        # verb came first ("msg karo keshav ko ...") -- name is right
        # after it, before the next connector word
        after = q[idx + len(verb):].strip()
        m = re.match(r'^(\S+)\s+(?:ke liye|pe|ko|se)\b', after, re.IGNORECASE)
        if m:
            return m.group(1), direct_number
        return None, direct_number

    def _extract_message(self, query: str, verbs: list) -> str:
        quoted = re.findall(r'"([^"]+)"', query)
        if len(quoted) >= 2:
            return quoted[-1]

        q = re.sub(r'^\s*(?:whatsapp|altros)\s+(?:pe|par)?\s*', '', query, flags=re.IGNORECASE)
        low = q.lower()
        idx, verb = None, None
        for v in sorted(verbs, key=len, reverse=True):
            i = low.find(v)
            if i != -1:
                idx, verb = i, v
                break
        if idx is None:
            return ""
        before = self._strip_connector(q[:idx])
        after = q[idx + len(verb):].strip(' :,')
        after = re.sub(r'^(?:ki|ke)\s+', '', after, flags=re.IGNORECASE)

        if not before:
            # verb came first ("msg karo keshav ko kaha ho") -- strip the
            # leading "<name> <connector>" so it doesn't end up IN the message
            m = re.match(r'^\S+\s+(?:ke liye|ke|pe|ko|se)\s+', after, re.IGNORECASE)
            if m:
                after = after[m.end():].strip()

        return after

    def _strip_connector(self, text: str) -> str:
        t = text.strip()
        low = t.lower()
        for conn in sorted(CONNECTOR_WORDS, key=len, reverse=True):
            if low.endswith(' ' + conn):
                return t[: -(len(conn) + 1)].strip()
        return t

    def _to_wa_id(self, number: str) -> str:
        digits = re.sub(r'\D', '', number)
        if len(digits) == 10:
            digits = "91" + digits  # default country code
        return f"{digits}@c.us"

    def _load_json(self, path: str, default):
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def _save_json(self, path: str, data):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
