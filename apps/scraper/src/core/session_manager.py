"""
session_manager.py — Browser session state management for Phase 9.

Handles saving and restoring Playwright BrowserContext state (cookies +
localStorage) between runs so that each source can maintain a coherent
session across multiple collection jobs.

Architecture (per user recommendation):
    Crawlee SessionPool  →  logical crawler session
    Playwright BrowserContext  →  cookies / localStorage (this module)
    Persistent profile  →  NOT used in this POC

Design decisions:
    - We do NOT use persistent Chromium user data directories (user_data_dir)
      in this POC. Persistent profiles add complexity and state-related bugs
      that are hard to debug. We use Playwright's lighter storage_state
      snapshots instead.
    - Storage state files are saved per source in:
          runtime/session_states/<source>.state.json
    - These files are in .gitignore and must never be committed.
    - On CAPTCHA or access block: do NOT save a new state. The blocked
      state would propagate to the next run and is misleading.
    - Normal session expiry: allowed to create a fresh state automatically.

Phase 9 compliance:
    - Session rotation after a block is NOT supported.
    - max_session_rotations=0 in the crawler is the enforcement layer;
      this module is the storage layer.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Root directory for session state files (relative to project root).
# This path is excluded in .gitignore.
_DEFAULT_STATE_DIR = Path("runtime/session_states")


class SessionManager:
    """
    Manages Playwright BrowserContext storage_state for per-source sessions.

    Playwright's storage_state captures:
    - Cookies
    - localStorage entries
    - sessionStorage entries (where available)

    This lets the browser "remember" that it has visited a site before,
    accepted consent banners, etc. — without needing a full persistent profile.

    Usage (in a Crawlee handler):
        manager = SessionManager()

        # Before navigation — load saved state into the context
        saved_state = manager.load("indigo")
        if saved_state:
            await browser_context.add_cookies(saved_state.get("cookies", []))

        # After a successful run — save the updated context state
        state = await browser_context.storage_state()
        manager.save("indigo", state)

        # On CAPTCHA or block — do NOT save
        if captcha_detected:
            manager.mark_blocked("indigo")
            # do not call save()
    """

    def __init__(self, state_dir: Optional[Path | str] = None) -> None:
        """
        Args:
            state_dir: Directory to store session state files.
                       Defaults to runtime/session_states/.
        """
        self._state_dir = Path(state_dir) if state_dir else _DEFAULT_STATE_DIR
        self._state_dir.mkdir(parents=True, exist_ok=True)
        # In-memory record of sources that have been blocked this run.
        self._blocked: set[str] = set()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load(self, source: str) -> Optional[dict]:
        """
        Load the saved storage_state for a source, if it exists.

        Returns:
            A dict with "cookies", "origins" keys (Playwright storage_state
            format), or None if no saved state exists.
        """
        path = self._state_path(source)
        if not path.exists():
            logger.debug("SessionManager: no saved state for '%s'.", source)
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            logger.info(
                "SessionManager: loaded session state for '%s' from %s.", source, path
            )
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "SessionManager: could not read state for '%s' — %s. "
                "Starting fresh.",
                source, exc,
            )
            return None

    def save(self, source: str, state: dict) -> None:
        """
        Persist the Playwright storage_state for a source.

        This should ONLY be called after a successful, unblocked collection run.
        Do not call this if the run ended with CAPTCHA, 403, or any access block.

        Args:
            source: Source identifier (e.g. "indigo").
            state: The dict returned by Playwright's `context.storage_state()`.
        """
        if source in self._blocked:
            logger.warning(
                "SessionManager: refusing to save state for blocked source '%s'. "
                "Call mark_blocked() only when the source was blocked this run.",
                source,
            )
            return

        path = self._state_path(source)
        try:
            path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            logger.info("SessionManager: saved session state for '%s' to %s.", source, path)
        except OSError as exc:
            logger.error(
                "SessionManager: could not save state for '%s' — %s.", source, exc
            )

    def mark_blocked(self, source: str) -> None:
        """
        Record that this source was blocked this run so that save() is refused.

        Call this as soon as CAPTCHA, 403, or a login wall is detected.
        This prevents a corrupted (blocked-state) session from being persisted
        and accidentally reused in the next run.
        """
        self._blocked.add(source)
        logger.warning(
            "SessionManager: source '%s' marked as blocked — session state will NOT be saved.",
            source,
        )

    def is_blocked(self, source: str) -> bool:
        """Return True if this source was blocked during this run."""
        return source in self._blocked

    def clear_state(self, source: str) -> None:
        """
        Delete the saved state file for a source (e.g. after a schema change
        or when you want to start a completely fresh session).
        """
        path = self._state_path(source)
        if path.exists():
            path.unlink()
            logger.info("SessionManager: cleared saved state for '%s'.", source)
        else:
            logger.debug("SessionManager: no state to clear for '%s'.", source)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _state_path(self, source: str) -> Path:
        """Return the file path for a source's session state."""
        # Sanitize source name to a safe filename.
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in source)
        return self._state_dir / f"{safe_name}.state.json"
