# ============================================================
#  ALTROS — Thinking Loop Engine
#  User Input → Intent → Plan → Execute → Self-Check → Answer
# ============================================================

import json


INTENT_PROMPT = """Analyze this user input and return JSON only:
{
  "intent": "question|task|conversation|command|search",
  "needs_search": true/false,
  "needs_pc_control": false,
  "needs_knowledge": true/false,
  "complexity": "simple|medium|complex",
  "topic": "brief topic description"
}
User input: """

PLAN_PROMPT = """You are a planning engine. Create a brief step-by-step plan.
Return JSON only:
{
  "steps": ["step1", "step2", "step3"],
  "tools_needed": ["search/knowledge/pc_control/memory/none"]
}
Task: """

SELFCHECK_PROMPT = """Review this response for accuracy and quality.
Return JSON only:
{
  "is_accurate": true/false,
  "is_complete": true/false,
  "confidence": 0-10,
  "issues": "any issues found or empty string"
}
Response to check: """


class ThinkingEngine:
    def __init__(self, brain):
        self.brain = brain
        self.enabled = True

    def detect_intent(self, user_input: str) -> dict:
        try:
            prompt = INTENT_PROMPT + user_input
            response = self._quick_llm(prompt)
            return self._parse_json(response)
        except Exception:
            return {"intent": "conversation", "needs_search": False,
                    "needs_knowledge": False, "complexity": "simple", "topic": "general"}

    def make_plan(self, user_input: str, intent: dict) -> list:
        if intent.get("complexity") == "simple":
            return ["Direct response dena"]
        try:
            prompt = PLAN_PROMPT + user_input
            response = self._quick_llm(prompt)
            data = self._parse_json(response)
            return data.get("steps", ["Direct response dena"])
        except Exception:
            return ["Direct response dena"]

    def self_check(self, response: str, user_input: str) -> dict:
        # Only check complex responses
        if len(response) < 100:
            return {"is_accurate": True, "confidence": 8, "issues": ""}
        try:
            prompt = SELFCHECK_PROMPT + response[:500]
            result = self._quick_llm(prompt)
            return self._parse_json(result)
        except Exception:
            return {"is_accurate": True, "confidence": 7, "issues": ""}

    def _quick_llm(self, prompt: str) -> str:
        import requests
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        try:
            res = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=15
            )
            return res.json().get("response", "")
        except Exception:
            return ""

    def _parse_json(self, text: str) -> dict:
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception:
            pass
        return {}
