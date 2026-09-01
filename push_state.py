#!/usr/bin/env python3
"""Push AstrBot state (data/ dir) back to the repo every N minutes.

State = database, knowledge base, plugins, conversation sessions.
cmd_config.json is NEVER pushed or modified (it is generated fresh on every boot from GitHub Secrets).
"""
import base64
import json
import os
import sys
import time
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "")
STATE_DIR = Path(os.environ.get("ASTRBOT_DATA_DIR", "/tmp/astrbot-data")).resolve()
INTERVAL_MIN = int(os.environ.get("STATE_PUSH_INTERVAL", "1"))
BRANCH = os.environ.get("STATE_BRANCH", "state")
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")

API = f"https://api.github.com/repos/{REPO}"


def gh(method: str, url: str, body: dict | None = None) -> dict:
    import urllib.request

    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}{url}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "astrbot-cloud-pusher",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode() or "{}")


def push_file(path: Path, rel: str, message: str) -> None:
    content = path.read_bytes()
    payload = {
        "message": message,
        "content": base64.b64encode(content).decode(),
        "branch": BRANCH,
    }
    # check existing to update sha
    try:
        existing = gh("GET", f"/contents/{rel}?ref={BRANCH}")
        payload["sha"] = existing["sha"]
    except Exception:
        pass
    try:
        gh("PUT", f"/contents/{rel}", payload)
    except Exception as e:
        print(f"[pusher] failed {rel}: {e}", file=sys.stderr)


def snapshot() -> list[tuple[Path, str]]:
    """Collect pushable files: db, kb, plugins, logs. Skip caches, temps, and cmd_config.json."""
    out = []
    skip_parts = {"__pycache__", "temp", ".cache", "webchat", "dist"}
    for path in STATE_DIR.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(STATE_DIR)
        if any(p in skip_parts for p in rel.parts):
            continue
        # NEVER push cmd_config.json — secrets are injected from GitHub Secrets on each boot
        if path.name == "cmd_config.json":
            continue
        # NEVER push dist/ — AstrBot bundles a matching dashboard dist in its own
        # package every release. Restoring an old dist mixes chunk hashes across
        # versions (franken-dist) and 404s the WebUI after login.
        if rel.parts[0] == "dist":
            continue
        # Skip files > 12MB
        if path.stat().st_size > 12 * 1024 * 1024:
            continue
        out.append((path, rel.as_posix()))
    return out


def main() -> None:
    print(f"[pusher] state dir: {STATE_DIR} | interval: {INTERVAL_MIN}m | branch: {BRANCH}")
    # Initial sleep to allow AstrBot to finish initial boot safely
    time.sleep(15)
    while True:
        try:
            files = snapshot()
            for path, rel in files:
                push_file(path, f"state/{rel}", f"state-sync: {rel}")
            print(f"[pusher] pushed {len(files)} files at {time.strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[pusher] cycle error: {e}", file=sys.stderr)
        time.sleep(INTERVAL_MIN * 60)


if __name__ == "__main__":
    main()
