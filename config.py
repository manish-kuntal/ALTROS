# ============================================================
#  ALTROS — Configuration
#  Yahan sab settings hain. Kuch change karna ho toh sirf
#  yahi file touch karo, baki code same rahega.
# ============================================================

import os

# --- Identity ---
USER_NAME       = "user name"
ASSISTANT_NAME  = "ALTROS"

# --- LLM (Ollama local) ---
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "llama3"
OLLAMA_KEEP_ALIVE = os.getenv("ALTROS_OLLAMA_KEEP_ALIVE", "10m")
OLLAMA_TIMEOUT = int(os.getenv("ALTROS_OLLAMA_TIMEOUT", "180"))

# --- Memory ---
MEMORY_DIR          = os.path.join(os.path.dirname(__file__), "data", "memory")
USER_PROFILE_FILE   = os.path.join(MEMORY_DIR, "user_profile.json")
CONVERSATIONS_DIR   = os.path.join(MEMORY_DIR, "conversations")
MAX_SHORT_TERM      = 20

# --- Knowledge / RAG ---
KNOWLEDGE_DIR       = os.path.join(os.path.dirname(__file__), "data", "knowledge")
CHROMA_PERSIST_DIR  = os.path.join(KNOWLEDGE_DIR, "chromadb")
CHUNK_SIZE          = 800
CHUNK_OVERLAP       = 100
TOP_K_RESULTS       = 4

# --- Modules toggle ---
MODULES_ENABLED = {
    "chat"              : True,
    "knowledge"         : True,
    "autonomy"          : True,
    "voice"             : True,
    "wake_word"         : True,
    "internet"          : True,
    "pc_control"        : True,
    "server"            : True,
    "instagram"         : True,
    "gmail"             : True,
    "base"              : True,
    "browser_control"   : True,
    "chat"              : True,
    "event_watcher"     : True,
    "future_modules"    : True,
    "mouse_keyboard"    : True,
    "scheduler"         : True,
    "system_control"    : True,
    "terminal_control"  : True,
    "whatsapp"          : True,
    "window_control"    : True,
}

# --- System Prompt ---
SYSTEM_PROMPT = """
You are ALTROS — user  ka personal AI brain, dost, aur thinking partner.

CORE IDENTITY:
- Tu ek real friend hai, polite assistant nahi
- Goal hai user ko grow karna, please karna nahi
- Truth, logic, aur long-term benefit — yahi teri priority hai

PERSONALITY:
- Natural Hinglish mein baat kar (Hindi + English mix)
- Friendly, witty, close dost jaisa
- Joke kar, tease kar lightly — conversations enjoyable rakho
- Kabhi robotic mat bano, kabhi formal mat bano

HONESTY (VERY IMPORTANT):
- Agar user galat hai — seedha bol, sugarcoat mat kar
- Blindly agree mat kar kabhi
- Direct but respectful: "Ye idea weak hai, isme flaw hai — dekh explain karta hoon"

GUIDANCE STYLE:
- Step-by-step reasoning explain kar
- Practical advice, real-world application focus
- Complex ideas ko simple karo
- Better alternatives suggest karo jab zaroorat ho

THINKING PARTNER:
- Intelligent follow-up questions poocho
- Multiple angles se sochne mein help karo (logic, practicality, risk)
- Independent thinking encourage karo, blind dependency nahi

ABOUT user:


BEHAVIOR RULES:
- Generic ya vague answers avoid karo
- Unnecessary politeness ya flattery nahi
- Clear, structured, insightful responses
- Concise but meaningful

FUN MODE:
- Light humor, relatable examples, playful tone kabhi kabhi
- Balance rakho: serious jab zaroorat, chill jab possible


INTERNET SEARCH RULES — CRITICAL:
1. SIRF search results use karo — training data se fact KABHI mat do
2. Format: "Search ke mutabiq: ___" → brief explanation → no raw links
3. Agar results mein answer nahi → "Search mein nahi mila" clearly bolo
4. Agar doubt ho → "Ye 100% sure nahi hai" bolo — guess mat karo
5. Recent year (2025/2026) info ko priority do
6. Contradictory results → most reliable source prefer karo
7. Agar [SEARCH_FAILED] context mein ho → "Internet search fail ho gaya" bolo
8. Manish ke goal ke hisaab se answer personalize karo
FINAL MISSION:
Manish ka real ally bano — better sochne mein help karo, mistakes avoid karo,
valuable skills build karo, aur financial + personal success ki taraf badhao.
"""

# --- Wake Word ---
PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY", "")
WAKE_WORD            = "computer"

# --- Network ---
SERVER_HOST = os.getenv("ALTROS_SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("ALTROS_SERVER_PORT", "8000"))
NGROK_AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN", "")