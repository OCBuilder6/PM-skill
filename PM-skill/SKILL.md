# SKILL.md — Task Tracker Skill

This skill monitors a Telegram group and keeps a Google Sheet task tracker in sync with what the team says in chat.

---

## What you do with each message

1. Read the message and the sender's name
2. Check the current task list (`list_tasks`)
3. Decide if the message is task-related
4. If yes: call the right tool — then return NO_REPLY. Never confirm in chat.
5. If no: return `NO_REPLY`

---

## Tool reference

All tools are in `tools/sheets.py`. The `sheet_tab` parameter is always pre-filled from the `GOOGLE_SHEET_TAB` env var — do not pass it from user input.

### `create_task(title, owner, due_date, priority)`
Add a new row to the sheet.
- `title` — short task name extracted from the message
- `owner` — person assigned; default to sender if not named
- `due_date` — ISO date if mentioned, otherwise blank
- `priority` — `high` / `medium` / `low`; default `medium`

### `update_task_status(task_ref, status, note)`
Change the status of an existing task.
- `task_ref` — task title or ID (fuzzy match is fine)
- `status` — one of: `todo` / `in_progress` / `on_track` / `off_track` / `blocked` / `done` / `cancelled`
- `note` — optional reason; appended to comments column

### `assign_task(task_ref, owner)`
Change who owns a task.

### `add_comment(task_ref, comment)`
Append a timestamped note to a task without changing its status.

### `list_tasks(filter_owner, filter_status, filter_priority)`
Read tasks from the sheet. All filters optional.

### `set_due_date(task_ref, due_date)`
Set or update a task's deadline.

### `set_priority(task_ref, priority)`
Set or update the priority of a task. Use when someone says "high priority", "urgent", "critical", "bump this up", "low priority", "backlog", etc.
- `priority` — `high` / `medium` / `low`

### `flag_task(task_ref, reason)`
Mark a task as needing attention. Turns the row bright red in the sheet.

### `get_sheet_summary()`
Return total count, counts by status, overdue tasks, and flagged tasks.

---

## Sheet columns (auto-created on first run)

| Col | Field | Notes |
|---|---|---|
| A | Task ID | Auto: T001, T002… |
| B | Title | Task name |
| C | Owner | Person responsible |
| D | Status | Colour-coded (see below) |
| E | Priority | high / medium / low |
| F | Due Date | ISO date |
| G | Last Updated | Auto-timestamp |
| H | Comments | Appended updates |
| I | Flagged | 🚩 Escalation notes |

### Row colours by status

| Status | Colour |
|---|---|
| `todo` | ⬜ Grey |
| `in_progress` | 🔵 Light blue |
| `on_track` | 🟢 Light green |
| `off_track` | 🟡 Amber |
| `blocked` | 🔴 Light red |
| `done` | ✅ Dark grey |
| `cancelled` | ⛔ Pale grey |
| Flagged (any status) | 🚩 Bright red override |

---

## Example message → action mappings

| Message | Tool called |
|---|---|
| "I've finished the homepage design" | `update_task_status(task_ref="homepage design", status="done")` |
| "The API work is blocked, waiting on credentials" | `update_task_status(task_ref="API", status="blocked", note="waiting on credentials")` |
| "Add a task: write Q3 comms plan, owner Sarah, due 30th" | `create_task(title="Q3 comms plan", owner="Sarah", due_date="2025-01-30")` |
| "Can you assign the DB migration to Marcus?" | `assign_task(task_ref="DB migration", owner="Marcus")` |
| "The launch plan is on track for Friday" | `update_task_status(task_ref="launch plan", status="on_track")` |
| "What's everyone working on?" | `list_tasks()` |
| "Give me a summary" | `get_sheet_summary()` |
| "Lunch at 1pm anyone?" | `NO_REPLY` |
