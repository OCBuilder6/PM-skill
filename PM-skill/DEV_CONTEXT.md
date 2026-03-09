# DEV_CONTEXT.md — Task Tracker AI Skill
### Context for developers installing or extending this skill

---

## What this is

A dedicated AI agent that monitors a Telegram group and keeps a Google Sheet task tracker up to date automatically. Team members talk naturally in the group — the agent reads every message, decides if it's task-related, and calls the right tool to update the sheet. No commands, no forms.

---

## Architecture

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
        ↓
   Reply sent back to group (via tools/telegram.py)
```

OpenClaw is the AI layer. It receives the Telegram message, runs the agent session, reads the skill files, and decides what to do. Python tools handle only the Google Sheets interaction. Intent parsing is in `tools/intent.py` which calls `claude-opus-4-5`.

---

## File structure

```
pm-skill/                          ← workspace root
├── AGENTS.md                      ← Agent operating instructions (read on every message)
├── openclaw.json                  ← OpenClaw config: groupPolicy, trigger, group binding
├── .env.example                   → copy to /home/ubuntu/.openclaw/.env
└── skills/
    └── task-tracker/
        ├── SKILL.md               ← Skill instructions: tools, mappings, examples
        ├── agent.py               ← Workspace binding, tool registry, message handler
        ├── skill.json             ← Formal skill descriptor
        ├── requirements.txt
        └── tools/
            ├── __init__.py
            ├── sheets.py          ← All Google Sheets CRUD
            ├── intent.py          ← LLM intent parser (returns JSON action decision)
            └── telegram.py        ← send_message, send_summary
```

---

## Required environment variables

Set in `/home/ubuntu/.openclaw/.env`:

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

## OpenClaw config (openclaw.json)

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

- **`groupPolicy: "open"`** — allows ALL group members to trigger the agent. **This is required.** Without it, OpenClaw defaults to `groupAllowFrom:[<deployer_id>]` and silently drops every other sender's messages.
- **`requireMention: false`** — agent reads ALL messages, not just @mentions.
- **`groupAllowFrom` must NOT be set** — if present, only the listed sender IDs get through.

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

## Running tools manually

```bash
cd /home/ubuntu/.openclaw/workspace-tasks/skills/task-tracker && \
  export $(grep -E 'GOOGLE_|TELEGRAM_ALLOWED_GROUP_ID|GOOGLE_SHEET_TAB' /home/ubuntu/.openclaw/.env | xargs -d '\n') && \
  python3 -c "
import sys, json, os
sys.path.insert(0, '.')
from tools.sheets import get_sheet_summary
print(json.dumps(get_sheet_summary(), indent=2))
"
```

---

## Installing on a new agent

1. Copy `skills/task-tracker/` into the agent's workspace at the correct path
2. Copy `AGENTS.md` and `openclaw.json` to the workspace root
3. Set all required env vars in `/home/ubuntu/.openclaw/.env`
4. Confirm `openclaw.json` has `groupPolicy: "open"` and `requireMention: false`
5. Confirm `groupAllowFrom` is **not** set anywhere
6. Share the Google Sheet with the service account email (Editor access)
7. Restart the gateway: `openclaw gateway restart`

---

## Known gotchas

- **`groupAllowFrom` blocks everyone else** — if set, only those sender IDs are processed. Remove it entirely.
- **`groupPolicy` defaults to restricted** — always set `"open"` explicitly for group-chat skills.
- **`sheet_tab` is never from user input** — always from `GOOGLE_SHEET_TAB` env var. Don't add it to tool call params.
- **Service account must have Editor access** on the spreadsheet or all sheet writes fail silently.
- **`_find_row` uses fuzzy title matching** — intentional, but very short task names can cause false matches.
- **NO_REPLY leak** — on older OpenClaw builds the `NO_REPLY` token may flash briefly in chat. Update to the latest build.

---

## Version history

| Version | Changes |
|---|---|
| v1.0.0 | Initial skill |
| v1.1.0 | Workspace binding model; defence-in-depth group guard; `tools/telegram.py`; `skill.json`; extra statuses; row colour coding |
| v1.2.0 | Restructured to correct OpenClaw file layout (`AGENTS.md`, `SKILL.md`, `openclaw.json`); `groupPolicy:open` + `requireMention:false` set explicitly to prevent sender-allowlist bug; removed `webhook_server.py` (OpenClaw handles routing); `DEV_CONTEXT.md` updated to match real architecture |
