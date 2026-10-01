# ============================================================
#  ALTROS Module: Voice I/O -- full voice-to-voice conversation
#
#  Flow: wake word -> record until you stop talking (not a fixed
#  timer) -> Whisper transcribes -> your query goes through the
#  SAME pipeline a typed line would -> the text response is
#  spoken back in a voice picked to match Hindi/Hinglish vs
#  English -> it keeps listening for a follow-up for a few
#  seconds without needing the wake word again -> back to idle.
#
#  Say something while it's talking and it stops (barge-in) --
#  this is the "interrupt detection" your own build guide lists
#  as a goal.
#
#  pip install sounddevice numpy openai-whisper edge-tts pygame
#  (pyttsx3 only needed if you set TTS_ENGINE = "pyttsx3" below)
#
#  TTS_ENGINE defaults to "edge": Microsoft's free cloud neural
#  voices, specifically built for Hindi/English code-mixing --
#  pyttsx3's offline voices read Hindi words with English letter-
#  sound rules and it sounds wrong. Edge TTS needs internet for
#  the VOICE ONLY (your Llama3 brain stays 100% local either
#  way). Set TTS_ENGINE = "pyttsx3" for fully-offline voice
#  output instead, at the cost of Hinglish pronunciation quality.
# ============================================================

import os
import re
import time
import threading
import numpy as np
import sounddevice as sd
from modules.base import BaseModule

TTS_ENGINE = "edge"  # "edge" (natural Hinglish, needs internet) or "pyttsx3" (fully offline)

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 500        # RMS below this = silence. Mic/room dependent --
                                # tune this first if recording cuts off too early
                                # or never stops (see the step-by-step guide).
SILENCE_CHUNKS_TO_STOP = 18    # ~1.5s of silence (at 0.08s/chunk) ends recording
MAX_RECORD_SECONDS = 20
FOLLOWUP_LISTEN_SECONDS = 8    # after speaking a reply, keep listening this long
                                # for a follow-up without needing the wake word again

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTS_TEMP_PATH = os.path.join(_ROOT, "data", "_tts_out.mp3")

VOICE_HINDI = "hi-IN-SwaraNeural"      # Edge TTS voice for Hindi/Hinglish-heavy text
VOICE_ENGLISH = "en-IN-NeerjaNeural"   # Edge TTS voice for mostly-English text
                                        # (Indian English, not US/UK -- more consistent
                                        # with the assistant's overall voice/persona)

HINDI_MARKERS = {
    "hai", "hain", "ho", "hoon", "tha", "thi", "the", "kya", "kaise", "kaisi",
    "kaisa", "kahan", "kab", "kyun", "kyu", "karo", "kar", "karna", "kiya",
    "mein", "se", "pe", "ko", "ka", "ki", "ke", "aur", "nahi", "nahin", "haan",
    "bhai", "yaar", "acha", "theek", "bata", "batao", "chalo", "abhi", "phir",
    "wala", "wali", "wale", "aap", "tum", "mera", "meri", "tera", "teri",
    "hoga", "hogi", "raha", "rahi", "rahe", "diya", "liya", "gaya", "gayi",
}

try:
    import whisper
    _WHISPER_OK = True
except ImportError:
    _WHISPER_OK = False
_WHISPER_MODEL = None  # loaded lazily on first use -- slow to load, do it once

try:
    import edge_tts
    import asyncio
    _EDGE_TTS_OK = True
except ImportError:
    _EDGE_TTS_OK = False

try:
    import pygame
    _PYGAME_OK = True
except ImportError:
    _PYGAME_OK = False

try:
    import pyttsx3
    _PYTTSX3_OK = True
except ImportError:
    _PYTTSX3_OK = False


class VoiceModule(BaseModule):
    name = "voice"
    description = "Full voice conversation -- listen, transcribe, speak back in Hindi/English/Hinglish"

    def __init__(self):
        self._ready = False
        self._query_handler = None   # wired via set_query_handler()
        self._pyttsx3_engine = None
        self._interrupt_flag = threading.Event()

    def on_enable(self):
        if self._ready:
            return  # already initialized -- your main.py's boot() may
                     # register+enable this, and the wake-word wiring
                     # calls on_enable() again explicitly; harmless
                     # either way, but no need to redo the setup work
        missing = []
        if not _WHISPER_OK:
            missing.append("openai-whisper")
        if TTS_ENGINE == "edge" and not _EDGE_TTS_OK:
            missing.append("edge-tts")
        if TTS_ENGINE == "edge" and not _PYGAME_OK:
            missing.append("pygame")
        if TTS_ENGINE == "pyttsx3" and not _PYTTSX3_OK:
            missing.append("pyttsx3")
        if missing:
            print(f"     \u26a0\ufe0f Voice module incomplete -- 'pip install {' '.join(missing)}'")
            return
        if TTS_ENGINE == "edge" and _PYGAME_OK:
            pygame.mixer.init()
        os.makedirs(os.path.dirname(TTS_TEMP_PATH), exist_ok=True)
        self._ready = True
        print(f"     \u2705 Voice module ready (TTS engine: {TTS_ENGINE})")

    def set_query_handler(self, fn):
        """fn(text: str) -> str -- point this at whatever function in
        main.py/router.py already turns a TYPED line into a response
        string. A spoken query goes through the exact same pipeline
        as a typed one; this module only handles the ears and mouth."""
        self._query_handler = fn

    # ── Direct listen/speak -- used by your main.py's own call sites: ──
    #    the typed 'voice' command, the keyboard shortcut, the old
    #    wake_word_mod fallback, and --voice CLI mode. run_conversation_turn()
    #    (below) is the newer all-in-one version used by wake_word.py's
    #    background listener; these do the same recording/speaking work
    #    without needing a query handler wired up, for callers that
    #    handle routing themselves.
    def listen(self, duration: int = 5) -> str:
        """Records until you stop talking (or `duration` seconds pass,
        whichever comes first) and returns the transcribed text, or ''
        if nothing was heard."""
        if not self._ready:
            return ""
        audio = self._record_until_silence(max_seconds=duration)
        if audio is None or len(audio) < SAMPLE_RATE * 0.3:
            return ""
        return self._transcribe(audio)

    def speak(self, text: str):
        """Speaks `text` aloud, voice picked automatically for
        Hindi/Hinglish vs English. Blocks until playback finishes (or
        is interrupted by you talking)."""
        if not self._ready or not text:
            return
        self._speak(text)

    # Manual one-shot trigger still works too: 'voice' / 'voice 10',
    # same commands your build guide already documents, now with
    # silence-based stopping instead of a fixed recording length.
    def can_handle(self, query: str, context: dict) -> bool:
        return self._ready and query.lower().strip().split(" ")[0] == "voice"

    def handle(self, query: str, context: dict) -> str:
        parts = query.strip().split()
        max_seconds = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else MAX_RECORD_SECONDS
        self.run_conversation_turn(max_seconds=max_seconds)
        return ""  # the turn speaks its own response, nothing more to print

    # ── The actual conversation turn -- called by wake_word.py's ──
    #    on_wake callback, or manually via the 'voice' command
    def run_conversation_turn(self, max_seconds: int = MAX_RECORD_SECONDS):
        if not self._ready:
            print("     Voice: module not ready -- check the pip installs above.")
            return
        if not self._query_handler:
            print("     Voice: no query handler wired up -- call set_query_handler() in main.py first.")
            return

        audio = self._record_until_silence(max_seconds)
        if audio is None or len(audio) < SAMPLE_RATE * 0.3:
            return  # nothing said, treat as a no-op

        text = self._transcribe(audio)
        if not text or not text.strip():
            return

        print(f"     \U0001f3a4 Aapne kaha: {text}")
        response = self._query_handler(text)
        if not response:
            return
        self._speak(response)

        # stay in conversation mode for a bit -- no wake word needed
        # for a natural follow-up
        deadline = time.time() + FOLLOWUP_LISTEN_SECONDS
        while time.time() < deadline:
            remaining = deadline - time.time()
            follow_audio = self._record_until_silence(max_seconds, quick_timeout=remaining)
            if follow_audio is None or len(follow_audio) < SAMPLE_RATE * 0.3:
                break
            follow_text = self._transcribe(follow_audio)
            if not follow_text or not follow_text.strip():
                break
            print(f"     \U0001f3a4 Aapne kaha: {follow_text}")
            follow_response = self._query_handler(follow_text)
            if not follow_response:
                break
            self._speak(follow_response)
            deadline = time.time() + FOLLOWUP_LISTEN_SECONDS

    # ── Recording that stops when you stop talking, not on a timer ──
    def _record_until_silence(self, max_seconds: int, quick_timeout: float = None):
        chunk_samples = int(SAMPLE_RATE * 0.08)  # 80ms chunks
        silence_run = 0
        heard_speech = False
        buf = []
        start = time.time()
        timeout = quick_timeout if quick_timeout is not None else max_seconds

        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16') as stream:
                while time.time() - start < timeout and time.time() - start < max_seconds:
                    data, _ = stream.read(chunk_samples)
                    buf.append(data.copy())
                    rms = np.sqrt(np.mean(data.astype(np.float64) ** 2))
                    if rms > SILENCE_THRESHOLD:
                        heard_speech = True
                        silence_run = 0
                    else:
                        silence_run += 1
                    if heard_speech and silence_run > SILENCE_CHUNKS_TO_STOP:
                        break
        except Exception as e:
            print(f"     Voice: recording error -- {e}")
            return None

        if not heard_speech:
            return None
        return np.concatenate(buf).flatten()

    # ── STT ──────────────────────────────────────────────────────
    def _transcribe(self, audio: np.ndarray) -> str:
        global _WHISPER_MODEL
        if not _WHISPER_OK:
            return ""
        if _WHISPER_MODEL is None:
            print("     Voice: Whisper model load ho raha hai (pehli baar thoda time lega)...")
            _WHISPER_MODEL = whisper.load_model("small")
        audio_float = audio.astype(np.float32) / 32768.0
        result = _WHISPER_MODEL.transcribe(audio_float, fp16=False)
        return result.get("text", "").strip()

    # ── TTS with language-aware voice + barge-in interrupt ───────────
    def _speak(self, text: str) -> bool:
        """Returns True if the user talked over it (barge-in)."""
        text = self._clean_for_speech(text)
        if not text:
            return False

        self._interrupt_flag.clear()
        monitor_stop = threading.Event()
        monitor_thread = threading.Thread(target=self._monitor_for_interrupt, args=(monitor_stop,), daemon=True)
        monitor_thread.start()
        try:
            if TTS_ENGINE == "edge" and _EDGE_TTS_OK and _PYGAME_OK:
                self._speak_edge(text)
            elif _PYTTSX3_OK:
                self._speak_pyttsx3(text)
            else:
                print(f"     Voice (no TTS available): {text}")
        finally:
            monitor_stop.set()
            monitor_thread.join(timeout=0.5)
        return self._interrupt_flag.is_set()

    def _clean_for_speech(self, text: str) -> str:
        text = re.sub(r'[\U0001F300-\U0001FAFF\u2600-\u27BF]', '', text)  # emoji
        text = re.sub(r'[*_`#]', '', text)  # markdown-ish symbols that read weird aloud
        return text.strip()

    def _pick_voice(self, text: str) -> str:
        words = re.findall(r'[a-zA-Z]+', text.lower())
        if not words:
            return VOICE_ENGLISH
        hindi_hits = sum(1 for w in words if w in HINDI_MARKERS)
        return VOICE_HINDI if (hindi_hits / len(words)) > 0.15 else VOICE_ENGLISH

    def _speak_edge(self, text: str):
        voice = self._pick_voice(text)
        try:
            asyncio.run(edge_tts.Communicate(text, voice).save(TTS_TEMP_PATH))
        except Exception as e:
            print(f"     Voice: Edge TTS error -- {e} (internet chal raha hai?)")
            return
        try:
            pygame.mixer.music.load(TTS_TEMP_PATH)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if self._interrupt_flag.is_set():
                    pygame.mixer.music.stop()
                    break
                time.sleep(0.05)
        except Exception as e:
            print(f"     Voice: playback error -- {e}")

    def _speak_pyttsx3(self, text: str):
        if self._pyttsx3_engine is None:
            self._pyttsx3_engine = pyttsx3.init()
        self._pyttsx3_engine.say(text)
        self._pyttsx3_engine.runAndWait()
        # pyttsx3's runAndWait() is blocking and doesn't expose a clean
        # mid-utterance stop() on every platform -- interrupt support
        # here is best-effort; edge_tts+pygame is the reliable path

    # ── Barge-in: listen for you talking WHILE it's talking ────────────
    def _monitor_for_interrupt(self, stop_signal: threading.Event):
        # Safe to open the mic here: wake_word.py is paused for the
        # entire conversation turn (see wake_word.py), so nothing else
        # is competing for the audio device right now.
        try:
            chunk_samples = int(SAMPLE_RATE * 0.1)
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16') as stream:
                while not stop_signal.is_set():
                    data, _ = stream.read(chunk_samples)
                    rms = np.sqrt(np.mean(data.astype(np.float64) ** 2))
                    if rms > SILENCE_THRESHOLD * 1.5:  # a bit higher bar than
                        self._interrupt_flag.set()      # normal silence detection
                        break
        except Exception:
            pass
