#!/usr/bin/env bash
# Starts a cloudflared quick tunnel to the AstrBot dashboard (port 6185),
# writes the public URL to the data dir (state-synced to Git), and DMs the
# URL + credentials to every admin via the Telegram bot API.
set -u

DATA_DIR="${ASTRBOT_DATA_DIR:-/tmp/astrbot-data}"
TG_TOKEN="${TG_BOT_TOKEN:-}"
ADMINS="${ASTRBOT_ADMIN_IDS:-6592796294}"
DASH_USER="admin"
DASH_PASS="${DASH_PASSWORD:-changeme-cloud}"
DASH_PORT="${DASH_PORT:-6185}"

mkdir -p "$DATA_DIR"

# 1. download cloudflared (amd64)
CF=/tmp/cloudflared
for i in 1 2 3; do
  if curl -sL --max-time 120 -o "$CF" "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"; then
    break
  fi
  sleep 5
done
chmod +x "$CF" || { echo "cloudflared download failed" | tee "$DATA_DIR/gui_tunnel.log"; exit 1; }

# 2. start quick tunnel (free, no account, CF edge = Iran-friendly)
nohup "$CF" tunnel --url "http://127.0.0.1:${DASH_PORT}" --no-autoupdate > /tmp/cloudflared.log 2>&1 &

# 3. wait for the random URL to appear in the log
URL=""
for i in $(seq 1 60); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cloudflared.log | head -1)
  [ -n "$URL" ] && break
  sleep 2
done

if [ -z "$URL" ]; then
  { echo "tunnel failed to start"; tail -20 /tmp/cloudflared.log; } | tee "$DATA_DIR/gui_tunnel.log"
  exit 1
fi

echo "$URL" > "$DATA_DIR/webui_url.txt"

# 4. DM the credentials to all admins
TEXT="🌩 AstrBot WebUI is LIVE

${URL}

user: ${DASH_USER}
pass: ${DASH_PASS}

Note: the URL changes every ~5h shift — this bot re-sends the fresh link each boot."

IFS=',' read -ra IDS <<< "$ADMINS"
for id in "${IDS[@]}"; do
  curl -s --max-time 20 -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
    -d chat_id="$id" --data-urlencode "text=$TEXT" > /dev/null 2>&1
done

{
  echo "tunnel up: $URL"
  echo "DM'd admins: $ADMINS"
} | tee "$DATA_DIR/gui_tunnel.log"
