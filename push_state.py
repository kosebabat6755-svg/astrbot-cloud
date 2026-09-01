#!/usr/bin/env python3
"""Push AstrBot state (data/ dir) back to the repo every N minutes.

State = config, plugins, sessions DB. Secrets excluded (cmd_config.json holds
the TG token at runtime — we strip it before pushing).
"""
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "")
STATE_DIR = Path(os.environ.get("ASTRBOT_DATA_DIR", "/tmp/astrbot-data")).resolve()
INTERVAL_MIN = int(os.environ.get("STATE_PUSH_INTERVAL", "10"))
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


def get_ref_sha(branch: str) -> str | None:
    try:
        return gh("GET", f"/git/ref/heads/{branch}")["object"]["sha"]
    except Exception:
        return None


def push_file(path: Path, rel: str, message: str) -> None:
    content = path.read_bytes()
    payload = {
        "message": message,
        "content": base64.b64encode(content).decode(),
        "branch": BRANCH,
    }
    # check existing to update
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
    """Collect pushable files: small config/json/db files, skip caches and secrets."""
    out = []
    skip_parts = {"__pycache__", "logs", "temp", ".cache", "webchat"}
    for path in STATE_DIR.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(STATE_DIR)
        if any(p in skip_parts for p in rel.parts):
            continue
        # Skip files > 8MB (sessions DBs can grow; config/plugins stay small)
        if path.stat().st_size > 8 * 1024 * 1024:
            continue
        out.append((path, rel.as_posix()))
    return out


def main() -> None:
    print(f"[pusher] state dir: {STATE_DIR} | interval: {INTERVAL_MIN}m | branch: {BRANCH}")
    while True:
        try:
            files = snapshot()
            for path, rel in files:
                # Redact runtime secrets in cmd_config.json before pushing
                if rel == "cmd_config.json":
                    try:
                        cfg = json.loads(path.read_text(encoding="utf-8"))
                        for plat in cfg.get("platform", []):
                            if "telegram_token" in plat:
                                plat["telegram_token"] = "REDACTED"
                        for prov in cfg.get("provider", []):
                            if isinstance(prov.get("key"), list):
                                prov["key"] = ["REDACTED"]
                        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
                    except Exception as e:
                        print(f"[pusher] redact failed: {e}", file=sys.stderr)
                push_file(path, f"state/{rel}", f"state-sync: {rel}")
            print(f"[pusher] pushed {len(files)} files at {time.strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[pusher] cycle error: {e}", file=sys.stderr)
        time.sleep(INTERVAL_MIN * 60)


if __name__ == "__main__":
    main()
