#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# PM-skill installer
# Installs the Telegram task tracker skill into an OpenClaw workspace.
# Usage: curl -sSL https://raw.githubusercontent.com/OCBuilder6/PM-skill/main/install.sh | bash
# ─────────────────────────────────────────────────────────────────────────────

set -e

REPO="https://raw.githubusercontent.com/OCBuilder6/PM-skill/main/PM-skill"
OPENCLAW_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
CONFIG_FILE="$OPENCLAW_DIR/openclaw.json"
ENV_FILE="$OPENCLAW_DIR/.env"

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
CYAN="\033[0;36m"
RED="\033[0;31m"
NC="\033[0m"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        PM-skill Installer v1.3.0         ║${NC}"
echo -e "${CYAN}║   Telegram Task Tracker for OpenClaw     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Check OpenClaw is installed ───────────────────────────────────────────────
if ! command -v openclaw &>/dev/null; then
  echo -e "${RED}✗ OpenClaw is not installed or not in PATH.${NC}"
  echo "  Install it first: https://openclaw.ai"
  exit 1
fi
echo -e "${GREEN}✓ OpenClaw found${NC}"

# ── Detect workspace ──────────────────────────────────────────────────────────
if [ -n "$OPENCLAW_WORKSPACE" ]; then
  WORKSPACE="$OPENCLAW_WORKSPACE"
else
  # Try to detect from config
  WORKSPACE=$(python3 -c "
import json, os
try:
  with open('$CONFIG_FILE') as f:
    d = json.load(f)
  agents = d.get('agents', {}).get('list', [])
  for a in agents:
    if a.get('id') == 'tasks':
      ws = a.get('workspace', '')
      if ws: print(ws.replace('~', os.path.expanduser('~'))); exit()
  ws = d.get('agents', {}).get('defaults', {}).get('workspace', '')
  if ws: print(ws.replace('~', os.path.expanduser('~'))); exit()
except: pass
print('$OPENCLAW_DIR/workspace-tasks')
" 2>/dev/null)
fi

echo ""
echo -e "${YELLOW}Where should the skill be installed?${NC}"
echo -e "  Default: $WORKSPACE"
read -p "  Press Enter to accept or type a different path: " CUSTOM_WORKSPACE
if [ -n "$CUSTOM_WORKSPACE" ]; then
  WORKSPACE="$CUSTOM_WORKSPACE"
fi

SKILL_DIR="$WORKSPACE/skills/task-tracker"
mkdir -p "$SKILL_DIR/tools"
echo -e "${GREEN}✓ Workspace: $WORKSPACE${NC}"

# ── Download skill files ──────────────────────────────────────────────────────
echo ""
echo "Downloading skill files..."
FILES=(
  "SKILL.md"
  "agent.py"
  "skill.json"
  "requirements.txt"
  "openclaw.json"
  "tools/__init__.py"
  "tools/sheets.py"
  "tools/intent.py"
  "tools/telegram.py"
)

for f in "${FILES[@]}"; do
  dir=$(dirname "$SKILL_DIR/$f")
  mkdir -p "$dir"
  curl -sSL "$REPO/$f" -o "$SKILL_DIR/$f"
  echo -e "  ${GREEN}✓${NC} $f"
done

# ── Collect credentials ───────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}Now I need a few values to connect the skill to your accounts.${NC}"
echo -e "${CYAN}You'll need these before continuing:${NC}"
echo ""
echo "  1. A Telegram Bot Token (from @BotFather)"
echo "  2. Your Telegram group chat ID"
echo "  3. A Google Spreadsheet ID"
echo "  4. A Google Service Account JSON key"
echo "  5. An Anthropic API key"
echo ""

read -p "Telegram Bot Token: " TG_TOKEN
read -p "Telegram Group Chat ID (e.g. -1001234567890): " TG_GROUP_ID
read -p "Google Spreadsheet ID: " SHEET_ID
read -p "Sheet tab name (default: Tasks): " SHEET_TAB
SHEET_TAB="${SHEET_TAB:-Tasks}"
read -p "Anthropic API Key: " ANTHROPIC_KEY
echo "Paste your Google Service Account JSON (single line, then press Enter):"
read -r SA_JSON

# ── Write / update .env ───────────────────────────────────────────────────────
echo ""

# Remove existing PM-skill entries if present
if [ -f "$ENV_FILE" ]; then
  # Back up
  cp "$ENV_FILE" "$ENV_FILE.bak"
  # Remove old keys
  grep -v -E "TELEGRAM_BOT_TOKEN|TELEGRAM_ALLOWED_GROUP_ID|GOOGLE_SHEETS_ID|GOOGLE_SHEET_TAB|GOOGLE_SERVICE_ACCOUNT_JSON|ANTHROPIC_API_KEY" "$ENV_FILE" > /tmp/.env_clean || true
  mv /tmp/.env_clean "$ENV_FILE"
fi

cat >> "$ENV_FILE" <<ENVBLOCK

# PM-skill — added by installer
TELEGRAM_BOT_TOKEN=$TG_TOKEN
TELEGRAM_ALLOWED_GROUP_ID=$TG_GROUP_ID
GOOGLE_SHEETS_ID=$SHEET_ID
GOOGLE_SHEET_TAB=$SHEET_TAB
ANTHROPIC_API_KEY=$ANTHROPIC_KEY
GOOGLE_SERVICE_ACCOUNT_JSON=$SA_JSON
ENVBLOCK

echo -e "${GREEN}✓ Credentials written to $ENV_FILE${NC}"

# ── Update openclaw.json ──────────────────────────────────────────────────────
python3 - <<PYEOF
import json, sys

config_file = "$CONFIG_FILE"
group_id = "$TG_GROUP_ID"

try:
  with open(config_file) as f:
    d = json.load(f)
except:
  d = {}

# Ensure groupPolicy is open
tg = d.setdefault("channels", {}).setdefault("telegram", {})
tg["groupPolicy"] = "open"
tg.setdefault("groups", {})[group_id] = {"requireMention": False}

# Remove groupAllowFrom if present
tg.pop("groupAllowFrom", None)

with open(config_file, "w") as f:
  json.dump(d, f, indent=2)

print("✓ openclaw.json updated")
PYEOF

# ── Install Python deps ───────────────────────────────────────────────────────
echo ""
echo "Installing Python dependencies..."
if command -v pip3 &>/dev/null; then
  pip3 install -q -r "$SKILL_DIR/requirements.txt" && echo -e "${GREEN}✓ Python dependencies installed${NC}"
else
  echo -e "${YELLOW}⚠ pip3 not found — install manually: pip install -r $SKILL_DIR/requirements.txt${NC}"
fi

# ── Restart gateway ───────────────────────────────────────────────────────────
echo ""
echo "Restarting OpenClaw gateway..."
if openclaw gateway restart &>/dev/null; then
  sleep 2
  echo -e "${GREEN}✓ Gateway restarted${NC}"
else
  echo -e "${YELLOW}⚠ Could not restart gateway automatically. Run: openclaw gateway restart${NC}"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         PM-skill installed! 🎉            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}Next step:${NC} Share your Google Sheet with the service account email"
echo -e "  (find it inside your service account JSON under ${YELLOW}client_email${NC})"
echo -e "  Give it ${YELLOW}Editor${NC} access."
echo ""
echo -e "  Then send a message in your Telegram group and watch the sheet update!"
echo ""
