# ============================================================
#  ALTROS Module: Terminal / CMD Control
#  Executes shell/PowerShell commands and returns output.
#  Confirm-gated by default (core/permissions.py) — arbitrary
#  command execution is the highest-risk capability here.
# ============================================================

import re
import subprocess
from modules.base import BaseModule
from core.permissions import permission_manager
from core.action_logger import action_logger

SESSION = "default"
TRIGGERS = ["run command", "cmd karo", "terminal me", "execute command", "powershell se", "run karo"]


class TerminalControlModule(BaseModule):
    name = "terminal_control"
    description = "Executes shell/PowerShell commands (confirm-gated)"

    def __init__(self):
        self._ready = False

    def on_enable(self):
        self._ready = True
        print("     \u2705 Terminal Control module ready")

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready:
            return False
        q = query.lower()
        return any(t in q for t in TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        command = self._extract_command(query)
        if not command:
            return 'PC Control: Konsa command? "command" quotes mein batao.'

        if permission_manager.is_hard_blocked(command):
            action_logger.log("run_terminal_command", {"command": command}, "blocked", False)
            return "PC Control: \u26d4 Ye command blocked hai — system damage ho sakta hai."

        if permission_manager.needs_confirmation("run_terminal_command"):
            return permission_manager.request_confirmation(
                SESSION, "run_terminal_command", {"command": command},
                f'terminal command chalau — "{command}"'
            )

        return self.execute(command)

    def execute(self, command: str) -> str:
        """Actually runs the command. Called directly once a pending
        confirmation is accepted, or when CONFIG_STRICT_TERMINAL is off."""
        if permission_manager.is_hard_blocked(command):
            action_logger.log("run_terminal_command", {"command": command}, "blocked", False)
            return "PC Control: \u26d4 Ye command blocked hai."
        try:
            proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = (proc.stdout or proc.stderr or "(no output)").strip()[:1500]
            action_logger.log("run_terminal_command", {"command": command}, output, proc.returncode == 0)
            return f"PC Control: Command run ho gaya \u2705\n```\n{output}\n```"
        except subprocess.TimeoutExpired:
            action_logger.log("run_terminal_command", {"command": command}, "timeout", False)
            return "PC Control: \u23f1\ufe0f Command timeout ho gaya (30s se zyada le raha tha)."
        except Exception as e:
            action_logger.log("run_terminal_command", {"command": command}, str(e), False)
            return f"PC Control: \u274c Command error — {e}"

    def _extract_command(self, query: str) -> str:
        m = re.search(r'"([^"]+)"', query)
        if m:
            return m.group(1)
        low = query.lower()
        for kw in TRIGGERS:
            if kw in low:
                idx = low.index(kw) + len(kw)
                return query[idx:].strip(' :"')
        return ""
