# ============================================================
#  ALTROS Module: Wake Word (background, always-on)
#  Porcupine listens continuously for the wake word without
#  recording or transcribing anything until it actually hears
#  it -- this is what makes voice mode "work in the background"
#  instead of needing you to type 'voice' first.
#
#  pip install pvporcupine pvrecorder
#  Free PORCUPINE_ACCESS_KEY: https://console.picovoice.ai
#  (same key/setup your own build guide already documents)
# ============================================================

import threading
import time

try:
    import pvporcupine
    from pvrecorder import PvRecorder
    _PORCUPINE_OK = True
except ImportError:
    _PORCUPINE_OK = False


class WakeWordModule:
    """Compatibility stub, not a reimplementation.

    Your main.py does `from modules.wake_word import WakeWordModule,
    WakeWordListener` and later `wake_word_mod.start(callback=...)` as
    a FALLBACK if the new WakeWordListener below fails to start (see
    main.py -- it's gated on `new_wake_word_started`). I never received
    your original wake_word.py, so I can't reproduce whatever your
    actual old wake-word logic did. This stub exists purely so the
    import and the fallback check don't crash: it reports itself as
    not-ready, so that fallback path is simply skipped and
    WakeWordListener (the real, working listener) does all the work.

    If you want the fallback to be a genuine second implementation
    rather than a no-op, share your original wake_word.py and I'll
    merge it in properly instead of guessing at it.
    """
    name = "wake_word"
    description = "Compatibility stub -- see WakeWordListener for the real background listener"

    def __init__(self):
        self._ready = False

    def on_enable(self):
        pass  # intentionally inert -- see class docstring

    def can_handle(self, query, context):
        return False

    def handle(self, query, context):
        return ""

    def start(self, callback=None):
        pass  # no-op: only reached if WakeWordListener failed to start


class WakeWordListener:
    """Runs Porcupine in a background thread. Calls on_wake() (no
    args) whenever the wake word is heard.

    pause()/resume() fully stop/restart the underlying mic stream
    (not just a flag) -- during an actual conversation turn,
    voice.py needs the microphone for itself, and two libraries
    both holding the audio device open is a reliable way to get
    silent recordings or a crash. Only one thing reads the mic at
    a time: Porcupine while idle, sounddevice during a turn.
    """

    def __init__(self, access_key: str, keyword: str, on_wake):
        self.access_key = access_key
        self.keyword = keyword
        self.on_wake = on_wake
        self._porcupine = None
        self._recorder = None
        self._thread = None
        self._stop_signal = threading.Event()
        self._paused = threading.Event()
        self._ready = False

    def start(self):
        if not _PORCUPINE_OK:
            print("     \u26a0\ufe0f pvporcupine/pvrecorder missing -- 'pip install pvporcupine pvrecorder'")
            return
        if not self.access_key or self.access_key == "your_key_here":
            print("     \u26a0\ufe0f PORCUPINE_ACCESS_KEY config.py mein set nahi hai -- https://console.picovoice.ai se le lo")
            return
        try:
            self._porcupine = pvporcupine.create(access_key=self.access_key, keywords=[self.keyword])
            self._recorder = PvRecorder(device_index=-1, frame_length=self._porcupine.frame_length)
            self._recorder.start()
        except Exception as e:
            print(f"     \u26a0\ufe0f Wake word init error -- {e}")
            return
        self._ready = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"     \u2705 Wake word listening in background ('{self.keyword}')")

    def pause(self):
        """Release the mic -- called right before a conversation turn
        starts recording."""
        if not self._ready:
            return
        self._paused.set()
        try:
            self._recorder.stop()
        except Exception:
            pass

    def resume(self):
        """Reclaim the mic -- called once a conversation turn (including
        any follow-ups) is fully done."""
        if not self._ready:
            return
        try:
            self._recorder.start()
        except Exception:
            pass
        self._paused.clear()

    def stop(self):
        self._stop_signal.set()
        if self._recorder:
            try:
                self._recorder.stop()
                self._recorder.delete()
            except Exception:
                pass
        if self._porcupine:
            try:
                self._porcupine.delete()
            except Exception:
                pass

    def _loop(self):
        while not self._stop_signal.is_set():
            if self._paused.is_set():
                time.sleep(0.1)
                continue
            try:
                pcm = self._recorder.read()
                result = self._porcupine.process(pcm)
                if result >= 0:
                    self.pause()
                    try:
                        self.on_wake()
                    except Exception as e:
                        print(f"     Wake word callback error -- {e}")
                    self.resume()
            except Exception:
                time.sleep(0.1)
