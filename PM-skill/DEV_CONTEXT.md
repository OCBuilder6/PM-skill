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
   (routes to agent session by group ID)
        ↓
   AI agent (Claude via OpenClaw)
   reads AGENTS.md + SKILL.md as instructions
        ↓
   Runs Python tool via exec (tools/sheets.py)
   using Google Sheets API
        ↓
   Sheet row created/updated + colour coded
        ↓
   (Optional) Reply sent back to group
```

The AI layer is **OpenClaw** — it receives the Telegram message, runs the agent session, which reads the skill files and decides what to do. The Python tools handle only the Google Sheets interaction. The AI does the intent parsing; Claude (`claude-opus-4-5`) is called inside `tools/intent.py` for structured decisions.

---

## File structure

```
skills/task-tracker/
├── SKILL.md              ← Agent instructions (read by OpenClaw on every message)
├── agent.py              ← Core logic: workspace binding, tool registry, message handler
├── skill.json            ← Formal skill descriptor (env bindings, trigger filter)
├── requirements.txt      ← Python deps
├── tools/
│   ├── __init__.py
│   ├── sheets.py         ← All Google Sheets CRUD (create, update, list, flag, etc.)
│   ├── intent.py         ← LLM intent parser (calls Claude, returns JSON action)
│   └── telegram.py       ← Telegram send helpers (send_message, send_summary)
```

**AGENTS.md** (workspace root) — the agent's operating instructions. This is what the AI reads first on every message. Keep it accurate.

---

## Required environment variables

Set in `/home/ubuntu/.openclaw/.env`:

| Variable | What it is |
|---|---|
| `TELEGRAM_ALLOWED_GROUP_ID` | Telegram group chat ID the agent is bound to (e.g. `-5234910462`) |
| `GOOGLE_SHEET_TAB` | Tab name inside the Google Sheet to write to (e.g. `Tasks`) |
| `GOOGLE_SHEETS_ID` | Spreadsheet ID from the URL |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON of the Google service account key |
| `ANTHROPIC_API_KEY` | Anthropic API key (used by intent.py for Claude calls) |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |

The agent **refuses to start** if `TELEGRAM_ALLOWED_GROUP_ID` or `GOOGLE_SHEET_TAB` are missing.

---

## Workspace binding (important)

The agent is bound at startup to **one group** and **one sheet tab**. These never change at runtime:

- `TELEGRAM_ALLOWED_GROUP_ID` is enforced at two levels: OpenClaw's trigger filter drops non-matching messages before the agent sees them, and `agent.py` checks again as defence-in-depth.
- `GOOGLE_SHEET_TAB` is baked into every tool lambda in `agent.py` — it is never passed from user input.

To run a second instance for a different group or sheet, deploy a second agent with different env vars.

---

## OpenClaw config (openclaw.json)

The Telegram channel must have:

```json
"groupPolicy": "open",
"groups": {
  "-5234910462": {
    "requireMention": false
  }
}
```

- `groupPolicy: "open"` — allows all group members to trigger the agent (not just the owner). Required for the task tracker to work.
- `requireMention: false` — agent reads ALL messages in the group, not just @mentions.
- `groupAllowFrom` must **not** be set — if it is, only the listed sender IDs will get through and everyone else is silently dropped.

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
| `in_progress` | 🔵 Blue |
| `on_track` | 🟢 Green |
| `off_track` | 🟡 Amber |
| `blocked` | 🔴 Red |
| `done` | ✅ Dark grey |
| `cancelled` | ⛔ Pale |
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

## How the intent pipeline works

1. OpenClaw routes the group message to the agent session
2. The agent reads `SKILL.md` + `AGENTS.md` as instructions
3. It calls `tools/intent.py` → `parse_intent()` which sends the message + current task list to Claude and gets back a JSON decision: `{ action, params, reply }`
4. If action is set, the corresponding tool lambda in `agent.py` is called (with `sheet_tab` baked in)
5. If reply is set, `tools/telegram.py` → `send_message()` sends it back to the group

---

## Known gotchas

- **`groupAllowFrom` blocks everyone else** — if set, only those sender IDs get processed. Remove it entirely for task tracker use.
- **`sheet_tab` is never passed from user input** — it's always read from `GOOGLE_SHEET_TAB` env var. Don't add it to tool call params.
- **The Google service account email must be shared** on the spreadsheet with Editor access, or all sheet writes will fail silently.
- **`_find_row` uses fuzzy title matching** — "the landing page" will match a task titled "Landing Page Design". This is intentional but can cause false matches on very short task names.
- **NO_REPLY leak** — OpenClaw should suppress the NO_REPLY token silently, but on older builds it may briefly flash in the group chat. Update to the latest OpenClaw build to fix this.

---

## Version history

| Version | Changes |
|---|---|
| v1.0.0 | Initial skill — sheets.py, intent.py, basic agent.py |
| v1.1.0 | Workspace binding model (env-driven, defence-in-depth group guard); added `tools/telegram.py` (was missing); `skill.json`; `in_progress` + `cancelled` statuses; `filter_priority`; row colour coding; `get_sheet_summary` with unassigned tracking |

---

## Installing on a new agent

1. Copy `skills/task-tracker/` into the new agent's workspace
2. Set all required env vars in `.env`
3. Set `groupPolicy: "open"` and `requireMention: false` for the target group in `openclaw.json`
4. Ensure `groupAllowFrom` is **not** set (or remove it)
5. Share the Google Sheet with the service account email
6. Restart the OpenClaw gateway: `openclaw gateway restart`
