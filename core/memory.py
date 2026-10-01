# ============================================================
#  ALTROS — 3-Layer Memory System
#  Layer 1: Short-term (last N messages)
#  Layer 2: Long-term (facts with importance score)
#  Layer 3: Semantic (ChromaDB — books/knowledge)
# ============================================================

import json
import os
from datetime import datetime
from config import (
    USER_PROFILE_FILE, CONVERSATIONS_DIR,
    MAX_SHORT_TERM, USER_NAME
)

MEMORY_CATEGORIES = {
    "goal": 10,
    "fact": 7,
    "preference": 6,
    "project": 8,
    "habit": 5,
    "emotion": 4,
    "general": 3,
}


class MemorySystem:
    def __init__(self):
        self._ensure_dirs()
        self.short_term: list[dict] = []
        self.profile: dict = self._load_profile()
        self.facts: list[dict] = self._load_facts()

    # ── Layer 1: Short-term ──────────────────────────────────

    def add_message(self, role: str, content: str):
        self.short_term.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.short_term) > MAX_SHORT_TERM * 2:
            self.short_term = self.short_term[-(MAX_SHORT_TERM * 2):]

    def get_history(self) -> list[dict]:
        return [{"role": m["role"], "content": m["content"]} for m in self.short_term]

    def clear_session(self):
        self._save_conversation()
        self.short_term = []

    # ── Layer 2: Long-term facts ─────────────────────────────

    def remember(self, key: str, value, category: str = "fact", importance: int = None):
        if importance is None:
            importance = MEMORY_CATEGORIES.get(category, 5)

        self.profile[key] = value
        self.profile["last_updated"] = datetime.now().isoformat()
        self._save_profile()

        # Also add to structured facts
        fact = {
            "key": key,
            "value": str(value)[:300],
            "category": category,
            "importance": importance,
            "timestamp": datetime.now().isoformat(),
        }
        # Update existing or add new
        self.facts = [f for f in self.facts if f["key"] != key]
        self.facts.append(fact)
        self._save_facts()

    def recall(self, key: str, default=None):
        return self.profile.get(key, default)

    def get_top_facts(self, n: int = 10) -> list[dict]:
        return sorted(self.facts, key=lambda x: x.get("importance", 0), reverse=True)[:n]

    def get_profile_summary(self) -> str:
        if not self.profile:
            return ""
        top_facts = self.get_top_facts(15)
        if not top_facts:
            # Fallback to profile dict
            lines = [f"Known facts about {USER_NAME}:"]
            skip = {"last_updated"}
            for k, v in self.profile.items():
                if k not in skip:
                    lines.append(f"  - {k}: {v}")
            return "\n".join(lines)

        lines = [f"Known facts about {USER_NAME} (by importance):"]
        for fact in top_facts:
            imp = fact.get("importance", 5)
            cat = fact.get("category", "fact")
            lines.append(f"  [{cat.upper()} | {imp}/10] {fact['key']}: {fact['value']}")
        return "\n".join(lines)

    def extract_and_store(self, user_text: str):
        """Smart extraction from conversation."""
        text_lower = user_text.lower()

        # ALTROS project and AI-assistant goals
        if any(w in text_lower for w in [
            "apna ai brain", "ai brain banana", "personal ai", "altros",
            "ollama", "llama 3", "llama3",
        ]):
            self.remember(
                "altros_vision",
                user_text[:300],
                category="project",
                importance=10,
            )

        # Hardware and runtime facts
        if any(w in text_lower for w in [
            "rtx 4050", "acer aspire", "i7 13", "ollama ke through",
        ]):
            self.remember(
                "ai_hardware",
                user_text[:300],
                category="fact",
                importance=8,
            )

        # Goals — high importance
        if any(w in text_lower for w in [
            "mera goal", "main chahta", "future mein", "banna chahta",
            "dream", "banana chahta",
        ]):
            self.remember("goal", user_text[:200], category="goal", importance=10)

        # Projects
        elif any(w in text_lower for w in ["project", "bana raha", "working on", "develop"]):
            self.remember("current_project", user_text[:200], category="project", importance=8)

        # Preferences
        elif any(w in text_lower for w in ["mujhe pasand", "i like", "favourite", "best", "prefer"]):
            self.remember("preference", user_text[:200], category="preference", importance=6)

        # Facts about self
        elif any(w in text_lower for w in ["main ", "mera naam", "mai ", "i am", "i'm"]):
            self.remember("self_info", user_text[:200], category="fact", importance=7)

    # ── Helpers ──────────────────────────────────────────────

    def _ensure_dirs(self):
        os.makedirs(os.path.dirname(USER_PROFILE_FILE), exist_ok=True)
        os.makedirs(CONVERSATIONS_DIR, exist_ok=True)

    def _load_profile(self) -> dict:
        if os.path.exists(USER_PROFILE_FILE):
            try:
                with open(USER_PROFILE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_profile(self):
        with open(USER_PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.profile, f, ensure_ascii=False, indent=2)

    def _load_facts(self) -> list:
        facts_file = USER_PROFILE_FILE.replace("user_profile.json", "facts.json")
        if os.path.exists(facts_file):
            try:
                with open(facts_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_facts(self):
        facts_file = USER_PROFILE_FILE.replace("user_profile.json", "facts.json")
        with open(facts_file, "w", encoding="utf-8") as f:
            json.dump(self.facts, f, ensure_ascii=False, indent=2)

    def _save_conversation(self):
        if not self.short_term:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(CONVERSATIONS_DIR, f"{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.short_term, f, ensure_ascii=False, indent=2)