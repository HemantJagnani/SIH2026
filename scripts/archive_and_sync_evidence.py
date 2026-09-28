"""
Automated Evidence Archiving and GitHub Release Sync for APIx.

Can be run:
1. Locally: `python scripts/archive_and_sync_evidence.py [YYYY-MM-DD]`
2. In GitHub Actions: automatically called after each daily collection run.
"""

import os
import sys
import json
import tarfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import urllib.request
import urllib.error

import subprocess

ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

DEFAULT_REPO_OWNER = "HemantJagnani"
DEFAULT_REPO_NAME = "SIH2026"
DEFAULT_TAG = "v1.0-evidence"


def get_github_token() -> Optional[str]:
    """Retrieve GitHub token from env or automatically query git credential manager."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n",
            capture_output=True,
            text=True,
            timeout=5
        )
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                val = line.split("=", 1)[1].strip()
                if val:
                    return val
    except Exception:
        pass
    return None


def get_repo_info() -> tuple[str, str]:
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("REPO_OWNER", DEFAULT_REPO_OWNER)
    repo = os.environ.get("GITHUB_REPOSITORY")
    if repo and "/" in repo:
        owner, repo_name = repo.split("/", 1)
        return owner, repo_name
    return owner, os.environ.get("REPO_NAME", DEFAULT_REPO_NAME)


def archive_evidence_for_date(date_str: str) -> Optional[Path]:
    evidence_dir = ROOT / "runtime" / "evidence" / date_str
    if not evidence_dir.exists():
        print(f"No evidence directory found at {evidence_dir}")
        return None

    out_archive = ROOT / "runtime" / f"apix_evidence_{date_str.replace('-', '_')}.tar.gz"
    print(f"Compressing {evidence_dir} into {out_archive.name}...")

    with tarfile.open(out_archive, "w:gz") as tar:
        tar.add(evidence_dir, arcname=f"evidence/{date_str}")

    size_mb = out_archive.stat().st_size / (1024 * 1024)
    print(f"Compression complete: {out_archive.name} ({size_mb:.2f} MB)")
    return out_archive


def upload_to_github_release(
    archive_path: Path,
    tag_name: str = DEFAULT_TAG,
    release_title: Optional[str] = None,
    github_token: Optional[str] = None
) -> bool:
    token = github_token or get_github_token()
    if not token:
        print(
            "GITHUB_TOKEN not found in environment or git credentials. Evidence is compressed locally at "
            f"{archive_path}, but not uploaded to GitHub. Set GITHUB_TOKEN in .env or run in GitHub Actions to enable auto-upload."
        )
        return False

    owner, repo = get_repo_info()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "APIx-Evidence-Archiver"
    }

    # Fetch release
    release_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag_name}"
    req = urllib.request.Request(release_url, headers=headers, method="GET")

    release_data = None
    try:
        with urllib.request.urlopen(req) as resp:
            release_data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"Release {tag_name} not found. Creating new release on {owner}/{repo}...")
            create_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
            payload = json.dumps({
                "tag_name": tag_name,
                "name": release_title or f"APIx Scraped Evidence Snapshot ({tag_name})",
                "body": "Automated audit trail of raw HTML DOMs and screenshots for APIx airfare observations."
            }).encode()
            create_req = urllib.request.Request(create_url, data=payload, headers={**headers, "Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(create_req) as c_resp:
                release_data = json.loads(c_resp.read().decode())
        else:
            print(f"GitHub API error fetching release: {e}")
            return False

    release_id = release_data.get("id")
    assets = release_data.get("assets", [])
    filename = archive_path.name

    # Remove old asset if duplicate exists
    for asset in assets:
        if asset.get("name") == filename:
            asset_id = asset.get("id")
            print(f"Existing asset {filename} (id={asset_id}) found. Replacing with fresh version...")
            del_url = f"https://api.github.com/repos/{owner}/{repo}/releases/assets/{asset_id}"
            del_req = urllib.request.Request(del_url, headers=headers, method="DELETE")
            try:
                with urllib.request.urlopen(del_req):
                    pass
            except Exception as de:
                print(f"Note: Could not delete old asset: {de}")

    upload_url = f"https://uploads.github.com/repos/{owner}/{repo}/releases/{release_id}/assets?name={filename}"
    file_bytes = archive_path.read_bytes()
    upload_headers = {
        **headers,
        "Content-Type": "application/gzip",
        "Content-Length": str(len(file_bytes))
    }
    upload_req = urllib.request.Request(upload_url, data=file_bytes, headers=upload_headers, method="POST")

    try:
        print(f"Uploading {filename} ({len(file_bytes) / (1024*1024):.2f} MB) to GitHub Release {tag_name}...")
        with urllib.request.urlopen(upload_req) as up_resp:
            resp_data = json.loads(up_resp.read().decode())
            download_url = resp_data.get("browser_download_url")
            print(f"SUCCESS! Asset uploaded to GitHub: {download_url}")
            return True
    except urllib.error.HTTPError as he:
        print(f"Failed to upload asset to GitHub: {he.code} - {he.read().decode()}")
        return False
    except Exception as ex:
        print(f"Unexpected error uploading to GitHub: {ex}")
        return False


def auto_archive_and_sync(date_str: Optional[str] = None, tag_name: str = DEFAULT_TAG) -> Optional[Path]:
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    archive = archive_evidence_for_date(date_str)
    if archive:
        upload_to_github_release(archive, tag_name=tag_name)
    return archive


if __name__ == "__main__":
    target_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Triggering auto-archive and sync for date: {target_date}")
    result = auto_archive_and_sync(target_date)
    if result:
        print(f"Archive file: {result}")
    else:
        print(f"No evidence folder found for date {target_date}.")
