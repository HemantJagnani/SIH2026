"""
Live Playwright source – compliance-gated, honest User-Agent.

DISABLED BY DEFAULT. Enable only after:
  1. Verifying robots.txt allows the search path for our UA.
  2. Reading and recording the ToS outcome in SOURCES.md.
  3. Changing source.name to 'live' in config.yaml.

Behaviour on failure:
  - robots.txt refusal    → return ([], refused_snapshot)
  - HTTP 403 / 429        → stop, record reason, do not retry with different headers
  - CAPTCHA / login wall  → stop, record reason
  - Network timeout       → one retry after 60 s, then stop
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime
from pathlib import Path

from apix.compliance import ComplianceGate, Refused
from apix.models import Quote, RawSnapshot
from apix.sources.base import FareSource

logger = logging.getLogger(__name__)

# Raw HTML snapshots are saved here (gitignored)
_RAW_DIR = Path(__file__).parent.parent.parent.parent / "data" / "raw"


class LiveSource(FareSource):
    """
    Playwright-based live scraper.

    All URL fetches go through the compliance gate first. On any block,
    error or challenge page, the run stops for that page and records the
    reason. No retries with altered behaviour; one retry for network
    timeouts only.
    """

    def __init__(
        self,
        run_id: int,
        target_url_template: str,
        compliance_gate: ComplianceGate,
        user_agent: str,
    ) -> None:
        self.run_id = run_id
        self.url_template = target_url_template
        self.gate = compliance_gate
        self.user_agent = user_agent

    def fetch(
        self,
        route: str,
        origin: str,
        destination: str,
        travel_date: date,
        run_id: int,
    ) -> tuple[list[Quote], RawSnapshot]:
        url = self.url_template.format(
            origin=origin,
            destination=destination,
            date=travel_date.isoformat(),
        )

        # ── Compliance check ──────────────────────────────────────────────
        result = self.gate.check(url)
        if isinstance(result, Refused):
            snapshot = RawSnapshot(
                run_id=run_id,
                route=route,
                travel_date=travel_date,
                fetched_at=datetime.utcnow(),
                url=url,
                http_status=None,
                robots_allowed=False,
                body_path=None,
            )
            logger.warning("Live source: compliance refused %s — %s", url, result.reason)
            return [], snapshot

        # ── Playwright fetch ───────────────────────────────────────────────
        try:
            from playwright.sync_api import sync_playwright  # lazy import
        except ImportError:
            raise RuntimeError(
                "playwright is not installed. Run: pip install playwright && "
                "playwright install chromium"
            )

        body_path: str | None = None
        http_status: int | None = None
        quotes: list[Quote] = []

        def _do_fetch() -> tuple[int | None, str | None, list[Quote]]:
            """Inner fetch; returns (status, body_path, quotes)."""
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                ctx = browser.new_context(user_agent=self.user_agent)
                page = ctx.new_page()

                # One network-timeout retry is handled in the caller
                response = page.goto(url, timeout=30_000)
                status = response.status if response else None

                # Detect stop conditions
                if status in (403, 429):
                    logger.warning("Live source: HTTP %s for %s — stopping", status, url)
                    browser.close()
                    return status, None, []

                content = page.content()

                # Simple CAPTCHA / login-wall heuristic (extend as needed)
                lower = content.lower()
                if any(kw in lower for kw in ("captcha", "challenge", "login", "sign in")):
                    logger.warning("Live source: challenge page detected for %s — stopping", url)
                    browser.close()
                    return status, None, []

                # Save raw HTML
                _RAW_DIR.mkdir(parents=True, exist_ok=True)
                fname = f"{route}_{travel_date}_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.html"
                out_path = _RAW_DIR / fname
                out_path.write_text(content, encoding="utf-8")
                rel_path = str(out_path.relative_to(Path(__file__).parent.parent.parent.parent))

                parsed = self._parse_page(content, route, origin, destination, travel_date, run_id)
                browser.close()
                return status, rel_path, parsed

        # One retry for network timeout only
        for attempt in range(2):
            try:
                http_status, body_path, quotes = _do_fetch()
                break
            except Exception as exc:
                if attempt == 0 and "timeout" in str(exc).lower():
                    logger.warning("Network timeout for %s; retrying in 60 s", url)
                    time.sleep(60)
                else:
                    logger.error("Live source fetch failed for %s: %s", url, exc)
                    break

        snapshot = RawSnapshot(
            run_id=run_id,
            route=route,
            travel_date=travel_date,
            fetched_at=datetime.utcnow(),
            url=url,
            http_status=http_status,
            robots_allowed=True,
            body_path=body_path,
        )
        return quotes, snapshot

    def _parse_page(
        self,
        html: str,
        route: str,
        origin: str,
        destination: str,
        travel_date: date,
        run_id: int,
    ) -> list[Quote]:
        """
        Parse flight result HTML into Quote objects.

        NOTE: This is a stub. Selectors must be determined by inspecting
        the rendered DOM for the specific source, then written here and
        saved as fixture tests. Do not guess selectors.
        """
        logger.warning(
            "LiveSource._parse_page is a stub. "
            "Inspect the rendered DOM and implement real selectors before use."
        )
        return []
