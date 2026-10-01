# ============================================================
#  ALTROS Module: Server (Phase 5)
#  FastAPI + SSE Streaming — ChatGPT style
# ============================================================

import os
import threading
import uvicorn
from modules.base import BaseModule
from config import SERVER_HOST, SERVER_PORT

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


class ServerModule(BaseModule):
    name = "server"
    description = "FastAPI server — phone + browser access"

    def __init__(self):
        self._ready = False
        self._router = None
        self._memory = None
        self._voice  = None

    def set_dependencies(self, router, memory, voice_mod):
        self._router = router
        self._memory = memory
        self._voice  = voice_mod

    def on_enable(self):
        self._ready = True
        print("     ✅ Server module ready")

    def can_handle(self, query, context): return False
    def handle(self, query, context): return ""

    def start(self):
        if not self._ready: return
        threading.Thread(target=self._run_server, daemon=True).start()

    def _run_server(self):
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import FileResponse, StreamingResponse
        from pydantic import BaseModel
        import json, time

        app = FastAPI(title="ALTROS")
        app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

        class Msg(BaseModel):
            text: str

        @app.get("/")
        def root():
            idx = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(idx):
                return FileResponse(idx, media_type="text/html")
            return {"status": "ALTROS online"}

        @app.post("/chat")
        def chat(msg: Msg):
            if not msg.text.strip():
                return {"response": "Kuch toh bolo!"}
            self._memory.extract_and_store(msg.text)
            response = self._router.route(msg.text)
            self._memory.add_message("user", msg.text)
            self._memory.add_message("assistant", response)
            return {"response": response}

        @app.post("/chat/stream")
        def chat_stream(msg: Msg):
            """SSE streaming — ChatGPT style word by word"""
            if not msg.text.strip():
                return {"response": "Kuch toh bolo!"}

            self._memory.extract_and_store(msg.text)
            response = self._router.route(msg.text)
            self._memory.add_message("user", msg.text)
            self._memory.add_message("assistant", response)

            def generate():
                words = response.split(' ')
                for i, word in enumerate(words):
                    token = word + ('' if i == len(words)-1 else ' ')
                    data = json.dumps({"token": token})
                    yield f"data: {data}\n\n"
                    time.sleep(0.04)
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
            )

        @app.get("/memory")
        def get_memory():
            return {"profile": self._memory.profile}

        @app.post("/remember")
        def remember(key: str, value: str):
            self._memory.remember(key, value)
            return {"status": "done", "key": key, "value": value}

        @app.get("/status")
        def status():
            return {
                "status": "online",
                "model": getattr(self._router.brain, "model", "unknown"),
                "user": "Manish",
            }

        print(f"\n🌐 ALTROS server — http://localhost:{SERVER_PORT}")
        print(f"📱 Browser se bhi khol sakte ho: http://localhost:{SERVER_PORT}\n")
        uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level="error")