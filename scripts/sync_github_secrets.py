"""
Automated synchronization of .env secrets to GitHub Actions Repository Secrets.
Uses GitHub REST API and LibSodium public-key encryption.
"""

import os
import sys
import json
import subprocess
from base64 import b64encode
import urllib.request
import urllib.error
from pathlib import Path

from nacl import encoding, public
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent


def get_git_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n",
        capture_output=True,
        text=True,
        check=True
    )
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("Could not find GitHub token in environment or git credentials.")


def encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    pub_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder)  # type: ignore
    sealed_box = public.SealedBox(pub_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")


def sync_secrets():
    owner = "HemantJagnani"
    repo = "SIH2026"
    token = get_git_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "APIx-Automator"
    }

    # 1. Fetch Repo Public Key
    key_url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key"
    req = urllib.request.Request(key_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        key_data = json.loads(resp.read().decode())

    public_key = key_data["key"]
    key_id = key_data["key_id"]
    print(f"Retrieved GitHub public key (id: {key_id}) for {owner}/{repo}")

    # 2. Secrets to push
    env_file = ROOT / ".env"
    env_dict = dotenv_values(env_file)

    target_keys = [
        "DATABASE_URL",
        "DATABASE_URL_SYNC",
        "REDIS_URL",
        "GEMINI_API_KEY",
        "IGNAV_API_KEY"
    ]

    for k in target_keys:
        val = env_dict.get(k) or os.environ.get(k)
        if not val:
            print(f"Skipping {k}: no value found in .env")
            continue

        encrypted_val = encrypt_secret(public_key, val)
        secret_url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{k}"
        payload = json.dumps({
            "encrypted_value": encrypted_val,
            "key_id": key_id
        }).encode("utf-8")

        put_req = urllib.request.Request(
            secret_url,
            data=payload,
            headers={**headers, "Content-Type": "application/json"},
            method="PUT"
        )

        try:
            with urllib.request.urlopen(put_req) as p_resp:
                status = p_resp.status
                print(f"Successfully synced secret '{k}' to GitHub Actions (status {status})")
        except urllib.error.HTTPError as e:
            print(f"Failed to set secret '{k}': {e.code} - {e.read().decode()}")

    print("\nAll GitHub Actions secrets are now configured automatically!")


if __name__ == "__main__":
    sync_secrets()
