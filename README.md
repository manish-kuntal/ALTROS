# ALTROS — Setup Guide

## Phase 1 Setup (15 minutes)

### Step 1 — Ollama install karo
```
https://ollama.ai se download karo (Windows/Mac/Linux)
```

### Step 2 — Llama 3 pull karo
```bash
ollama pull llama3
ollama serve          # background mein chalta rahega
```

### Step 3 — Python dependencies
```bash
py -3.12 -m pip install -r requirements.txt
```

### Step 4 — ALTROS run karo
```bash
py -3.12 main.py

### Optional: phone access

Set your ngrok token in the current terminal session without putting it in source code:

```powershell
$env:NGROK_AUTHTOKEN = "YOUR_TOKEN"
py -3.12 main.py
```

For wake-word support, set your Picovoice key similarly:

```powershell
$env:PORCUPINE_ACCESS_KEY = "YOUR_KEY"
```

Do not commit either token. Rotate a token immediately if it was pasted into chat or a public file.
```

### Step 5 — Book add karo
```bash
py -3.12 main.py --add-book "C:/path/to/atomic_habits.pdf"
```

---

## Commands (runtime)
| Command | Kaam |
|---|---|
| `exit` | Band karo |
| `clear` | Session clear |
| `memory` | Apna profile dekho |
| `remember goal software engineer` | Kuch yaad karwao |
| `books` | Knowledge base count |
| `help` | Commands list |

---

## Future Phases — Kaise enable karein

### Phase 2 — Voice
1. `requirements.txt` mein voice lines uncomment karo
2. `pip install openai-whisper TTS pvporcupine`
3. `modules/future_modules.py` mein `VoiceModule` implement karo
4. `config.py` mein `MODULES_ENABLED["voice"] = True`

### Phase 4 — Internet + PC Control
1. Same pattern: implement → enable in config → done

### Phase 5 — Phone Access
1. `ServerModule.start()` implement karo (FastAPI)
2. Ngrok se tunnel banao: `ngrok http 8000`
3. Phone ke browser mein URL kholo

---

## Folder Structure
```
altros/
├── main.py              ← Entry point
├── config.py            ← Sab settings
├── requirements.txt
├── core/
│   ├── brain.py         ← LLM engine
│   ├── memory.py        ← Memory system
│   └── router.py        ← Module router
├── modules/
│   ├── base.py          ← Module blueprint
│   ├── chat.py          ← Phase 1: Basic chat
│   ├── knowledge.py     ← Phase 1: Book RAG
│   └── future_modules.py ← Phase 2-5 stubs
└── data/
    ├── memory/
    │   ├── user_profile.json
    │   └── conversations/
    └── knowledge/
        └── chromadb/    ← Vector DB
```
