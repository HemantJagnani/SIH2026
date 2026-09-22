import asyncio
import pytest
import os
import json
from pathlib import Path

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))

from core.evidence import EvidenceCapture
from core.retry_policy import HttpStatusPolicy, HttpAction


class MockPage:
    def __init__(self, html, url="https://example.com/search"):
        self._html = html
        self.url = url
    
    async def content(self):
        return self._html
        
    async def screenshot(self, path=None, full_page=False):
        if path:
            Path(path).write_bytes(b"fake image data")

@pytest.mark.asyncio
async def test_evidence_capture_creates_all_files(tmp_path):
    capture = EvidenceCapture(base_dir=tmp_path)
    
    page = MockPage("<html><body>Blocked</body></html>")
    request_data = {"origin": "DEL", "destination": "BOM"}
    
    job_dir = await capture.capture(
        page=page,
        source="test_source",
        request_data=request_data,
        status="CAPTCHA_BLOCKED",
        result_data={"some": "data"},
        run_id="test-run-123",
        error_message="Captcha detected"
    )
    
    assert job_dir.exists()
    assert (job_dir / "request.json").exists()
    assert (job_dir / "page.html").exists()
    assert (job_dir / "result.json").exists()
    assert (job_dir / "screenshot.png").exists()
    assert (job_dir / "metadata.json").exists()
    
    metadata = json.loads((job_dir / "metadata.json").read_text())
    assert metadata["source"] == "test_source"
    assert metadata["status"] == "CAPTCHA_BLOCKED"
    assert metadata["error_message"] == "Captcha detected"

def test_http_status_policy():
    assert HttpStatusPolicy.evaluate(200) == HttpAction.PARSE
    
    assert HttpStatusPolicy.evaluate(401) == HttpAction.STOP
    assert HttpStatusPolicy.evaluate(403) == HttpAction.STOP
    assert HttpStatusPolicy.evaluate(451) == HttpAction.STOP
    
    assert HttpStatusPolicy.evaluate(429) == HttpAction.BACKOFF
    
    assert HttpStatusPolicy.evaluate(408) == HttpAction.RETRY
    assert HttpStatusPolicy.evaluate(500) == HttpAction.RETRY
    assert HttpStatusPolicy.evaluate(503) == HttpAction.RETRY
    
    assert HttpStatusPolicy.evaluate(404) == HttpAction.STOP
    assert HttpStatusPolicy.evaluate(400) == HttpAction.STOP
