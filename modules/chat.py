# ============================================================
#  ALTROS Module: Chat (Phase 1)
#  Default chat handler — always active.
#  Agar koi dusra module handle nahi karta, ye handle karta hai.
# ============================================================

from modules.base import BaseModule


class ChatModule(BaseModule):
    name = "chat"
    description = "Basic conversation — default fallback module"

    def can_handle(self, query: str, context: dict) -> bool:
        # Chat module always ready hai, but low priority.
        # Isko sirf tab use karo jab koi specialist module nahi mila.
        return True

    def handle(self, query: str, context: dict) -> str:
        # Chat module extra context inject nahi karta —
        # brain directly hi handle karega.
        return ""
