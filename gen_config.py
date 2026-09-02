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
import hashlib
import json
import os
import secrets

DATA_DIR = os.path.abspath(os.environ.get("ASTRBOT_DATA_DIR", "/tmp/astrbot-data"))


def _pbkdf2_dashboard(raw: str) -> str:
    """Hash exactly like astrbot.core.utils.auth_password.hash_dashboard_password."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", raw.encode(), bytes.fromhex(salt), 600_000
    ).hex()
    return f"pbkdf2_sha256$600000${salt}${digest}"

ADMIN_IDS = [x.strip() for x in os.environ.get("ASTRBOT_ADMIN_IDS", "6592796294,8439794110").split(",") if x.strip()]

# Whitelist entries: platform_id:message_type:session_id
# Boss DMs (both his accounts) + his group بره (-1001635507223)
WHITELIST = [f"telegram:FriendMessage:{i}" for i in ADMIN_IDS]
WHITELIST.append("telegram:GroupMessage:-1001635507223")

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
        },
        # --- Voice provider (STT only: Groq Whisper API — TTS intentionally OFF per Boss) ---
        {
            "id": "groq_whisper",
            "provider": "openai",
            "type": "openai_whisper_api",
            "provider_type": "speech_to_text",
            "enable": True,
            # literal key required: whisper source reads api_key raw. Never
            # persisted — cmd_config.json is excluded from state sync.
            "api_key": os.environ.get("GROQ_API_KEY", ""),
            "api_base": "https://api.groq.com/openai/v1",
            "model": "whisper-large-v3-turbo",
            "proxy": "",
        },
    ],
    "provider_sources": [],
    "provider_settings": {
        "enable": True,
        "provider_pool": ["*"],
        "wake_prefix": "",
        "web_search": True,
        "websearch_provider": "tavily",
        # literal key required: web search tools read this raw (no $env resolution
        # outside provider manager). Value lives only on the runner — cmd_config.json
        # is never pushed to the state branch.
        "websearch_tavily_key": [os.environ.get("TAVILY_API_KEY", "")],
        "web_search_link": True,
        "streaming_response": False,
        "datetime_system_prompt": True,
        "show_tool_use_status": True,
    },
    # --- t2i: TOP-LEVEL keys in v4.28 (not under provider_settings) ---
    "t2i": True,
    "t2i_word_threshold": 150,
    # --- Voice settings: STT only (Groq Whisper in). TTS OFF per Boss. ---
    "provider_stt_settings": {
        "enable": True,
        "provider_id": "groq_whisper",
    },
    "provider_tts_settings": {
        "enable": False,
        "provider_id": "",
        "dual_output": False,
        "use_file_service": False,
        "trigger_probability": 1.0,
    },
    # --- Image understanding (bot describes photos you send) ---
    "provider_ltm_settings": {
        "group_icl_enable": False,
        "group_message_max_cnt": 100,
        "image_caption": True,
        "image_caption_provider_id": "nine-router-flash",
        "group_message_history_enable": False,
        "group_message_history_max_cnt": 100,
        "active_reply": {
            "enable": False,
            "method": "possibility_reply",
            "possibility_reply": 0.1,
            "whitelist": [],
        },
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
        "reply_with_quote": True,
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
}

# --- Dashboard: loopback only (cloudflared tunnel exposes it publicly) ---
# v4.28 auth: login compares against pbkdf2_password (preferred) or the md5
# hex in `password`. We pre-hash the secret here in the exact server format
# — plaintext in this field can NEVER log in (verify_dashboard_password only
# understands md5/pbkdf2 hashes) and the ASTRBOT_DASHBOARD_INITIAL_PASSWORD
# reset path would print the secret into the boot log (public state branch).
_dash_pw = os.environ.get("ASTRBOT_DASH_PASSWORD", "")
config["dashboard"] = {
    "enable": True,
    "username": os.environ.get("ASTRBOT_DASH_USER", "mamad"),
    "password": hashlib.md5(_dash_pw.encode()).hexdigest() if _dash_pw else "",
    "pbkdf2_password": _pbkdf2_dashboard(_dash_pw) if _dash_pw else "",
    "password_storage_upgraded": bool(_dash_pw),
    "host": "127.0.0.1",
    "port": 6185,
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
