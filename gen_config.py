#!/usr/bin/env python3
"""Generate AstrBot data/cmd_config.json headlessly from env vars (cloud bootstrapping).

AstrBot auto-fills missing keys from DEFAULT_CONFIG at load, so we only write
our overrides. Secrets never touch disk in plaintext — injected via env at boot.

v2 fixes (2026-09-01):
- whitelist uses unified_msg_origin format: "telegram:FriendMessage:<id>"
  (raw IDs are NOT matched by the pipeline's WhitelistCheckStage)
- admins_id set to real Telegram IDs (string form)
- dashboard bound to 127.0.0.1, port 6185
- root path strategy: ASTRBOT_ROOT env must point at the dir CONTAINING data/
  (the workflow exports ASTRBOT_ROOT=$ASTRBOT_DATA_DIR/..)
"""
import json
import os

DATA_DIR = os.path.abspath(os.environ.get("ASTRBOT_DATA_DIR", "/tmp/astrbot-data"))

ADMIN_IDS = [x.strip() for x in os.environ.get("ASTRBOT_ADMIN_IDS", "6592796294,8439794110").split(",") if x.strip()]

# Whitelist entries: platform_id:message_type:session_id
WHITELIST = [f"telegram:FriendMessage:{i}" for i in ADMIN_IDS]

config = {
    # --- Provider: 9router OpenAI-compatible ---
    "provider": [
        {
            "id": "nine-router-flash",
            "provider": "openai",
            "type": "openai_chat_completion",
            "provider_type": "chat_completion",
            "enable": True,
            "model": os.environ.get("MODEL_NAME", "Flash-lite"),
            "key": ["$ROUTER_API_KEY"],  # env resolution built into AstrBot
            "api_base": os.environ.get(
                "ROUTER_URL", "https://9router-production-0a47.up.railway.app/v1"
            ),
            "timeout": 120,
            "custom_headers": {},
        }
    ],
    "provider_sources": [],
    "provider_settings": {
        "enable": True,
        "provider_pool": ["*"],
        "wake_prefix": "",
        "web_search": False,
        "streaming_response": False,
        "datetime_system_prompt": True,
    },
    # --- Platform: Telegram via long polling ---
    "platform": [
        {
            "id": "telegram",
            "type": "telegram",
            "enable": True,
            "telegram_token": os.environ.get("TG_BOT_TOKEN", ""),
            "start_message": "AstrBot on the cloud ☁️",
            "telegram_api_base_url": "https://api.telegram.org/bot",
            "telegram_file_base_url": "https://api.telegram.org/file/bot",
            "telegram_command_register": True,
            "telegram_command_auto_refresh": True,
            "telegram_command_register_interval": 300,
            "telegram_polling_restart_delay": 5.0,
        }
    ],
    # --- Routing: who answers by default ---
    "agent_runner": {
        "runner_type": "local",
        "config": {"model": {"provider_id": "nine-router-flash"}},
    },
    # --- Access control ---
    "platform_settings": {
        "unique_session": False,
        "rate_limit": {"time": 60, "count": 30, "strategy": "stall"},
        "enable_id_white_list": True,
        "id_whitelist": WHITELIST,
        "id_whitelist_log": True,
        "wl_ignore_admin_on_group": False,
        "wl_ignore_admin_on_friend": False,
        "reply_with_mention": False,
        "reply_with_quote": False,
        "no_permission_reply": True,
        "friend_message_needs_wake_prefix": False,
        "ignore_bot_self_message": True,
    },
    # --- Admins (string IDs, compared via str(event.get_sender_id())) ---
    "admins_id": ADMIN_IDS,
    # --- Persona ---
    "persona": [
        {
            "name": "default",
            "prompt": os.environ.get(
                "ASTRBOT_PERSONA",
                "You are AstrBot, a helpful, direct AI assistant on Telegram. "
                "Be concise, friendly, no fluff.",
            ),
            "begin_dialogs": [],
            "mood_imitation_dialogs": [],
        }
    ],
    # --- Dashboard: loopback only ---
    "dashboard": {
        "enable": True,
        "username": "admin",
        "password": os.environ.get("ASTRBOT_DASH_PASSWORD", "changeme-cloud"),
        "host": "127.0.0.1",
        "port": 6185,
    },
}

os.makedirs(DATA_DIR, exist_ok=True)
out = os.path.join(DATA_DIR, "cmd_config.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
print(f"[gen-config v2] wrote {out} ({os.path.getsize(out)} bytes)")
print(f"[gen-config v2] provider model: {config['provider'][0]['model']}")
print(f"[gen-config v2] tg token present: {bool(config['platform'][0]['telegram_token'])}")
print(f"[gen-config v2] admins: {config['admins_id']}")
print(f"[gen-config v2] whitelist: {config['platform_settings']['id_whitelist']}")
