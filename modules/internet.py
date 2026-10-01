# ============================================================
#  ALTROS Module: Internet Search (Phase 4)
#  Search → Filter → Summarize pipeline
# ============================================================

from modules.base import BaseModule

SEARCH_TRIGGERS = [
    "latest", "aaj ka", "abhi", "news", "current", "today",
    "recent", "breaking", "live", "update", "2025", "2026",
    "kya ho raha", "kya hua",
    "launch", "launched", "release", "released", "available",
    "price", "rate", "specs", "review", "compare", "vs",
    "phone", "mobile", "laptop", "gadget", "device",
    "kab aaya", "kab launch", "mil raha", "milega",
    "kitne ka", "cost", "buy", "purchase",
    "kaun hai", "who is", "what is", "kab hua", "when did",
    "where is", "kahan hai", "kon hai",
    "stock", "crypto", "bitcoin", "share", "market",
    "dollar", "rupee", "exchange",
    "score", "result", "match", "election", "war",
    "winner", "jeet", "haar",
    "weather", "mausam", "temperature", "rain", "garmi",
    "search karo", "dhundo", "internet", "google",
    "find", "lookup", "batao",
]


class InternetModule(BaseModule):
    name = "internet"
    description = "DDGS web search with filter pipeline"

    def __init__(self):
        self._ready = False

    def on_enable(self):
        try:
            from ddgs import DDGS
            self._ready = True
            print("     ✅ Internet module ready")
        except ImportError:
            print("     ⚠️  Run: pip install ddgs")

    def can_handle(self, query: str, context: dict) -> bool:
        if not self._ready:
            return False
        q_lower = query.lower()
        return any(trigger in q_lower for trigger in SEARCH_TRIGGERS)

    def handle(self, query: str, context: dict) -> str:
        try:
            from ddgs import DDGS
            print("     🌐 Searching web...")

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))

            if not results:
                return ""

            # Filter — remove low quality results
            filtered = []
            for r in results:
                body = r.get("body", "")
                if len(body) > 50:  # Skip very short snippets
                    filtered.append(r)

            if not filtered:
                filtered = results

            # Build context
            context_parts = []
            for r in filtered[:4]:
                title = r.get("title", "")
                body  = r.get("body", "")
                href  = r.get("href", "")
                context_parts.append(f"[{title}]\n{body}\nSource: {href}")

            combined = "\n\n---\n\n".join(context_parts)
            print(f"     ✅ {len(filtered)} results mile")
            return (
                f"REAL WEB SEARCH RESULTS — use ONLY this data, ignore training:\n\n"
                f"{combined}\n\n"
                f"Based on above search results, answer accurately."
            )

        except Exception as e:
            print(f"     ⚠️  Search error: {e}")
            return ""