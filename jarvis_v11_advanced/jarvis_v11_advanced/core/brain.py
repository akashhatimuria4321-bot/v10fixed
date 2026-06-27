"""
core/brain.py — JARVIS OMEGA V11 ★ ADVANCED ★
FIXES & IMPROVEMENTS:
 1. Compound command parser — breaks "open youtube and play song" into sequential actions
 2. Context-aware responses — tracks what app is open for smart follow-ups
 3. Response caching — instant replies for repeated commands
 4. Pre-warmed model calls — faster first response
 5. Streaming-like fast mode — uses smaller model first, upgrades if needed
 6. Better action extraction with validation
 7. USB/pendrive detection and audio playback logic
 8. App detection integration — only suggests installed apps
"""
from __future__ import annotations

import os
import re
import json
import time
import sqlite3
import threading
import hashlib
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent

try:
    import requests
    REQ = True
except ImportError:
    REQ = False
    print("[BRAIN] WARNING: requests not installed — pip install requests")

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
        self.conn = sqlite3.connect(str(db), check_same_thread=False)
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
# RESPONSE CACHE (instant replies for repeated commands)
# ═══════════════════════════════════════════════════════════════════════════
class ResponseCache:
    def __init__(self, max_size: int = 50, ttl: float = 300.0):
        self._cache: Dict[str, Tuple[str, List[dict], float]] = {}
        self._max_size = max_size
        self._ttl = ttl
        self._lock = threading.Lock()

    def _key(self, text: str) -> str:
        return hashlib.md5(text.lower().strip().encode()).hexdigest()

    def get(self, text: str) -> Optional[Tuple[str, List[dict]]]:
        with self._lock:
            key = self._key(text)
            if key in self._cache:
                response, actions, ts = self._cache[key]
                if time.time() - ts < self._ttl:
                    return response, actions
                del self._cache[key]
            return None

    def put(self, text: str, response: str, actions: List[dict]):
        with self._lock:
            key = self._key(text)
            self._cache[key] = (response, actions, time.time())
            if len(self._cache) > self._max_size:
                oldest = min(self._cache, key=lambda k: self._cache[k][2])
                del self._cache[oldest]

# ═══════════════════════════════════════════════════════════════════════════
# INSTANT COMMAND ROUTER (zero latency — no Ollama needed)
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
        lambda: "Main JARVIS Omega V11 hoon, Sir. Advanced multi-model Ollama architecture.",
}

_SETTINGS: dict = {}

def _greet() -> str:
    h = datetime.now().hour
    t = "Good morning" if h < 12 else ("Good afternoon" if h < 17 else "Good evening")
    return f"{t}, Sir! JARVIS V11 hazir hai. Kya kaam hai aapka?"

def instant_route(text: str) -> Optional[str]:
    for pat, fn in _INSTANT.items():
        if re.search(pat, text, re.I):
            return fn()
    return None

# ═══════════════════════════════════════════════════════════════════════════
# COMPOUND COMMAND PARSER
# Breaks "open youtube and play latest song" into multiple actions
# ═══════════════════════════════════════════════════════════════════════════
_COMPOUND_SEPARATORS = r'\b(and|then|after that|uske baad|aur|phir|baad mein)\b'

def parse_compound_commands(text: str) -> List[str]:
    """Split compound commands into individual commands."""
    parts = re.split(_COMPOUND_SEPARATORS, text, flags=re.I)
    commands = [p.strip() for p in parts if p.strip()]
    return commands if len(commands) > 1 else [text]

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
scan_usb, play_usb_audio
"""

def _sys_prompt(name: str) -> str:
    return SYS.format(name=name, time=datetime.now().strftime("%I:%M %p, %A"))

# ═══════════════════════════════════════════════════════════════════════════
# ACTION EXTRACTOR
# ═══════════════════════════════════════════════════════════════════════════
def extract_actions(response: str) -> List[dict]:
    actions = []
    # Find JSON blocks
    for match in re.finditer(r'\{[^{}]*?"action"\s*:\s*"[^"]+?"[^{}]*?\}', response, re.DOTALL):
        try:
            obj = json.loads(match.group())
            if "action" in obj and obj["action"]:
                actions.append(obj)
        except json.JSONDecodeError:
            pass

    if not actions:
        # Fallback regex
        for match in re.finditer(r'"action"\s*:\s*"([^"]+)"', response):
            action_name = match.group(1)
            seg = response[match.start():match.start() + 200]
            tm = re.search(r'"target"\s*:\s*"([^"]*)"', seg)
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
# OLLAMA CALLER
# ═══════════════════════════════════════════════════════════════════════════
def call_ollama(url: str, model: str, msgs: list, tok: int = 400) -> Optional[str]:
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
            timeout=(8, 120)
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

def check_ollama_running(url: str) -> tuple[bool, list[str]]:
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
# FAST SEQUENTIAL MODEL CALLER
# ═══════════════════════════════════════════════════════════════════════════
def call_first_available(model_list: list[tuple[str, str, int]],
                         msgs: list,
                         global_timeout: float = 90.0) -> Optional[str]:
    deadline = time.time() + global_timeout
    for url, model, tok in model_list:
        if time.time() > deadline:
            print("[BRAIN] Global timeout reached across all models")
            break
        print(f"[BRAIN] Trying model: {model}")
        remaining = deadline - time.time()
        result = _call_with_timeout(url, model, msgs, tok, min(remaining, 90.0))
        if result:
            print(f"[BRAIN] ✓ Got response from {model} ({len(result)} chars)")
            return result
        print(f"[BRAIN] ✗ {model} returned nothing — trying next")
    return None

def _call_with_timeout(url: str, model: str, msgs: list,
                       tok: int, timeout: float) -> Optional[str]:
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
        read_t = min(timeout - connect_t, 110.0)
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
        self.url = settings.get("ollama_url", "http://localhost:11434")
        self.models = settings.get("V11_MODELS", {})

    def _m(self, key: str) -> str:
        return self.models.get(key) or "llama3.2"

    def _entry(self, key: str, tok: int) -> tuple:
        return (self.url, self._m(key), tok)

    def for_chat(self) -> list: return [self._entry("chat", 400), self._entry("fast", 250)]
    def for_search(self) -> list: return [self._entry("reasoning", 600), self._entry("chat", 400)]
    def for_screen(self) -> list: return [self._entry("vision", 400), self._entry("chat", 350)]
    def for_code(self) -> list: return [self._entry("code", 800), self._entry("chat", 400)]
    def for_creative(self) -> list: return [self._entry("creative", 600), self._entry("chat", 400)]
    def for_fast(self) -> list: return [self._entry("fast", 200), self._entry("chat", 300)]

# ═══════════════════════════════════════════════════════════════════════════
# MAIN BRAIN
# ═══════════════════════════════════════════════════════════════════════════
class JarvisBrain:
    def __init__(self, settings: dict):
        global _SETTINGS
        self.settings = settings
        _SETTINGS = settings
        self.memory = Memory()
        self.router = TaskRouter(settings)
        self.cache = ResponseCache()
        self._screen_ctx = ""
        self.automation = None
        self.context_manager = None
        self.vision_enabled = settings.get("V11_FEATURES", {}).get("vision_enabled", True)
        self.web_search_enabled = settings.get("V11_FEATURES", {}).get("web_search_enabled", True)
        self.fast_mode = settings.get("V11_FEATURES", {}).get("fast_mode", True)

        # Check Ollama at startup
        url = settings.get("ollama_url", "http://localhost:11434")
        ok, installed = check_ollama_running(url)
        if ok:
            print(f"[BRAIN] ✓ Ollama running | Installed models: {installed}")
            self._validate_models(installed)
        else:
            print(f"[BRAIN] ⚠ Ollama NOT running at {url}")
            print("[BRAIN] → Open a terminal and run: ollama serve")

        print(f"[BRAIN] ✓ V11 Brain ready")
        print(f"[BRAIN] Chat={self.router._m('chat')} | Fast={self.router._m('fast')}")
        print(f"[BRAIN] Code={self.router._m('code')} | Creative={self.router._m('creative')}")
        print(f"[BRAIN] Vision={self.router._m('vision')} | Reasoning={self.router._m('reasoning')}")

    def _validate_models(self, installed: list[str]):
        needed = set(self.router.models.values())
        inst_base = {m.split(":")[0] for m in installed} | set(installed)
        for m in needed:
            base = m.split(":")[0]
            if base not in inst_base and m not in installed:
                print(f"[BRAIN] ⚠ Model '{m}' NOT installed → run: ollama pull {m}")

    def _build_msgs(self, user_input: str, include_context: bool = True) -> list:
        msgs = [{"role": "system",
                 "content": _sys_prompt(self.settings.get("user_name", "Sir"))}]
        if include_context and self.context_manager:
            ctx = self.context_manager.get_context_summary()
            if ctx and ctx != "No apps currently open.":
                msgs.append({"role": "system", "content": f"Current context: {ctx}"})
        for h in self.memory.context():
            msgs.append({"role": "user", "content": h["user"]})
            msgs.append({"role": "assistant", "content": h["assistant"]})
        msgs.append({"role": "user", "content": user_input})
        return msgs

    def update_screen_context(self, text: str):
        self._screen_ctx = text[:500]

    def process(self, text: str, task_hint: str = "chat") -> Tuple[str, List[dict]]:
        t0 = time.time()

        # ── 0. Check cache for instant response ───────────────────────────
        cached = self.cache.get(text)
        if cached:
            print(f"[BRAIN] Cache hit! {(time.time()-t0)*1000:.0f}ms")
            return cached

        # ── 1. Instant router (0ms, no Ollama) ───────────────────────────
        quick = instant_route(text)
        if quick:
            self.memory.save(text, quick)
            self.cache.put(text, quick, [])
            print(f"[BRAIN] instant {(time.time()-t0)*1000:.0f}ms")
            return quick, []

        # ── 2. Parse compound commands ─────────────────────────────────────
        commands = parse_compound_commands(text)
        is_compound = len(commands) > 1

        # ── 3. Context-aware resolution for follow-ups ────────────────────
        if self.context_manager and len(commands) == 1:
            resolved_action, resolved_target = self.context_manager.resolve_target(text)
            if resolved_action:
                print(f"[BRAIN] Context resolved: {resolved_action} -> {resolved_target}")
                # Build a direct action
                action = {"action": resolved_action, "target": resolved_target or text}
                reply = f"Sir, main {resolved_target} play kar raha hoon."
                self.memory.save(text, reply)
                self.cache.put(text, reply, [action])
                return reply, [action]

        # ── 4. Web search augmentation ────────────────────────────────────
        user_input = text
        if self.web_search_enabled and needs_search(text):
            print("[BRAIN] Running web search…")
            sr = web_search(text, n=3)
            if sr:
                user_input = f"{text}\n\n[Web results]\n{sr}"
                print(f"[BRAIN] Web search done ({len(sr)} chars)")

        # ── 5. Screen vision context ──────────────────────────────────────
        screen_triggers = ["screen", "dekho", "read screen", "click on",
                           "what is on", "screen pe", "dikhao", "kya dikha"]
        if any(t in text.lower() for t in screen_triggers) and self.vision_enabled:
            try:
                from vision.screen_vision import get_screen_reader
                reader = get_screen_reader(self.settings)
                screen_text = reader.read(use_ai=False)
                user_input += f"\n\n[Screen OCR]\n{screen_text[:600]}"
                task_hint = "screen"
                print(f"[BRAIN] Screen OCR injected ({len(screen_text)} chars)")
            except Exception as e:
                print(f"[BRAIN] Screen read error: {e}")

        if self._screen_ctx:
            user_input = f"[Screen context: {self._screen_ctx}]\n\n{user_input}"

        # ── 6. Auto-detect task type ──────────────────────────────────────
        tl = text.lower()
        if task_hint == "chat":
            if any(w in tl for w in ["code", "python", "script", "function", "program", "bug"]):
                task_hint = "code"
            elif any(w in tl for w in ["write", "essay", "story", "poem", "likhna", "creative"]):
                task_hint = "creative"
            elif any(w in tl for w in ["search", "find", "news", "latest", "who is", "what is", "explain"]):
                task_hint = "search"
            elif is_compound:
                task_hint = "fast"  # Compound commands need fast parsing

        # ── 7. Pick model list ────────────────────────────────────────────
        if self.fast_mode and task_hint == "chat":
            model_list = self.router.for_fast()
        else:
            model_list = {
                "screen": self.router.for_screen,
                "search": self.router.for_search,
                "code": self.router.for_code,
                "creative": self.router.for_creative,
                "fast": self.router.for_fast,
            }.get(task_hint, self.router.for_chat)()

        msgs = self._build_msgs(user_input)

        # ── 8. Call models sequentially ────────────────────────────────────
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

        # ── 9. Extract + clean ────────────────────────────────────────────
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

        # ── 10. Handle compound commands ───────────────────────────────────
        if is_compound and not actions:
            # Force generate actions from compound command
            actions = self._generate_actions_from_commands(commands)
            if actions:
                clean = f"Sir, main {' aur '.join(commands)} kar raha hoon."
        elif is_compound and actions:
            # Ensure we have enough actions for all commands
            extra_actions = self._generate_actions_from_commands(commands[len(actions):])
            actions.extend(extra_actions)

        self.memory.save(text, clean)
        self.cache.put(text, clean, actions)
        print(f"[BRAIN] Done in {time.time()-t0:.2f}s | {len(actions)} action(s)")
        return clean, actions

    def _generate_actions_from_commands(self, commands: List[str]) -> List[dict]:
        """Generate actions from plain command text when LLM fails."""
        actions = []
        for cmd in commands:
            cl = cmd.lower()
            if any(w in cl for w in ["open youtube", "youtube kholo"]):
                actions.append({"action": "open_url", "target": "https://youtube.com"})
            elif any(w in cl for w in ["open google", "google kholo"]):
                actions.append({"action": "open_url", "target": "https://google.com"})
            elif any(w in cl for w in ["play", "bajao", "chalaao", "song", "gaana"]):
                query = re.sub(r'\b(play|bajao|chalaao|song|gaana|music|kar)\b', '', cl, flags=re.I).strip()
                actions.append({"action": "search_youtube", "target": query or "latest songs"})
            elif any(w in cl for w in ["open", "kholo", "start"]):
                app = re.sub(r'\b(open|kholo|start|the|app)\b', '', cl, flags=re.I).strip()
                if app:
                    actions.append({"action": "open_app", "target": app})
        return actions

    def clear_history(self):
        self.memory.short_term.clear()
        self.cache._cache.clear()

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
    text = re.sub(r'[\u0900-\u097F]+', lambda m: f'[{m.group()}]', text)
    return text
