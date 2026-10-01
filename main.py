#!/usr/bin/env python3
# ============================================================
# ALTROS — Main Entry Point v2.0
# Thinking Engine + 3-Layer Memory + Autonomy
# ============================================================

import sys
import os
import importlib
import inspect

sys.path.insert(0, os.path.dirname(__file__))

# ============================================================
# CORE SYSTEMS — DO NOT CHANGE
# ============================================================

from core.memory import MemorySystem
from core.brain import Brain
from core.thinking import ThinkingEngine
from core.router import Router, ModuleManager

# ============================================================
# EXISTING WORKING MODULES
# ============================================================

from modules.chat import ChatModule
from modules.knowledge import KnowledgeModule
from modules.voice import VoiceModule
from modules.wake_word import WakeWordModule, WakeWordListener
from modules.internet import InternetModule
from modules.pc_control import PCControlModule
from modules.server import ServerModule
from modules.autonomy import AutonomyModule
from modules.instagram import InstagramModule
from modules.gmail import GmailModule

# ============================================================
# CONFIG
# ============================================================

import config
from config import ASSISTANT_NAME, USER_NAME, MODULES_ENABLED


# ============================================================
# MODULE LOADER
# ============================================================

def load_extra_modules(mm, already_loaded):
    """
    Loads additional modules enabled in config.py.

    Existing working modules are handled explicitly above.
    This loader searches the corresponding modules/*.py file
    for a BaseModule subclass.

    future_modules.py is intentionally skipped because it
    contains placeholder/stub classes, not FutureModulesModule.
    """

    try:
        from modules.base import BaseModule
    except Exception as e:
        print(f"⚠️ BaseModule load failed: {e}")
        return

    # These are already explicitly loaded above.
    known_modules = {
        "chat",
        "knowledge",
        "voice",
        "wake_word",
        "internet",
        "pc_control",
        "server",
        "autonomy",
        "instagram",
        "gmail",
        "base",
        "future_modules",
    }

    # Modules which should NOT be dynamically loaded.
    # future_modules.py only contains old placeholder classes.
    skip_modules = {
        "base",
        "future_modules",
        "__init__",
    }

    for module_name, enabled in MODULES_ENABLED.items():

        if not enabled:
            continue

        if module_name in known_modules:
            continue

        if module_name in skip_modules:
            continue

        try:
            module = importlib.import_module(
                f"modules.{module_name}"
            )

        except ModuleNotFoundError as e:
            print(
                f"  ⚠️ {module_name}: module/file not found — {e}"
            )
            continue

        except Exception as e:
            print(
                f"  ⚠️ {module_name}: import failed — {e}"
            )
            continue

        loaded = False

        # Find BaseModule subclasses.
        for class_name, cls in inspect.getmembers(
            module,
            inspect.isclass
        ):

            if cls is BaseModule:
                continue

            try:
                is_module = issubclass(cls, BaseModule)
            except TypeError:
                is_module = False

            if not is_module:
                continue

            # Don't instantiate imported BaseModule subclasses
            # that belong to another module.
            if cls.__module__ != module.__name__:
                continue

            try:
                instance = cls()

                # Avoid duplicate registration.
                instance_name = getattr(
                    instance,
                    "name",
                    module_name
                )

                if instance_name in already_loaded:
                    continue

                mm.register(instance)
                already_loaded.add(instance_name)

                print(
                    f"  ✓ {instance_name}"
                )

                loaded = True
                break

            except Exception as e:
                print(
                    f"  ⚠️ {module_name}: "
                    f"{class_name} could not start — {e}"
                )

        if not loaded:
            print(
                f"  ⚠️ {module_name}: "
                f"no usable BaseModule class found"
            )


# ============================================================
# BOOT
# ============================================================

def boot():

    print(f"\n{'=' * 52}")
    print(f"  {ASSISTANT_NAME} v2.0 — Booting...")
    print(f"{'=' * 52}")

    # --------------------------------------------------------
    # Core systems
    # --------------------------------------------------------

    memory = MemorySystem()

    brain = Brain(memory)

    thinker = ThinkingEngine(brain)

    brain.set_thinking_engine(thinker)

    # --------------------------------------------------------
    # Module manager
    # --------------------------------------------------------

    mm = ModuleManager()

    print("\nLoading modules:")

    # --------------------------------------------------------
    # Existing modules
    # --------------------------------------------------------

    internet_mod = InternetModule()
    pc_mod = PCControlModule()
    knowledge_mod = KnowledgeModule()
    voice_mod = VoiceModule()
    wake_word_mod = WakeWordModule()
    server_mod = ServerModule()
    autonomy_mod = AutonomyModule()
    instagram_mod = InstagramModule()
    gmail_mod = GmailModule()

    # --------------------------------------------------------
    # Register existing modules
    # --------------------------------------------------------

    already_loaded = set()

    mm.register(internet_mod)
    already_loaded.add("internet")

    mm.register(pc_mod)
    already_loaded.add("pc_control")

    mm.register(knowledge_mod)
    already_loaded.add("knowledge")

    mm.register(voice_mod)
    already_loaded.add("voice")

    mm.register(wake_word_mod)
    already_loaded.add("wake_word")

    mm.register(autonomy_mod)
    already_loaded.add("autonomy")

    mm.register(instagram_mod)
    already_loaded.add("instagram")

    mm.register(gmail_mod)
    already_loaded.add("gmail")

    mm.register(server_mod)
    already_loaded.add("server")

    # Chat
    chat_mod = ChatModule()
    mm.register(chat_mod)
    already_loaded.add("chat")

    # --------------------------------------------------------
    # Load remaining enabled modules automatically
    # --------------------------------------------------------

    load_extra_modules(
        mm,
        already_loaded
    )

    # --------------------------------------------------------
    # Router
    # --------------------------------------------------------

    router = Router(
        brain,
        memory,
        mm
    )

    # --------------------------------------------------------
    # Ollama connection
    # --------------------------------------------------------

    print()

    if brain.check_connection():

        print(
            f"  🧠 Ollama connected — model: {brain.model}"
        )

    else:

        print(
            "  ⚠️ Ollama not running. "
            "Run: ollama serve"
        )

    # --------------------------------------------------------
    # Active modules
    # --------------------------------------------------------

    active = mm.list_active()

    print(
        f"\n  Active modules: {', '.join(active)}"
    )

    print(
        "\n  Commands: "
        "help | exit | clear | memory | books | tasks | voice"
    )

    print(f"{'=' * 52}\n")

    return (
        memory,
        brain,
        router,
        knowledge_mod,
        voice_mod,
        wake_word_mod,
        server_mod,
        autonomy_mod
    )


# ============================================================
# HELP
# ============================================================

def show_help():

    print("""
COMMANDS:

  exit
      ALTROS band karo

  clear
      Session clear karo

  memory
      Profile dekho

  remember X Y
      Kuch yaad karwao

  books
      Knowledge base count

  tasks
      Pending tasks dekho

  voice
      Mic se baat karo (5 sec)

  voice 10
      10 sec record

  help
      Ye menu
""")


# ============================================================
# COMMAND HANDLER
# ============================================================

def handle_command(
    user_input,
    memory,
    knowledge_mod,
    voice_mod,
    router,
    autonomy_mod
):

    cmd = user_input.lower().strip()

    # --------------------------------------------------------
    # EXIT
    # --------------------------------------------------------

    if cmd == "exit":

        print(
            f"\nALTROS: Chalte hain, "
            f"{USER_NAME}. Take care! 👋\n"
        )

        memory.clear_session()

        return True, True

    # --------------------------------------------------------
    # HELP
    # --------------------------------------------------------

    if cmd == "help":

        show_help()

        return True, False

    # --------------------------------------------------------
    # CLEAR
    # --------------------------------------------------------

    if cmd == "clear":

        memory.clear_session()

        print(
            "ALTROS: Session clear. Fresh start.\n"
        )

        return True, False

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    if cmd == "memory":

        summary = memory.get_profile_summary()

        print(
            f"\nALTROS:\n"
            f"{summary if summary else 'Abhi kuch yaad nahi.'}\n"
        )

        return True, False

    # --------------------------------------------------------
    # TASKS
    # --------------------------------------------------------

    if cmd == "tasks":

        tasks = (
            autonomy_mod.get_pending_tasks()
            if autonomy_mod._ready
            else []
        )

        if tasks:

            print("\nALTROS: Pending tasks:")

            for task in tasks:

                print(
                    f"  [{task.get('priority', 5)}/10] "
                    f"{task['title']}"
                )

        else:

            print(
                "\nALTROS: Koi pending task nahi. "
                "Clean slate!\n"
            )

        return True, False

    # --------------------------------------------------------
    # BOOKS
    # --------------------------------------------------------

    if cmd == "books":

        try:

            count = (
                knowledge_mod._collection.count()
                if knowledge_mod._ready
                else 0
            )

            print(
                f"\nALTROS: Knowledge base mein "
                f"{count} chunks hain.\n"
            )

        except Exception:

            print(
                "ALTROS: Knowledge module ready nahi.\n"
            )

        return True, False

    # --------------------------------------------------------
    # REMEMBER
    # --------------------------------------------------------

    if cmd.startswith("remember "):

        parts = user_input[9:].split(" ", 1)

        if len(parts) == 2:

            memory.remember(
                parts[0],
                parts[1]
            )

            print(
                f"ALTROS: Yaad kar liya — "
                f"{parts[0]}: {parts[1]}\n"
            )

        return True, False

    # --------------------------------------------------------
    # VOICE
    # --------------------------------------------------------

    if cmd.startswith("voice"):

        if not MODULES_ENABLED.get("voice"):

            print(
                "ALTROS: Voice disabled. "
                "config.py mein enable karo.\n"
            )

            return True, False

        parts = cmd.split()

        duration = (
            int(parts[1])
            if len(parts) > 1 and parts[1].isdigit()
            else 5
        )

        spoken = voice_mod.listen(
            duration=duration
        )

        if not spoken:

            print(
                "ALTROS: Kuch sunai nahi diya.\n"
            )

            return True, False

        memory.extract_and_store(spoken)

        response = router.route(spoken)

        memory.add_message(
            "user",
            spoken
        )

        memory.add_message(
            "assistant",
            response
        )

        voice_mod.speak(response)

        return True, False

    return False, False


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # --add-book
    # --------------------------------------------------------

    if (
        len(sys.argv) >= 3
        and sys.argv[1] == "--add-book"
    ):

        book_path = sys.argv[2]

        (
            memory,
            brain,
            router,
            knowledge_mod,
            voice_mod,
            ww,
            server,
            autonomy
        ) = boot()

        knowledge_mod.add_document(
            book_path
        )

        return

    # --------------------------------------------------------
    # Voice mode
    # --------------------------------------------------------

    voice_mode = "--voice" in sys.argv

    (
        memory,
        brain,
        router,
        knowledge_mod,
        voice_mod,
        wake_word_mod,
        server_mod,
        autonomy_mod
    ) = boot()

    # --------------------------------------------------------
    # Background wake-word listener
    # --------------------------------------------------------

    new_wake_word_started = False

    if not voice_mode:

        try:

            voice = voice_mod

            if hasattr(
                voice,
                "on_enable"
            ):

                voice.on_enable()

            if hasattr(
                voice,
                "set_query_handler"
            ):

                voice.set_query_handler(
                    lambda text: router.route(text)
                )

            if (
                MODULES_ENABLED.get("wake_word")
                and getattr(
                    config,
                    "PORCUPINE_ACCESS_KEY",
                    None
                )
            ):

                ww_keyword = getattr(
                    config,
                    "WAKE_WORD",
                    None
                )

                try:

                    wake_word = WakeWordListener(
                        access_key=config.PORCUPINE_ACCESS_KEY,
                        keyword=ww_keyword,
                        on_wake=lambda:
                            voice.run_conversation_turn()
                            if hasattr(
                                voice,
                                "run_conversation_turn"
                            )
                            else None
                    )

                    wake_word.start()

                    new_wake_word_started = True

                except Exception:

                    pass

        except Exception:

            pass

    # --------------------------------------------------------
    # Server
    # --------------------------------------------------------

    if MODULES_ENABLED.get("server"):

        try:

            server_mod.set_dependencies(
                router,
                memory,
                voice_mod
            )

            server_mod.start()

        except NotImplementedError:

            print(
                "⚠️ Server module is enabled "
                "but not implemented."
            )

        except Exception as e:

            print(
                f"⚠️ Server startup failed: {e}"
            )

        try:

            import ngrok

            listener = ngrok.forward(
                8000,
                authtoken_from_env=False
            )

            print(
                f"📱 Phone access URL: "
                f"{listener.url()}"
            )

        except Exception:

            print(
                "📱 Phone access: "
                "http://localhost:8000"
            )

    # --------------------------------------------------------
    # Autonomy
    # --------------------------------------------------------

    if (
        MODULES_ENABLED.get("autonomy")
        and autonomy_mod._ready
    ):

        def reminder_callback(msg):

            print(
                f"\n⏰ ALTROS: {msg}\n"
            )

        autonomy_mod.set_callback(
            reminder_callback
        )

        autonomy_mod.start()

    # --------------------------------------------------------
    # Old-style wake word fallback
    # --------------------------------------------------------

    if (
        not new_wake_word_started
        and MODULES_ENABLED.get("wake_word")
        and wake_word_mod._ready
    ):

        def activate_voice():

            spoken = voice_mod.listen(
                duration=6
            )

            if spoken:

                memory.extract_and_store(
                    spoken
                )

                response = router.route(
                    spoken
                )

                memory.add_message(
                    "user",
                    spoken
                )

                memory.add_message(
                    "assistant",
                    response
                )

                voice_mod.speak(
                    response
                )

        try:

            wake_word_mod.start(
                callback=activate_voice
            )

        except Exception as e:

            print(
                f"⚠️ Wake-word startup failed: {e}"
            )

    # --------------------------------------------------------
    # Keyboard shortcut
    # --------------------------------------------------------

    try:

        import keyboard

        def activate_voice_kb():

            spoken = voice_mod.listen(
                duration=6
            )

            if spoken:

                memory.extract_and_store(
                    spoken
                )

                response = router.route(
                    spoken
                )

                memory.add_message(
                    "user",
                    spoken
                )

                memory.add_message(
                    "assistant",
                    response
                )

                voice_mod.speak(
                    response
                )

        keyboard.add_hotkey(
            "ctrl+alt+a",
            activate_voice_kb
        )

        print(
            "⌨️ Shortcut: Ctrl+Alt+A"
        )

    except Exception:

        pass

    # --------------------------------------------------------
    # Daily briefing
    # --------------------------------------------------------

    if autonomy_mod._ready:

        try:

            briefing = (
                autonomy_mod.get_daily_briefing()
            )

            print(
                f"\n📋 {briefing}\n"
            )

        except Exception:

            pass

    # --------------------------------------------------------
    # Voice mode
    # --------------------------------------------------------

    if voice_mode:

        print(
            "ALTROS: Voice mode on! "
            "Ctrl+C se band karo.\n"
        )

        voice_mod.speak(
            "ALTROS ready hai. Bolo Manish."
        )

        while True:

            try:

                spoken = voice_mod.listen(
                    duration=6
                )

                if not spoken:
                    continue

                if (
                    "stop" in spoken.lower()
                    or "band" in spoken.lower()
                ):

                    voice_mod.speak(
                        "Theek hai. Chalte hain."
                    )

                    break

                memory.extract_and_store(
                    spoken
                )

                response = router.route(
                    spoken
                )

                memory.add_message(
                    "user",
                    spoken
                )

                memory.add_message(
                    "assistant",
                    response
                )

                voice_mod.speak(
                    response
                )

            except KeyboardInterrupt:

                print(
                    "\nALTROS: Chalte hain. 👋\n"
                )

                memory.clear_session()

                break

        return

    # --------------------------------------------------------
    # Main chat loop
    # --------------------------------------------------------

    while True:

        try:

            user_input = input(
                f"{USER_NAME}: "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print(
                f"\n\nALTROS: Chalte hain, "
                f"{USER_NAME}! 👋\n"
            )

            memory.clear_session()

            break

        if not user_input:
            continue

        handled, should_exit = handle_command(
            user_input,
            memory,
            knowledge_mod,
            voice_mod,
            router,
            autonomy_mod
        )

        if should_exit:
            break

        if handled:
            continue

        memory.extract_and_store(
            user_input
        )

        response = router.route(
            user_input
        )

        memory.add_message(
            "user",
            user_input
        )

        memory.add_message(
            "assistant",
            response
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()