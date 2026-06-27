"""
core/context.py — JARVIS OMEGA V11
Context Manager: Tracks open apps, last actions, and user intent for smart follow-ups.
"""
from __future__ import annotations

import time
import psutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class AppContext:
    name: str
    window_title: str = ""
    opened_at: float = field(default_factory=time.time)
    url: str = ""  # For browsers
    is_browser: bool = False
    is_media_player: bool = False

class ContextManager:
    """Tracks what the user is doing so follow-up commands make sense."""

    def __init__(self):
        self.open_apps: List[AppContext] = []
        self.last_action: Optional[str] = None
        self.last_target: Optional[str] = None
        self.last_command_time: float = 0.0
        self.pending_tasks: List[Dict[str, Any]] = []
        self.user_location: str = "desktop"
        self._cache: Dict[str, Any] = {}

    def record_action(self, action: str, target: str = "", result: Any = None):
        self.last_action = action
        self.last_target = target
        self.last_command_time = time.time()

        # Track opened apps
        if action in ("open_app", "open_browser", "open_url", "search_web", "search_youtube"):
            app_name = target.lower().strip()
            is_browser = any(b in app_name for b in ["chrome", "edge", "firefox", "brave", "browser"])
            is_media = any(m in app_name for m in ["spotify", "vlc", "media", "music", "player"])

            # Remove duplicate entries
            self.open_apps = [a for a in self.open_apps if a.name != app_name]

            ctx = AppContext(
                name=app_name,
                opened_at=time.time(),
                is_browser=is_browser,
                is_media_player=is_media
            )
            self.open_apps.append(ctx)

            # Keep only last 5 apps
            self.open_apps = self.open_apps[-5:]

    def get_last_browser(self) -> Optional[AppContext]:
        for app in reversed(self.open_apps):
            if app.is_browser:
                return app
        return None

    def get_last_media_player(self) -> Optional[AppContext]:
        for app in reversed(self.open_apps):
            if app.is_media_player:
                return app
        return None

    def get_most_recent_app(self) -> Optional[AppContext]:
        if self.open_apps:
            return self.open_apps[-1]
        return None

    def is_follow_up(self) -> bool:
        return (time.time() - self.last_command_time) < 45.0

    def resolve_target(self, command: str) -> tuple[str, str]:
        """
        Smart target resolution.
        If user says "play a song" after opening YouTube, target YouTube.
        Returns (resolved_action, resolved_target)
        """
        cmd_lower = command.lower()

        # Music play follow-up
        if any(w in cmd_lower for w in ["play", "bajao", "chalaao", "song", "gaana", "music"]):
            last_browser = self.get_last_browser()
            if last_browser and "youtube" in last_browser.name:
                return "search_youtube", command.replace("play", "").replace("song", "").strip()
            if last_browser and "spotify" in last_browser.name:
                return "play_music", command.replace("play", "").replace("song", "").strip()

        # Search follow-up
        if any(w in cmd_lower for w in ["search", "find", "look for", "dhundo", "khojo"]):
            last_browser = self.get_last_browser()
            if last_browser and "youtube" in last_browser.name:
                return "search_youtube", command.replace("search", "").strip()

        # Default: no resolution
        return "", ""

    def get_context_summary(self) -> str:
        if not self.open_apps:
            return "No apps currently open."
        lines = []
        for app in reversed(self.open_apps[-3:]):
            lines.append(f"- {app.name} (opened {int(time.time() - app.opened_at)}s ago)")
        return "\n".join(lines)

    def clear(self):
        self.open_apps.clear()
        self.last_action = None
        self.last_target = None
        self.pending_tasks.clear()
