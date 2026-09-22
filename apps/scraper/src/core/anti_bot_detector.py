"""
anti_bot_detector.py — Detection (not bypass) of CAPTCHA, access blocks,
login walls, and rate-limiting on airline/OTA pages.

Phase 9 spec §CAPTCHA-detection:
    Detect, do not solve.

Phase 9 spec §http-status-policy:
    403 → ACCESS_BLOCKED, stop source
    429 → RATE_LIMITED, backoff / honor Retry-After
    401 → AUTH_REQUIRED, stop source
    451 → LEGAL_RESTRICTION, stop source
    Login wall → AUTH_REQUIRED, stop source
    CAPTCHA → CAPTCHA_BLOCKED, stop source

IMPORTANT:
    These functions only DETECT. They never attempt to:
    - Solve a CAPTCHA
    - Rotate a session or proxy to avoid a block
    - Retry a request after a 403
    When detection fires, the calling code (CollectionOrchestrator) must:
    1. Capture evidence (screenshot + HTML)
    2. Record the AvailabilityStatus
    3. Call session_manager.mark_blocked(source)
    4. Stop the job cleanly

All detection is based on publicly visible page text, HTTP status codes,
and well-known DOM markers — not on any internal anti-bot intelligence.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CAPTCHA text markers
# Source: Phase 9 spec §CAPTCHA-detection
# These strings appear in the body text of common CAPTCHA/challenge pages.
# ---------------------------------------------------------------------------
CAPTCHA_TEXT_MARKERS = (
    "captcha",
    "verify you are human",
    "human verification",
    "security check",
    "automated queries",
    "unusual traffic",
    "prove you are not a robot",
    "are you a robot",
    "bot verification",
    "ddos-guard",
    "cloudflare",         # Cloudflare challenge pages
    "just a moment",      # Cloudflare "Just a moment..." challenge
    "checking your browser",
)

# Common DOM element IDs/classes/data attributes that indicate a CAPTCHA.
# These are checked in addition to body text.
CAPTCHA_DOM_MARKERS = (
    "captcha",
    "recaptcha",
    "h-captcha",
    "cf-challenge",
    "cf-turnstile",
    "challenge-form",
)

# Text that indicates a login wall has appeared.
LOGIN_WALL_MARKERS = (
    "sign in to continue",
    "please log in",
    "login to view",
    "sign up to search",
    "create an account",
    "member-only",
    "access restricted",
)


# ---------------------------------------------------------------------------
# Detection functions
# ---------------------------------------------------------------------------

async def captcha_present(page) -> bool:
    """
    Return True if the page appears to be showing a CAPTCHA or bot challenge.

    Checks:
    1. Body text for known CAPTCHA phrases (case-insensitive).
    2. DOM elements with known CAPTCHA-related IDs / class names.

    Args:
        page: A Playwright Page object.

    Returns:
        True if a CAPTCHA or challenge page is detected.
    """
    try:
        body_text = (await page.locator("body").inner_text()).lower()
    except Exception as exc:
        logger.warning("anti_bot_detector: could not read body text — %s", exc)
        return False

    # Check text markers.
    for marker in CAPTCHA_TEXT_MARKERS:
        if marker in body_text:
            logger.warning(
                "anti_bot_detector: CAPTCHA marker detected in body text: '%s'", marker
            )
            return True

    # Check DOM markers: look for elements whose id/class contains the keyword.
    for marker in CAPTCHA_DOM_MARKERS:
        try:
            # Use CSS attribute-contains selector for id and class.
            count = await page.locator(
                f"[id*='{marker}'], [class*='{marker}'], [data-testid*='{marker}']"
            ).count()
            if count > 0:
                logger.warning(
                    "anti_bot_detector: CAPTCHA DOM element found with marker '%s' (%d element(s))",
                    marker, count,
                )
                return True
        except Exception:
            pass  # Selector errors are non-fatal; move on to the next marker.

    return False


def is_access_blocked(http_status: int) -> bool:
    """
    Return True if the HTTP status code indicates a hard access block.

    403 → ACCESS_BLOCKED (do NOT retry, do NOT rotate)
    451 → LEGAL_RESTRICTION (legal block)

    Args:
        http_status: The HTTP response status code.
    """
    blocked = http_status in (403, 451)
    if blocked:
        logger.warning(
            "anti_bot_detector: access blocked — HTTP %d (no retry, no rotation).",
            http_status,
        )
    return blocked


def is_rate_limited(http_status: int, retry_after: Optional[str] = None) -> tuple[bool, Optional[float]]:
    """
    Return (True, wait_seconds) if the server is rate-limiting us (HTTP 429).

    Args:
        http_status: The HTTP response status code.
        retry_after: The value of the Retry-After response header, if present.
                     Can be a number of seconds or an HTTP-date string.

    Returns:
        (True, wait_seconds) if rate-limited, where wait_seconds is the
        recommended backoff (from Retry-After or a conservative default).
        (False, None) if not rate-limited.
    """
    if http_status != 429:
        return False, None

    wait_seconds = _parse_retry_after(retry_after)
    logger.warning(
        "anti_bot_detector: rate limited (HTTP 429). Recommended backoff: %.0fs.",
        wait_seconds,
    )
    return True, wait_seconds


def is_auth_required(http_status: int) -> bool:
    """
    Return True if the server requires authentication (HTTP 401).

    401 → AUTH_REQUIRED (stop source; do NOT attempt login)

    Args:
        http_status: The HTTP response status code.
    """
    if http_status == 401:
        logger.warning(
            "anti_bot_detector: authentication required (HTTP 401) — stopping source."
        )
        return True
    return False


async def is_login_wall(page) -> bool:
    """
    Return True if the page appears to be showing a login wall or sign-up gate.

    A login wall typically appears as a modal or redirect requiring the user
    to log in before seeing fare results. We detect it purely by visible text.

    Args:
        page: A Playwright Page object.

    Returns:
        True if a login wall is detected.
    """
    try:
        body_text = (await page.locator("body").inner_text()).lower()
    except Exception as exc:
        logger.warning("anti_bot_detector: could not read body text for login wall check — %s", exc)
        return False

    for marker in LOGIN_WALL_MARKERS:
        if marker in body_text:
            logger.warning(
                "anti_bot_detector: login wall detected — text marker: '%s'", marker
            )
            return True

    return False


def is_server_error(http_status: int) -> bool:
    """
    Return True if the HTTP status indicates a server error (5xx).

    5xx → SERVER_ERROR (bounded retry permitted — max 2 per Phase 9 spec)

    Args:
        http_status: The HTTP response status code.
    """
    return 500 <= http_status < 600


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_CONSERVATIVE_BACKOFF_SECONDS = 120  # 2 minutes if Retry-After is absent


def _parse_retry_after(retry_after: Optional[str]) -> float:
    """
    Parse the Retry-After header value into a wait duration in seconds.

    Supports:
    - A plain integer string ("60")
    - Absent value → conservative default (2 minutes)

    HTTP-date format (e.g. "Wed, 21 Oct 2015 07:28:00 GMT") is not parsed
    here; in practice, airlines return numeric values.

    Returns:
        Float seconds to wait.
    """
    if retry_after is None:
        return float(_CONSERVATIVE_BACKOFF_SECONDS)

    try:
        return max(float(retry_after.strip()), 1.0)
    except ValueError:
        logger.debug(
            "anti_bot_detector: could not parse Retry-After '%s'; using %ds default.",
            retry_after, _CONSERVATIVE_BACKOFF_SECONDS,
        )
        return float(_CONSERVATIVE_BACKOFF_SECONDS)
