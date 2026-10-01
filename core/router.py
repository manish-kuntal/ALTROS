# ============================================================
#  ALTROS — Router + Module Manager
# ============================================================

from typing import Optional
from modules.base import BaseModule
from config import MODULES_ENABLED

# Ye modules direct response dete hain — brain BYPASS hota hai
DIRECT_RESPONSE_MODULES = {"pc_control", "autonomy"}


class ModuleManager:
    def __init__(self):
        self._modules: dict[str, BaseModule] = {}

    def register(self, module: BaseModule):
        name = module.name
        if MODULES_ENABLED.get(name, False):
            self._modules[name] = module
            module.on_enable()
            print(f"  ✅ Module loaded: {name}")
        else:
            print(f"  ⏸  Module skipped (disabled): {name}")

    def get_handler(self, query: str, context: dict) -> Optional[BaseModule]:
        for module in self._modules.values():
            try:
                if module.can_handle(query, context):
                    return module
            except Exception:
                continue
        return None

    def list_active(self) -> list[str]:
        return list(self._modules.keys())


class Router:
    def __init__(self, brain, memory, module_manager: ModuleManager):
        self.brain = brain
        self.memory = memory
        self.mm = module_manager

    def route(self, user_input: str) -> str:
        context = {
            "history": self.memory.get_history(),
            "profile": self.memory.profile,
        }

        handler = self.mm.get_handler(user_input, context)

        if handler:
            result = handler.handle(user_input, context)

            # PC Control / Autonomy — direct response, brain BYPASS
            if handler.name in DIRECT_RESPONSE_MODULES:
                if result and result.strip():
                    print(f"\nALTROS: {result}\n")
                    return result
                # Module ne handle nahi kiya — brain ko do
                return self.brain.think(user_input)

            # Knowledge / Internet — result context ke roop mein brain ko do
            if result and result.strip():
                return self.brain.think(user_input, extra_context=result)

        # Default: direct brain
        return self.brain.think(user_input)