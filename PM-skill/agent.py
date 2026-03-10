"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     TASKBOT — agent.py                                       ║
║                                                                              ║
║  Called by OpenClaw for every message that passes the trigger filter.        ║
║                                                                              ║
║  WORKSPACE BINDING (set once in .env, never changes at runtime):             ║
║    TELEGRAM_ALLOWED_GROUP_ID  →  the only group this agent listens to        ║
║    GOOGLE_SHEET_TAB           →  the only tab this agent writes to           ║
║                                                                              ║
║  OpenClaw handles routing. This file handles intent → tool → reply.          ║
║                                                                              ║
║  ⚠️  groupPolicy MUST be "open" in openclaw.json                             ║
║      Without it, OpenClaw sets groupAllowFrom:[deployer_id] and drops        ║
║      all other senders silently. See openclaw.json for the correct config.   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
from tools.sheets import (
    create_task, update_task_status, assign_task,
    add_comment, list_tasks, set_due_date,
    set_priority, flag_task, get_sheet_summary
)
from tools.intent import parse_intent
from tools.telegram import send_message


# ══════════════════════════════════════════════════════════════════════════════
#  WORKSPACE BINDING
#  Read at import time. Missing = hard exit before OpenClaw can route anything.
# ══════════════════════════════════════════════════════════════════════════════

BOUND_GROUP_ID  = os.environ.get("TELEGRAM_ALLOWED_GROUP_ID", "").strip()
BOUND_SHEET_TAB = os.environ.get("GOOGLE_SHEET_TAB", "").strip()

if not BOUND_GROUP_ID or not BOUND_SHEET_TAB:
    missing = []
    if not BOUND_GROUP_ID:
        missing.append("  TELEGRAM_ALLOWED_GROUP_ID  — Telegram group this agent listens to")
    if not BOUND_SHEET_TAB:
        missing.append("  GOOGLE_SHEET_TAB           — sheet tab this agent writes to")
    print("\n[TaskBot] ❌ Cannot start — workspace binding incomplete.\n")
    for m in missing:
        print(m)
    print("\nSet these in /home/ubuntu/.openclaw/.env then restart the gateway.\n")
    sys.exit(1)

print(f"[TaskBot] ✅ Bound group : {BOUND_GROUP_ID}")
print(f"[TaskBot] ✅ Bound tab   : {BOUND_SHEET_TAB}")


# ══════════════════════════════════════════════════════════════════════════════
#  TOOL REGISTRY
#  sheet_tab is baked into every lambda from BOUND_SHEET_TAB.
#  It is never passed from user input or tool call params.
# ══════════════════════════════════════════════════════════════════════════════

TOOLS = {
    "create_task": {
        "fn": lambda **kw: create_task(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Add a new task row to the sheet",
        "params": {
            "title":    "string — short task name",
            "owner":    "string — who is assigned (default: sender)",
            "due_date": "string — ISO date if mentioned, else blank",
            "priority": "string — high / medium / low (default: medium)"
        }
    },
    "update_task_status": {
        "fn": lambda **kw: update_task_status(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Change the status of an existing task",
        "params": {
            "task_ref": "string — task title or ID (fuzzy match)",
            "status":   "string — todo / in_progress / on_track / off_track / blocked / done / cancelled",
            "note":     "string — optional reason, appended to comments"
        }
    },
    "assign_task": {
        "fn": lambda **kw: assign_task(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Set or change who owns a task",
        "params": {
            "task_ref": "string — task title or ID",
            "owner":    "string — name or @handle"
        }
    },
    "add_comment": {
        "fn": lambda **kw: add_comment(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Append a timestamped note without changing task status",
        "params": {
            "task_ref": "string — task title or ID",
            "comment":  "string — the update to log"
        }
    },
    "list_tasks": {
        "fn": lambda **kw: list_tasks(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Read tasks from the sheet with optional filters",
        "params": {
            "filter_owner":    "string — filter by person (optional)",
            "filter_status":   "string — filter by status (optional)",
            "filter_priority": "string — filter by priority (optional)"
        }
    },
    "set_due_date": {
        "fn": lambda **kw: set_due_date(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Set or update a task's deadline",
        "params": {
            "task_ref": "string — task title or ID",
            "due_date": "string — new due date"
        }
    },
    "set_priority": {
        "fn": lambda **kw: set_priority(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Set or update the priority of an existing task",
        "params": {
            "task_ref": "string — task title or ID",
            "priority": "string — high / medium / low"
        }
    },
    "flag_task": {
        "fn": lambda **kw: flag_task(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Mark a task as needing attention — turns row bright red",
        "params": {
            "task_ref": "string — task title or ID",
            "reason":   "string — why it's being flagged"
        }
    },
    "get_sheet_summary": {
        "fn": lambda **kw: get_sheet_summary(sheet_tab=BOUND_SHEET_TAB),
        "description": "Return counts by status, overdue tasks, and flagged tasks",
        "params": {}
    }
}


# ══════════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT
#  The LLM decision layer — what action to take given a message.
#  Reads SKILL.md at runtime so prompt stays in sync with the skill file.
# ══════════════════════════════════════════════════════════════════════════════

def _load_skill_md() -> str:
    skill_path = os.path.join(os.path.dirname(__file__), "SKILL.md")
    try:
        with open(skill_path) as f:
            return f.read()
    except FileNotFoundError:
        return ""

SYSTEM_PROMPT = f"""You are TaskBot, a dedicated project coordination agent.

WORKSPACE (fixed — never changes):
  Telegram group : {BOUND_GROUP_ID}
  Sheet tab      : {BOUND_SHEET_TAB}

SKILL INSTRUCTIONS:
{_load_skill_md()}

Respond with ONLY a JSON object — no markdown, no explanation:
{{
  "action": "<tool_name or null>",
  "params": {{ <tool params or {{}}> }},
  "reply":  "<1-2 line chat confirmation, or null>"
}}

AVAILABLE TOOLS:
{json.dumps({{k: {{"description": v["description"], "params": v["params"]}} for k, v in TOOLS.items()}}, indent=2)}
"""


# ══════════════════════════════════════════════════════════════════════════════
#  MESSAGE HANDLER
#  Called by OpenClaw for each message that passes the trigger filter.
#  By the time we get here, OpenClaw has already validated the group binding.
#  We check again as defence-in-depth.
# ══════════════════════════════════════════════════════════════════════════════

def handle_message(event: dict) -> dict:
    """
    Process one Telegram message.

    OpenClaw calls this after routing. Expected event shape:
      {
        "message":    str  — raw message text
        "sender":     str  — display name or @handle
        "chat_id":    str  — Telegram chat ID
        "message_id": int  — Telegram message ID
      }
    """
    message      = event.get("message", "").strip()
    sender       = event.get("sender", "Unknown")
    chat_id      = str(event.get("chat_id", ""))
    message_id   = event.get("message_id")
    was_mentioned = event.get("was_mentioned", False)

    # Defence-in-depth group guard (OpenClaw trigger filter is the first layer)
    if chat_id != str(BOUND_GROUP_ID):
        print(f"[TaskBot] blocked — message from unbound group {chat_id}")
        return {"status": "blocked", "reason": "chat_id not in bound group"}

    if not message:
        return {"status": "skipped", "reason": "empty message"}

    # Fetch current tasks to give the LLM context
    try:
        current_tasks = list_tasks(sheet_tab=BOUND_SHEET_TAB)
    except Exception as e:
        print(f"[TaskBot] warning: could not fetch task list: {e}")
        current_tasks = []

    # Ask the LLM what to do
    decision = parse_intent(
        system_prompt=SYSTEM_PROMPT,
        message=message,
        sender=sender,
        tasks=current_tasks
    )

    if not decision:
        return {"status": "error", "reason": "intent parsing failed"}

    action = decision.get("action")
    params = decision.get("params", {})
    reply  = decision.get("reply")

    # Execute tool (sheet_tab is baked into the lambda — not from params)
    result = {"status": "no_action"}
    if action and action in TOOLS:
        try:
            if action == "create_task" and "owner" not in params:
                params["owner"] = sender

            tool_result = TOOLS[action]["fn"](**params)
            result = {"status": "ok", "tool": action, "result": tool_result}
            print(f"[TaskBot] ✅ {action} → {tool_result}")

        except Exception as e:
            result = {"status": "tool_error", "tool": action, "error": str(e)}
            reply  = f"⚠️ I understood your update but had trouble saving it: {e}"
            print(f"[TaskBot] ❌ {action} failed: {e}")

    # Reply only when directly @mentioned — silent for all other actions
    if was_mentioned and reply:
        send_message(chat_id=chat_id, text=reply, reply_to=message_id)

    return result
