"""
EvidenceCapture — writes HTML and WebP screenshots to runtime/evidence/

Phase 9 spec:
When a failure occurs (or success, depending on config), we must capture:
- request.json
- page.html
- result.json (if any)
- screenshot.png (WebP format for smaller size, but named .png or .webp)
- metadata.json
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

EVIDENCE_DIR = Path("runtime/evidence")


class EvidenceCapture:
    """
    Captures raw evidence (HTML, screenshot, metadata) for a scrape job.
    """

    def __init__(self, base_dir: Path = EVIDENCE_DIR):
        self.base_dir = base_dir

    def _get_job_dir(self, source: str, run_id: Optional[str] = None) -> Path:
        if not run_id:
            run_id = str(uuid.uuid4())
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        job_dir = self.base_dir / date_str / f"source={source}" / f"run={run_id}"
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
        """
        Captures the current page state and writes evidence files.

        Args:
            page: Playwright page object (or anything with similar methods).
            source: Source identifier (e.g. 'indigo').
            request_data: Original search parameters.
            status: e.g. 'CAPTCHA_BLOCKED', 'AVAILABLE', etc.
            result_data: Parsed data, if any.
            run_id: UUID of the collection run.
            error_message: Exception or error string.

        Returns:
            The directory path where evidence was saved.
        """
        job_dir = self._get_job_dir(source, run_id)
        
        try:
            # 1. request.json
            (job_dir / "request.json").write_text(json.dumps(request_data, indent=2))

            # 2. page.html
            try:
                html_content = await page.content()
                (job_dir / "page.html").write_text(html_content, encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to capture HTML: {e}")

            # 3. result.json (if any)
            if result_data:
                (job_dir / "result.json").write_text(json.dumps(result_data, indent=2))

            # 4. screenshot.webp
            try:
                # Capture WebP to save space if supported, otherwise default png
                screenshot_path = str(job_dir / "screenshot.png")
                await page.screenshot(path=screenshot_path, full_page=True)
            except Exception as e:
                logger.error(f"Failed to capture screenshot: {e}")

            # 5. metadata.json
            try:
                url = page.url
            except Exception:
                url = None

            metadata = {
                "source": source,
                "run_id": run_id,
                "status": status,
                "url": url,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "error_message": error_message,
            }
            (job_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

            logger.info(f"Captured evidence for {source} at {job_dir}")
            return job_dir
            
        except Exception as e:
            logger.error(f"Failed to capture evidence: {e}")
            return job_dir

