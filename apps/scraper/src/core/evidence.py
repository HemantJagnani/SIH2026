"""
EvidenceCapture — writes HTML, screenshots, and metadata checkpoints.

Phase 16 spec:
Directory structure:
evidence/
YYYY-MM-DD/
run_id/
source/
route/
lead_time/
observation_id/

Store where permitted:
- core.html / core.png
- details.html / details.png
- fares.html / fares.png
- metadata.json

Guarantees:
- Never overwrites previous evidence.
- Preserves full audit trail for CPI reproducibility.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

EVIDENCE_DIR = Path("evidence")


class EvidenceCapture:
    """
    Captures raw evidence checkpoints (HTML, screenshot, metadata) for a scrape job.
    """

    def __init__(self, base_dir: Path = EVIDENCE_DIR):
        self.base_dir = base_dir

    def get_checkpoint_dir(
        self,
        source: str,
        run_id: str,
        route: str,
        lead_time: int,
        observation_id: str,
        date_str: Optional[str] = None,
    ) -> Path:
        """
        Builds the canonical checkpoint directory per Phase 16:
        evidence/YYYY-MM-DD/run_id/source/route/lead_time/observation_id/
        """
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        clean_route = route.replace("->", "-").replace("–", "-").upper()
        lead_str = f"T+{lead_time}"

        checkpoint_dir = (
            self.base_dir
            / date_str
            / str(run_id)
            / str(source)
            / clean_route
            / lead_str
            / str(observation_id)
        )
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return checkpoint_dir

    async def save_checkpoint(
        self,
        page: Any,
        checkpoint_name: str,  # 'core', 'details', 'fares'
        source: str,
        run_id: str,
        route: str,
        lead_time: int,
        travel_date: str,
        observation_id: str,
        extraction_mode: str = "CORE_ONLY",
        enrichment_type: Optional[str] = None,
        navigation_state: Optional[str] = None,
        parser_version: str = "1.0.0",
        navigation_version: str = "1.0.0",
        result_count: int = 1,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Saves a named checkpoint (core, details, or fares) with HTML, screenshot, and metadata.json.
        """
        checkpoint_dir = self.get_checkpoint_dir(
            source=source,
            run_id=run_id,
            route=route,
            lead_time=lead_time,
            observation_id=observation_id,
        )

        try:
            # 1. Save HTML
            html_path = checkpoint_dir / f"{checkpoint_name}.html"
            if not html_path.exists() and page:
                try:
                    html_content = await page.content()
                    html_path.write_text(html_content, encoding="utf-8")
                except Exception as e:
                    logger.debug(f"EvidenceCapture: Could not grab HTML for {checkpoint_name}: {e}")

            # 2. Save Screenshot (.png)
            png_path = checkpoint_dir / f"{checkpoint_name}.png"
            if not png_path.exists() and page:
                try:
                    await page.screenshot(path=str(png_path), full_page=False)
                except Exception as e:
                    logger.debug(f"EvidenceCapture: Could not take screenshot for {checkpoint_name}: {e}")

            # 3. Save or update metadata.json
            meta_path = checkpoint_dir / "metadata.json"
            meta_data: Dict[str, Any] = {}
            if meta_path.exists():
                try:
                    meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

            meta_data.update({
                "source": source,
                "route": route,
                "travel_date": travel_date,
                "lead_time": lead_time,
                "collection_timestamp": datetime.now(timezone.utc).isoformat(),
                "observation_id": observation_id,
                "parser_version": parser_version,
                "navigation_version": navigation_version,
                "extraction_mode": extraction_mode,
                "enrichment_type": enrichment_type,
                "navigation_state": navigation_state,
                "result_count": result_count,
            })
            if additional_metadata:
                meta_data.update(additional_metadata)

            meta_path.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
            logger.info(f"EvidenceCapture: Checkpoint '{checkpoint_name}' written to {checkpoint_dir}")
            return checkpoint_dir

        except Exception as e:
            logger.error(f"EvidenceCapture: Failed to write checkpoint {checkpoint_name}: {e}")
            return checkpoint_dir

    # Legacy support for existing orchestrator calls
    def _get_job_dir(self, source: str, run_id: Optional[str] = None) -> Path:
        if not run_id:
            run_id = str(uuid.uuid4())
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        job_dir = Path("runtime/evidence") / date_str / f"source={source}" / f"run={run_id}"
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    async def capture(
        self,
        page: Any,
        source: str,
        request_data: Dict[str, Any],
        status: str,
        result_data: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Path:
        """Captures page state for backwards-compatible orchestrator runs."""
        job_dir = self._get_job_dir(source, run_id)
        try:
            (job_dir / "request.json").write_text(json.dumps(request_data, indent=2))
            try:
                html_content = await page.content()
                (job_dir / "page.html").write_text(html_content, encoding="utf-8")
            except Exception:
                pass
            if result_data:
                (job_dir / "result.json").write_text(json.dumps(result_data, indent=2))
            try:
                await page.screenshot(path=str(job_dir / "screenshot.png"), full_page=True)
            except Exception:
                pass
            metadata = {
                "source": source,
                "run_id": run_id,
                "status": status,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "error_message": error_message,
            }
            (job_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
            return job_dir
        except Exception as e:
            logger.error(f"Failed to capture evidence: {e}")
            return job_dir
