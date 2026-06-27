"""
core/brain.py — JARVIS OMEGA V10  ★ FIXED ★
ROOT CAUSES FIXED:
  1. "All models timeout" — race() used ThreadPoolExecutor inside a lambda closure
     which caused the inner lambda to capture a stale `fn` reference.
     Fix: Call callables directly, not via lambda wrapping.
  2. Ollama connect_timeout was 3s — too short if Ollama is loading a model cold.
     Fix: connect_timeout = 8s, read_timeout = 120s.
  3. The race() future.result(timeout=0) raised immediately on slow results.
     Fix: result(timeout=None) — let the thread finish naturally.
  4. Web search triggered even for simple greetings, adding latency.
     Fix: tighter needs_search() guard.
  5. `concurrent.futures` race never returned when all futures raised exceptions
     because CancelledError was silently swallowed.
     Fix: proper exception handling and early return.
"""
from __future__ import annotations

import os
import re
import json
import time
import sqlite3
import threading
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent

try:
    import requests
    REQ = True
except ImportError:
    REQ = False
    print("[BRAIN] WARNING: requests not installed — pip install requests")

# ── Web Search (FREE — DuckDuckGo) ────────────────────────────────────────────
try:
    from duckduckgo_search import DDGS
    DDG = True
except ImportError:
    DDG = False

# ═══════════════════════════════════════════════════════════════════════════
# MEMORY
# ═══════════════════════════════════════════════════════════════════════════
class Memory:
    def __init__(self):
        db = BASE / "data" / "memory.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn  = sqlite3.connect(str(db), check_same_thread=False)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS conversations(
            id INTEGER PRIMARY KEY, user_msg TEXT, ai_msg TEXT, ts TEXT)""")
        self.conn.commit()
        self.short_term: List[dict] = []

    def save(self, u: str, a: str):
        with self._lock:
            self.conn.execute(
                "INSERT INTO conversations(user_msg,ai_msg,ts) VALUES(?,?,?)",
                (u, a, datetime.now().isoformat()))
            self.conn.execute(
                "DELETE FROM conversations WHERE id NOT IN "
                "(SELECT id FROM conversations ORDER BY id DESC LIMIT 300)")
            self.conn.commit()
        self.short_term.append({"user": u, "assistant": a})
        if len(self.short_term) > 14:
            self.short_term = self.short_term[-14:]

    def context(self) -> List[dict]:
        return self.short_term[-8:]


# ═══════════════════════════════════════════════════════════════════════════
# INSTANT COMMAND ROUTER  (zero latency — no Ollama needed)
# ═══════════════════════════════════════════════════════════════════════════
_INSTANT = {
    r'\b(time|waqt|samay|kitne baje|what time)\b':
        lambda: f"Sir, abhi {datetime.now():%I:%M %p} baj rahe hain.",
    r'\b(aaj|today|aaj ki date|what.*date|date kya)\b':
        lambda: f"Aaj {datetime.now():%A, %d %B %Y} hai, Sir.",
    r'\b(hello|hi|hey|namaste|hola|salaam)\b':
        lambda: _greet(),
    r'\b(kaisa|how are you|theek ho|sab theek)\b':
        lambda: "Main bilkul theek hoon, Sir! Aap batao, kya kaam hai?",
    r'\b(shukriya|thanks|thank you|dhanyawad)\b':
        lambda: "Koi baat nahi, Sir. Aur kuch kaam ho toh batao.",
    r'\b(mera naam|my name|naam kya)\b':
        lambda: f"Aapka naam {_SETTINGS.get('user_name', 'Sir')} hai.",
    r'\b(jarvis version|version)\b':
        lambda: "Main JARVIS Omega V10 hoon, Sir. Multi-model Ollama architecture.",
}

_SETTINGS: dict = {}


def _greet() -> str:
    h = datetime.now().hour
    t = "Good morning" if h < 12 else ("Good afternoon" if h < 17 else "Good evening")
    return f"{t}, Sir! JARVIS V10 hazir hai. Kya kaam hai aapka?"


def instant_route(text: str) -> Optional[str]:
    for pat, fn in _INSTANT.items():
        if re.search(pat, text, re.I):
            return fn()
    return None


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════
SYS = """You are JARVIS, an AI assistant running on a Windows 11 laptop.
User: {name}. Time: {time}.

LANGUAGE RULE (CRITICAL):
- Reply ONLY in Hinglish — Hindi words written in Roman/English script.
- Example: "Sir, main abhi Chrome khol deta hoon. Thodi der mein khul jayega."
- NEVER use Devanagari script. Roman letters only.
- Short replies — 1-3 sentences max. Address user as "Sir".

When performing a computer action, embed EXACTLY this JSON (no extra text around it):
{{"action":"ACTION_NAME","target":"TARGET_VALUE"}}

ACTIONS:
open_app, close_app, minimize_app, maximize_app
search_web, search_youtube, play_music, open_url, open_browser
mouse_move, mouse_click, double_click, right_click
mouse_scroll_up, mouse_scroll_down
type_text, hotkey
screenshot, read_screen, find_and_click
focus_window, list_windows
volume_up, volume_down, mute, lock_screen, system_info, list_processes
save_file, save_as
"""


def _sys_prompt(name: str) -> str:
    return SYS.format(name=name, time=datetime.now().strftime("%I:%M %p, %A"))


# ═══════════════════════════════════════════════════════════════════════════
# ACTION EXTRACTOR
# ═══════════════════════════════════════════════════════════════════════════
def extract_actions(response: str) -> List[dict]:
    actions = []
    for match in re.finditer(r'\{[^{}]*?"action"\s*:\s*"[^"]+?"[^{}]*?\}', response, re.DOTALL):
        try:
            obj = json.loads(match.group())
            if "action" in obj and obj["action"]:
                actions.append(obj)
        except json.JSONDecodeError:
            pass

    if not actions:
        for match in re.finditer(r'"action"\s*:\s*"([^"]+)"', response):
            action_name = match.group(1)
            seg = response[match.start():match.start() + 200]
            tm  = re.search(r'"target"\s*:\s*"([^"]*)"', seg)
            target = tm.group(1) if tm else ""
            actions.append({"action": action_name, "target": target})

    if actions:
        print(f"[BRAIN] Extracted {len(actions)} action(s): {[a['action'] for a in actions]}")
    return actions


def strip_actions(response: str) -> str:
    cleaned = re.sub(r'\s*\{[^{}]*?"action"[^{}]*?\}\s*', ' ', response, flags=re.DOTALL)
    return re.sub(r'\s+', ' ', cleaned).strip()


# ═══════════════════════════════════════════════════════════════════════════
# WEB SEARCH (DuckDuckGo — FREE, no API key)
# ═══════════════════════════════════════════════════════════════════════════
def web_search(query: str, n: int = 4) -> str:
    if not DDG:
        return ""
    try:
        with DDGS() as d:
            results = list(d.text(query, max_results=n))
        if not results:
            return ""
        return "\n".join(
            f"• {r.get('title','')}: {r.get('body','')[:120]}"
            for r in results
        )
    except Exception as e:
        print(f"[SEARCH] DuckDuckGo error: {e}")
        return ""


def needs_search(text: str) -> bool:
    # Never search for these — they are instant responses
    skip = [
        r'\b(time|waqt|samay|kitne baje)\b',
        r'\b(today|aaj|date)\b',
        r'\b(hello|hi|hey|namaste|thanks|shukriya)\b',
        r'\b(how are you|kaisa)\b',
    ]
    for pat in skip:
        if re.search(pat, text, re.I):
            return False

    triggers = [
        "search", "latest", "news", "price", "weather", "who is", "what is",
        "how to", "current", "stock", "score", "result", "match", "movie",
        "release", "information", "about", "meaning", "explain",
    ]
    tl = text.lower()
    return any(t in tl for t in triggers)


# ═══════════════════════════════════════════════════════════════════════════
# OLLAMA CALLER  ★ FIXED ★
#   - connect_timeout = 8s  (was 3s — too short for cold model load)
#   - read_timeout    = 120s (was 30s — not enough for large models)
#   - Proper error messages so we know WHY it failed
# ═══════════════════════════════════════════════════════════════════════════
def call_ollama(url: str, model: str, msgs: list, tok: int = 400) -> Optional[str]:
    """Call Ollama /api/chat. Returns content string or None."""
    if not REQ or not url or not model:
        return None
    try:
        body = {
            "model": model,
            "messages": msgs,
            "stream": False,
            "options": {
                "num_predict": tok,
                "temperature": 0.7,
                "top_p": 0.9,
            }
        }
        r = requests.post(
            f"{url}/api/chat",
            json=body,
            timeout=(8, 120)   # (connect_timeout, read_timeout)
        )
        if r.status_code == 200:
            content = r.json().get("message", {}).get("content", "").strip()
            return content if content else None
        print(f"[OLLAMA] HTTP {r.status_code} for model '{model}': {r.text[:120]}")
    except requests.exceptions.ConnectionError:
        print(f"[OLLAMA] ❌ Connection refused at {url} — run: ollama serve")
    except requests.exceptions.ConnectTimeout:
        print(f"[OLLAMA] ❌ Connect timeout — is Ollama slow to start?")
    except requests.exceptions.ReadTimeout:
        print(f"[OLLAMA] ❌ Read timeout — model '{model}' took >120s to respond")
    except Exception as e:
        print(f"[OLLAMA] ❌ Unexpected error: {type(e).__name__}: {e}")
    return None


# ═══════════════════════════════════════════════════════════════════════════
# CHECK OLLAMA IS RUNNING  (called at startup for early warning)
# ═══════════════════════════════════════════════════════════════════════════
def check_ollama_running(url: str) -> tuple[bool, list[str]]:
    """Returns (is_running, list_of_installed_model_names)."""
    if not REQ:
        return False, []
    try:
        r = requests.get(f"{url}/api/tags", timeout=(5, 10))
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return True, models
    except Exception:
        pass
    return False, []


# ═══════════════════════════════════════════════════════════════════════════
# SEQUENTIAL MODEL CALLER  ★ KEY FIX ★
#
# The old race() with ThreadPoolExecutor caused:
#   - Lambda closures capturing wrong variables
#   - future.result(timeout=0) raising immediately
#   - All "results" being None → "All models timeout"
#
# NEW approach: Try models ONE BY ONE in order of priority.
# The first model that returns a non-empty result wins.
# This is simpler, more reliable, and avoids all threading issues.
# With Ollama running locally, models respond in 2-15s — sequential is fine.
# ═══════════════════════════════════════════════════════════════════════════
def call_first_available(model_list: list[tuple[str, str, int]],
                         msgs: list,
                         global_timeout: float = 90.0) -> Optional[str]:
    """
    Try each (url, model_name, tok) in order.
    Returns the first non-empty response.
    Falls back to next model if one fails or times out.
    """
    deadline = time.time() + global_timeout
    for url, model, tok in model_list:
        if time.time() > deadline:
            print("[BRAIN] Global timeout reached across all models")
            break
        print(f"[BRAIN] Trying model: {model}")
        remaining = deadline - time.time()
        # Temporarily override timeout to remaining time
        result = _call_with_timeout(url, model, msgs, tok,
                                    min(remaining, 90.0))
        if result:
            print(f"[BRAIN] ✓ Got response from {model} ({len(result)} chars)")
            return result
        print(f"[BRAIN] ✗ {model} returned nothing — trying next")
    return None


def _call_with_timeout(url: str, model: str, msgs: list,
                       tok: int, timeout: float) -> Optional[str]:
    """Call Ollama with a per-call deadline."""
    if not REQ:
        return None
    try:
        body = {
            "model": model,
            "messages": msgs,
            "stream": False,
            "options": {"num_predict": tok, "temperature": 0.7, "top_p": 0.9}
        }
        connect_t = min(8.0, timeout * 0.1)
        read_t    = min(timeout - connect_t, 110.0)
        r = requests.post(
            f"{url}/api/chat",
            json=body,
            timeout=(connect_t, read_t)
        )
        if r.status_code == 200:
            content = r.json().get("message", {}).get("content", "").strip()
            return content or None
        print(f"[OLLAMA] HTTP {r.status_code}: {r.text[:80]}")
    except requests.exceptions.ConnectionError:
        print(f"[OLLAMA] Connection refused at {url}")
    except requests.exceptions.Timeout:
        print(f"[OLLAMA] Timeout on model '{model}'")
    except Exception as e:
        print(f"[OLLAMA] Error on '{model}': {type(e).__name__}: {e}")
    return None


# ═══════════════════════════════════════════════════════════════════════════
# MODEL PRIORITY LISTS per task
# ═══════════════════════════════════════════════════════════════════════════
class TaskRouter:
    def __init__(self, settings: dict):
        self.url    = settings.get("ollama_url", "http://localhost:11434")
        self.models = settings.get("V10_MODELS", {})

    def _m(self, key: str) -> str:
        """Get model name for key, fallback to llama3.2."""
        return self.models.get(key) or "llama3.2"

    def _entry(self, key: str, tok: int) -> tuple:
        return (self.url, self._m(key), tok)

    def for_chat(self)     -> list: return [self._entry("chat", 400),    self._entry("fast", 250)]
    def for_search(self)   -> list: return [self._entry("reasoning", 600), self._entry("chat", 400)]
    def for_screen(self)   -> list: return [self._entry("vision", 400),  self._entry("chat", 350)]
    def for_code(self)     -> list: return [self._entry("code", 800),    self._entry("chat", 400)]
    def for_creative(self) -> list: return [self._entry("creative", 600), self._entry("chat", 400)]


# ═══════════════════════════════════════════════════════════════════════════
# MAIN BRAIN
# ═══════════════════════════════════════════════════════════════════════════
class JarvisBrain:
    def __init__(self, settings: dict):
        global _SETTINGS
        self.settings   = settings
        _SETTINGS       = settings
        self.memory     = Memory()
        self.router     = TaskRouter(settings)
        self._screen_ctx= ""
        self.automation = None
        self.vision_enabled      = settings.get("V10_FEATURES", {}).get("vision_enabled", True)
        self.web_search_enabled  = settings.get("V10_FEATURES", {}).get("web_search_enabled", True)

        # Check Ollama at startup
        url = settings.get("ollama_url", "http://localhost:11434")
        ok, installed = check_ollama_running(url)
        if ok:
            print(f"[BRAIN] ✓ Ollama running | Installed models: {installed}")
            self._validate_models(installed)
        else:
            print(f"[BRAIN] ⚠ Ollama NOT running at {url}")
            print("[BRAIN]   → Open a terminal and run: ollama serve")

        print(f"[BRAIN] ✓ V10 Brain ready")
        print(f"[BRAIN]   Chat={self.router._m('chat')} | Fast={self.router._m('fast')}")
        print(f"[BRAIN]   Code={self.router._m('code')} | Creative={self.router._m('creative')}")
        print(f"[BRAIN]   Vision={self.router._m('vision')} | Reasoning={self.router._m('reasoning')}")

    def _validate_models(self, installed: list[str]):
        """Warn if a configured model is not installed."""
        needed = set(self.router.models.values())
        # Normalize: "llama3.2" matches "llama3.2:latest"
        inst_base = {m.split(":")[0] for m in installed} | set(installed)
        for m in needed:
            base = m.split(":")[0]
            if base not in inst_base and m not in installed:
                print(f"[BRAIN] ⚠ Model '{m}' NOT installed → run: ollama pull {m}")

    def _build_msgs(self, user_input: str) -> list:
        msgs = [{"role": "system",
                 "content": _sys_prompt(self.settings.get("user_name", "Sir"))}]
        for h in self.memory.context():
            msgs.append({"role": "user",      "content": h["user"]})
            msgs.append({"role": "assistant", "content": h["assistant"]})
        msgs.append({"role": "user", "content": user_input})
        return msgs

    def update_screen_context(self, text: str):
        self._screen_ctx = text[:500]

    def process(self, text: str, task_hint: str = "chat") -> Tuple[str, List[dict]]:
        t0 = time.time()

        # ── 1. Instant router (0ms, no Ollama) ───────────────────────────
        quick = instant_route(text)
        if quick:
            self.memory.save(text, quick)
            print(f"[BRAIN] instant {(time.time()-t0)*1000:.0f}ms")
            return quick, []

        # ── 2. Web search augmentation ────────────────────────────────────
        user_input = text
        if self.web_search_enabled and needs_search(text):
            print("[BRAIN] Running web search…")
            sr = web_search(text, n=4)
            if sr:
                user_input = f"{text}\n\n[Web results]\n{sr}"
                print(f"[BRAIN] Web search done ({len(sr)} chars)")

        # ── 3. Screen vision context ──────────────────────────────────────
        screen_triggers = ["screen", "dekho", "read screen", "click on",
                           "what is on", "screen pe", "dikhao", "kya dikha"]
        if any(t in text.lower() for t in screen_triggers) and self.vision_enabled:
            try:
                from vision.screen_vision import get_screen_reader
                reader = get_screen_reader(self.settings)
                screen_text = reader.read(use_ai=False)   # OCR only, no AI (faster)
                user_input += f"\n\n[Screen OCR]\n{screen_text[:600]}"
                task_hint = "screen"
                print(f"[BRAIN] Screen OCR injected ({len(screen_text)} chars)")
            except Exception as e:
                print(f"[BRAIN] Screen read error: {e}")

        if self._screen_ctx:
            user_input = f"[Screen context: {self._screen_ctx}]\n\n{user_input}"

        # ── 4. Auto-detect task type ──────────────────────────────────────
        tl = text.lower()
        if task_hint == "chat":
            if any(w in tl for w in ["code", "python", "script", "function", "program", "bug"]):
                task_hint = "code"
            elif any(w in tl for w in ["write", "essay", "story", "poem", "likhna", "creative"]):
                task_hint = "creative"
            elif any(w in tl for w in ["search", "find", "news", "latest", "who is", "what is", "explain"]):
                task_hint = "search"

        # ── 5. Pick model list ────────────────────────────────────────────
        model_list = {
            "screen":   self.router.for_screen,
            "search":   self.router.for_search,
            "code":     self.router.for_code,
            "creative": self.router.for_creative,
        }.get(task_hint, self.router.for_chat)()

        msgs = self._build_msgs(user_input)

        # ── 6. Call models sequentially (FIXED — no more race/timeout) ────
        print(f"[BRAIN] Task={task_hint} | Calling {len(model_list)} model(s)")
        raw = call_first_available(model_list, msgs, global_timeout=90.0)

        if not raw:
            print("[BRAIN] ❌ All models failed")
            ollama_ok, _ = check_ollama_running(
                self.settings.get("ollama_url", "http://localhost:11434"))
            if not ollama_ok:
                raw = ("Sir, Ollama chal nahi raha. "
                       "Ek terminal open karein aur likhen: ollama serve")
            else:
                raw = ("Sir, model response nahi diya. "
                       "Thoda wait karein — model load ho raha hoga.")

        # ── 7. Extract + clean ────────────────────────────────────────────
        actions = []
        try:
            actions = extract_actions(raw)
        except Exception as e:
            print(f"[BRAIN] Action extract error: {e}")

        try:
            clean = strip_actions(raw)
        except Exception:
            clean = raw

        clean = hindi_to_hinglish(clean)
        self.memory.save(text, clean)
        print(f"[BRAIN] Done in {time.time()-t0:.2f}s | {len(actions)} action(s)")
        return clean, actions

    def clear_history(self):
        self.memory.short_term.clear()


# ═══════════════════════════════════════════════════════════════════════════
# HINDI → HINGLISH CONVERTER
# ═══════════════════════════════════════════════════════════════════════════
_HM = {
    'नमस्ते':'namaste','धन्यवाद':'dhanyavaad','शुक्रिया':'shukriya',
    'हाँ':'haan','नहीं':'nahin','ठीक':'theek','बहुत':'bahut',
    'अच्छा':'achha','करो':'karo','करें':'karein','बताओ':'batao',
    'देखो':'dekho','खोलो':'kholo','बंद':'band','चालू':'chaalu',
    'क्या':'kya','कैसे':'kaise','कहाँ':'kahaan','कब':'kab',
    'क्यों':'kyun','कौन':'kaun','कितना':'kitna','मैं':'main',
    'आप':'aap','हम':'hum','वह':'woh','यह':'yeh','अभी':'abhi',
    'आज':'aaj','कल':'kal','सुबह':'subah','शाम':'shaam','रात':'raat',
    'हूँ':'hoon','है':'hai','हैं':'hain','था':'tha','होगा':'hoga',
    'गया':'gaya','रहा':'raha','और':'aur','या':'ya','लेकिन':'lekin',
    'के':'ke','की':'ki','का':'ka','में':'mein','पर':'par',
    'से':'se','को':'ko','ने':'ne','तो':'to','भी':'bhi',
    'सही':'sahi','काम':'kaam','नाम':'naam','बात':'baat',
    'मदद':'madad','जरूरत':'zaroorat','शुरू':'shuru','खत्म':'khatam',
    'सर':'Sir','दिखाओ':'dikhao','चलाओ':'chalaao',
}


def hindi_to_hinglish(text: str) -> str:
    for h, r in _HM.items():
        text = text.replace(h, r)
    # Mark any remaining Devanagari in brackets
    text = re.sub(r'[\u0900-\u097F]+', lambda m: f'[{m.group()}]', text)
    return text
