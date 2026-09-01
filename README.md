# AstrBot on GitHub Actions ☁️🤖

**$0/month, zero local processes.** AstrBot (39.9k⭐ Telegram/Discord AI framework)
runs as a GitHub Actions cron job, 24/7 coverage via 5-hour shifts + state sync.

## How it works
| Piece | File | Role |
|---|---|---|
| Cron workflow | `.github/workflows/astrbot.yml` | Every 5h: boot → run 4h45m → exit |
| Config generator | `gen_config.py` | Writes `data/cmd_config.json` from secrets |
| State pusher | `push_state.py` | Pushes config/sessions/plugins to `state` branch every 10min |
| State restore | workflow step | Next run pulls the `state` branch → continuity |

## Provider
- **API:** 9router (OpenAI-compatible) → model `Flash-lite`
- **Bot:** AradAminiForwardBot (long polling)

## Access
Whitelist ON — only these Telegram IDs can talk to it:
`6592796294` (@mokingh), `8439794110` (@alidabigpoly)

## Secrets required
- `TG_BOT_TOKEN` — Telegram bot token
- `ROUTER_API_KEY` — 9router API key
- `ROUTER_URL` — `https://9router-production-0a47.up.railway.app/v1`
- `ASTRBOT_ADMIN_IDS` — comma-separated admin Telegram IDs

## Manual deploy
```bash
gh workflow run astrbot.yml --repo balsicl1234/astrbot-cloud
gh run watch --repo balsicl1234/astrbot-cloud
```
