# PM-skill

AI-powered Telegram task tracker skill for [OpenClaw](https://openclaw.ai).

Monitors a Telegram group and automatically syncs task updates to a Google Sheet — no commands, just natural conversation.

---

## What this is

A dedicated AI agent that monitors a Telegram group and keeps a Google Sheet task tracker up to date automatically. Team members talk naturally in the group — the agent reads every message, decides if it's task-related, and calls the right tool to update the sheet. No commands, no forms.

---

## How it works

```
Telegram group message
        ↓
   OpenClaw gateway
   (routes to agent session by group ID — configured in openclaw.json)
        ↓
   AI agent (Claude via OpenClaw)
   reads AGENTS.md + skills/task-tracker/SKILL.md as instructions
        ↓
   Calls handle_message() in skills/task-tracker/agent.py
        ↓
   Runs Python tool via tools/sheets.py
   using Google Sheets API
        ↓
   Sheet row created/updated + colour coded
```

OpenClaw is the AI layer. It receives the Telegram message, runs the agent session, reads the skill files, and decides what to do. Python tools handle only the Google Sheets interaction. Intent parsing is in `tools/intent.py` which calls `claude-opus-4-5`.

---

## File structure

```
PM-skill/
├── AGENTS.md          ← Agent operating instructions (read on every message)
├── SKILL.md           ← Skill instructions: tools, mappings, examples
├── agent.py           ← Workspace binding, tool registry, message handler
├── skill.json         ← Formal skill descriptor
├── requirements.txt
├── openclaw.json      ← OpenClaw config template (groupPolicy, trigger, group binding)
├── .env.example       ← Copy to .openclaw/.env and fill in your values
└── tools/
    ├── __init__.py
    ├── sheets.py      ← All Google Sheets CRUD
    ├── intent.py      ← LLM intent parser (returns JSON action decision)
    └── telegram.py    ← send_message, send_summary
```

---

## Required environment variables

Set in your `~/.openclaw/.env` (see `.env.example` for a full template):

| Variable | What it is |
|---|---|
| `TELEGRAM_ALLOWED_GROUP_ID` | Telegram group chat ID the agent is bound to (e.g. `-5234910462`) |
| `GOOGLE_SHEET_TAB` | Tab name inside the Google Sheet to write to (e.g. `Tasks`) |
| `GOOGLE_SHEETS_ID` | Spreadsheet ID from the URL |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON of the Google service account key |
| `ANTHROPIC_API_KEY` | Anthropic API key (used by intent.py) |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |

The agent **refuses to start** if `TELEGRAM_ALLOWED_GROUP_ID` or `GOOGLE_SHEET_TAB` are missing.

---

## OpenClaw config

The `openclaw.json` at the root is a config template. Key settings:

```json
{
  "telegram": {
    "groupPolicy": "open",
    "groups": {
      "${TELEGRAM_ALLOWED_GROUP_ID}": {
        "requireMention": false
      }
    }
  }
}
```

- **`groupPolicy: "open"`** — allows ALL group members to trigger the agent. **Required.** Without it, OpenClaw defaults to `groupAllowFrom:[<deployer_id>]` and silently drops every other sender's messages.
- **`requireMention: false`** — agent reads ALL messages, not just @mentions.
- **`groupAllowFrom` must NOT be set** — if present, only listed sender IDs get through.

---

## Workspace binding

The agent is bound at startup to **one group** and **one sheet tab**:

- `TELEGRAM_ALLOWED_GROUP_ID` is enforced at two levels: OpenClaw's trigger filter drops non-matching groups first; `agent.py` checks again as defence-in-depth.
- `GOOGLE_SHEET_TAB` is baked into every tool lambda in `agent.py` — never passed from user input.

To run a second instance for a different group or sheet, deploy a second agent with different env vars.

---

## Sheet structure (auto-created on first run)

| Col | Field | Notes |
|---|---|---|
| A | Task ID | Auto-generated: T001, T002… |
| B | Title | Task name |
| C | Owner | Person responsible |
| D | Status | Colour-coded |
| E | Priority | high / medium / low |
| F | Due Date | ISO date |
| G | Last Updated | Auto-timestamp |
| H | Comments | Appended chat updates |
| I | Flagged | Escalation notes (🚩) |

### Status values and row colours

| Status | Colour |
|---|---|
| `todo` | ⬜ Grey |
| `in_progress` | 🔵 Light blue |
| `on_track` | 🟢 Light green |
| `off_track` | 🟡 Amber |
| `blocked` | 🔴 Light red |
| `done` | ✅ Dark grey |
| `cancelled` | ⛔ Pale grey |
| Flagged | 🚩 Bright red override |

---

## Installing

1. Clone this repo and copy the `PM-skill/` folder into your OpenClaw workspace
2. Copy `.env.example` → `~/.openclaw/.env` and fill in your values
3. Merge `openclaw.json` settings into your `~/.openclaw/openclaw.json`
4. Confirm `groupPolicy: "open"` and `requireMention: false` for your group
5. Confirm `groupAllowFrom` is **not** set (it silently blocks all other senders)
6. Share the Google Sheet with the service account email (Editor access)
7. Restart the gateway: `openclaw gateway restart`

---

## Running tools manually

```bash
cd PM-skill && \
  set -a && source ~/.openclaw/.env && set +a && \
  python3 -c "
import sys, json
sys.path.insert(0, '.')
from tools.sheets import get_sheet_summary
print(json.dumps(get_sheet_summary(), indent=2))
"
```

---

## Known gotchas

- **`groupAllowFrom` blocks everyone else** — if set, only those sender IDs are processed. Remove it entirely.
- **`groupPolicy` defaults to restricted** — always set `"open"` explicitly for group-chat skills.
- **`sheet_tab` is never from user input** — always from `GOOGLE_SHEET_TAB` env var. Don't add it to tool call params.
- **Service account must have Editor access** on the spreadsheet or all sheet writes fail silently.
- **`_find_row` uses fuzzy title matching** — intentional, but very short task names can cause false matches.
- **NO_REPLY leak** — on older OpenClaw builds the `NO_REPLY` token may flash briefly in chat. Update to the latest build.

---

## Credits

Built by [Benjamin Coste](https://www.linkedin.com/in/benjamincoste/en/)

---

## Version history

| Version | Changes |
|---|---|
| v1.0.0 | Initial skill |
| v1.1.0 | Workspace binding model; defence-in-depth group guard; `tools/telegram.py`; `skill.json`; extra statuses; row colour coding |
| v1.2.0 | Restructured to correct OpenClaw file layout; `groupPolicy:open` + `requireMention:false` explicit; `DEV_CONTEXT.md` added |
| v1.3.0 | `set_priority` tool added; task removal policy (cancelled as default); absolute silence rule in group chat; DEV_CONTEXT merged into README |
