# ============================================================
#  ALTROS Core: Permission System
#  Classifies actions by risk and manages the confirm-before-
#  you-run flow for anything dangerous or irreversible.
# ============================================================

import time

# Commands that are ALWAYS blocked — no confirmation can override these.
HARD_BLOCKED_PATTERNS = [
    "format c:", "format d:", "del /f /s /q c:\\", "rd /s /q c:\\windows",
    "rm -rf /", "rm -rf /*", "rm -rf ~", ":(){ :|:& };:",
    "reg delete hklm", "bcdedit", "diskpart",
    "cipher /w:c", "vssadmin delete shadows",
    "net user administrator", "attrib +h +s c:\\",
]

# Action types that must be confirmed by the user ("haan"/"yes")
# before they actually run.
CONFIRM_ACTIONS = {
    "delete_file", "delete_folder",
    "run_terminal_command", "kill_process",
    "send_whatsapp_message", "send_whatsapp_file",
}

# If False, terminal commands run immediately without asking first
# (blocked patterns are still always blocked). Flip this in your own
# copy if you want less friction — you take on the risk.
CONFIG_STRICT_TERMINAL = True


class PermissionManager:
    """Single shared gatekeeper for anything risky PC Control does."""

    def __init__(self):
        self._pending = {}  # session_key -> {"action", "payload", "summary", "ts"}

    # ---- risk checks ----------------------------------------------------
    def is_hard_blocked(self, raw_text: str) -> bool:
        low = raw_text.lower()
        return any(p in low for p in HARD_BLOCKED_PATTERNS)

    def needs_confirmation(self, action_type: str) -> bool:
        if action_type == "run_terminal_command" and not CONFIG_STRICT_TERMINAL:
            return False
        return action_type in CONFIRM_ACTIONS

    # ---- confirmation flow -----------------------------------------------
    def request_confirmation(self, session_key: str, action_type: str, payload: dict,
                              summary: str, label: str = "PC Control") -> str:
        self._pending[session_key] = {
            "action": action_type, "payload": payload, "summary": summary, "ts": time.time(),
        }
        return (
            f"{label}: \u26a0\ufe0f Confirm karo — {summary}\n"
            f"Karu? bolo 'haan' ya 'nahi'"
        )

    def check_confirmation_reply(self, session_key: str, query: str):
        """
        Returns (action_type, payload) if this query confirms the
        pending action, "CANCELLED" if it declines, or None if the
        query doesn't look like a yes/no reply (pending stays queued).
        """
        pending = self._pending.get(session_key)
        if not pending:
            return None
        q = query.lower().strip()
        if any(w in q for w in ["haan", "yes", "han", "confirm", "ha karo"]):
            self._pending.pop(session_key, None)
            return (pending["action"], pending["payload"])
        if any(w in q for w in ["nahi", "no", "cancel", "mat karo"]):
            self._pending.pop(session_key, None)
            return "CANCELLED"
        return None

    def has_pending(self, session_key: str) -> bool:
        return session_key in self._pending


permission_manager = PermissionManager()
