# ============================================================
#  ALTROS — BaseModule
#  Har naya capability isi class ko extend karega.
#  Ye contract hai: can_handle() + handle() implement karo.
# ============================================================

from abc import ABC, abstractmethod
from typing import Optional


class BaseModule(ABC):
    """
    Har ALTROS module ka blueprint.
    
    Phase 2 mein voice module likhoge? BaseModule extend karo.
    Phase 4 mein laptop control? BaseModule extend karo.
    Sab ek jaisa interface — router ko kuch farak nahi padega.
    """

    name: str = "base"
    description: str = ""

    @abstractmethod
    def can_handle(self, query: str, context: dict) -> bool:
        """
        Kya ye module is query ko handle kar sakta hai?
        Router yahi check karega.
        """
        pass

    @abstractmethod
    def handle(self, query: str, context: dict) -> str:
        """
        Query process karo aur response string return karo.
        """
        pass

    def on_enable(self):
        """Module enable hone pe kuch setup karna ho toh yahan."""
        pass

    def on_disable(self):
        """Module disable hone pe cleanup."""
        pass
