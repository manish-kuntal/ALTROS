# ============================================================
#  ALTROS — Brain (LLM Engine) with Thinking Loop
# ============================================================

import requests
import json
from config import (
    OLLAMA_BASE_URL,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    SYSTEM_PROMPT,
)


class Brain:
    def __init__(self, memory):
        self.memory = memory
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL
        self.thinking_engine = None  # Set after init

    def set_thinking_engine(self, engine):
        self.thinking_engine = engine

    def think(self, user_input: str, extra_context: str = "") -> str:
        """
        Full thinking loop:
        Intent → Plan → Execute → Self-check → Answer
        """
        # Step 1: Intent detection (only for complex queries)
        intent = {"complexity": "simple", "intent": "conversation"}
        if self.thinking_engine and len(user_input) > 20:
            intent = self.thinking_engine.detect_intent(user_input)

        # Step 2: Build enhanced system prompt
        profile_summary = self.memory.get_profile_summary()
        top_facts = self.memory.get_top_facts(5) if hasattr(self.memory, 'get_top_facts') else []

        system = SYSTEM_PROMPT
        if profile_summary:
            system += f"\n\n{profile_summary}"
        if extra_context:
            system += f"\n\nRelevant context (USE THIS INFORMATION):\n{extra_context}"

        # Step 3: Add planning context for complex queries
        if intent.get("complexity") == "complex" and self.thinking_engine:
            plan = self.thinking_engine.make_plan(user_input, intent)
            if plan:
                system += f"\n\nApproach this step by step:\n" + "\n".join(f"- {s}" for s in plan)

        # Step 4: Build messages
        messages = [{"role": "system", "content": system}]
        messages += self.memory.get_history()
        messages.append({"role": "user", "content": user_input})

        # Step 5: Generate response
        response = self._call_llm(messages)

        return response

    def _call_llm(self, messages: list) -> str:
        try:
            res = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "keep_alive": OLLAMA_KEEP_ALIVE,
                },
                timeout=OLLAMA_TIMEOUT,
            )
            res.raise_for_status()
            data = res.json()
            reply = data.get("message", {}).get("content", "").strip()

            if reply:
                print(f"\nALTROS: {reply}\n")
                return reply
            else:
                print(f"\nALTROS: (blank response)\n")
                return ""

        except requests.exceptions.ConnectionError:
            msg = "Ollama connect nahi hua. 'ollama serve' chalaao."
            print(f"\nALTROS: ⚠️  {msg}\n")
            return msg
        except requests.exceptions.Timeout:
            msg = "Soch raha hoon... thoda time lag raha hai. Dobara try karo."
            print(f"\nALTROS: ⚠️  {msg}\n")
            return msg
        except Exception as e:
            msg = f"Error: {str(e)}"
            print(f"\nALTROS: ⚠️  {msg}\n")
            return msg

    def check_connection(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False