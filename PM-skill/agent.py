"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        TASKBOT — DEDICATED AGENT                            ║
║                                                                              ║
║  This agent has a fixed identity and a fixed workspace.                      ║
║  It is bound at deploy time to:                                              ║
║                                                                              ║
║    • ONE Telegram group  →  TELEGRAM_ALLOWED_GROUP_ID                        ║
║    • ONE Google Sheet tab →  GOOGLE_SHEET_TAB                                ║
║                                                                              ║
║  It does nothing else. It listens to no other group. It writes to no         ║
║  other sheet. These bindings are set once in .env and never change.          ║
║                                                                              ║
║  To deploy a second instance for a different group or sheet,                 ║
║  run a second copy of this skill with different env vars.                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

OpenClaw implementation note
─────────────────────────────
When registering this skill, create a DEDICATED AGENT (not a shared/generic one)
with its own isolated workspace. Bind the agent to:

  agent.workspace.bound_group     = env.TELEGRAM_ALLOWED_GROUP_ID
  agent.workspace.bound_sheet_tab = env.GOOGLE_SHEET_TAB

These are declared in skill.json under agent.workspace. The trigger filter in
skill.json (trigger.filter.chat_id) enforces the group binding at the platform
level. This file enforces it again at the application level as a second layer.
"""

import os
import sys
import json
from tools.sheets import (
    create_task, update_task_status, assign_task,
    add_comment, list_tasks, set_due_date,
    flag_task, get_sheet_summary
)
from tools.intent import parse_intent
from tools.telegram import send_message


# ══════════════════════════════════════════════════════════════════════════════
#  WORKSPACE BINDING
#  Read once at startup. These are the agent's entire operational scope.
#  If either is missing, the agent refuses to start.
# ══════════════════════════════════════════════════════════════════════════════

BOUND_GROUP_ID = os.environ.get("TELEGRAM_ALLOWED_GROUP_ID", "").strip()
BOUND_SHEET_TAB = os.environ.get("GOOGLE_SHEET_TAB", "").strip()

if not BOUND_GROUP_ID or not BOUND_SHEET_TAB:
    missing = []
    if not BOUND_GROUP_ID:
        missing.append("  TELEGRAM_ALLOWED_GROUP_ID  (the Telegram group this agent listens to)")
    if not BOUND_SHEET_TAB:
        missing.append("  GOOGLE_SHEET_TAB           (the sheet tab this agent writes to)")
    print("\n[TaskBot] ❌ Cannot start — workspace binding incomplete.\n")
    print("Set these environment variables before deploying:\n")
    for m in missing:
        print(m)
    print("\nSee skill.json → env_required for details.\n")
    sys.exit(1)

print(f"[TaskBot] ✅ Bound to Telegram group : {BOUND_GROUP_ID}")
print(f"[TaskBot] ✅ Bound to sheet tab      : {BOUND_SHEET_TAB}")


# ══════════════════════════════════════════════════════════════════════════════
#  TOOL REGISTRY
#  What this agent can do. sheet_tab is always BOUND_SHEET_TAB — never
#  passed in from outside, never overridable at runtime.
# ══════════════════════════════════════════════════════════════════════════════

TOOLS = {
    "create_task": {
        "fn": lambda **kw: create_task(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Add a new task row to the sheet",
        "params": {
            "title":    "string — short task name",
            "owner":    "string — who is assigned (name or @handle)",
            "due_date": "string — due date if mentioned (ISO format or natural language)",
            "priority": "string — high / medium / low (default: medium)"
        }
    },
    "update_task_status": {
        "fn": lambda **kw: update_task_status(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Change the status of an existing task",
        "params": {
            "task_ref": "string — task title or ID",
            "status":   "string — one of: todo / in_progress / on_track / off_track / blocked / done / cancelled",
            "note":     "string — optional reason or context"
        }
    },
    "assign_task": {
        "fn": lambda **kw: assign_task(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Assign or reassign a task to someone",
        "params": {
            "task_ref": "string — task title or ID",
            "owner":    "string — name or @handle to assign to"
        }
    },
    "add_comment": {
        "fn": lambda **kw: add_comment(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Log a comment or update against a task without changing its status",
        "params": {
            "task_ref": "string — task title or ID",
            "comment":  "string — what was said / the update"
        }
    },
    "list_tasks": {
        "fn": lambda **kw: list_tasks(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Retrieve tasks from the sheet, optionally filtered",
        "params": {
            "filter_owner":    "string — filter by person (optional)",
            "filter_status":   "string — filter by status (optional)",
            "filter_priority": "string — filter by priority (optional)"
        }
    },
    "set_due_date": {
        "fn": lambda **kw: set_due_date(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Set or update the due date for a task",
        "params": {
            "task_ref": "string — task title or ID",
            "due_date": "string — new due date"
        }
    },
    "flag_task": {
        "fn": lambda **kw: flag_task(**kw, sheet_tab=BOUND_SHEET_TAB),
        "description": "Flag a task as needing attention / escalated",
        "params": {
            "task_ref": "string — task title or ID",
            "reason":   "string — why it's being flagged"
        }
    },
    "get_sheet_summary": {
        "fn": lambda **kw: get_sheet_summary(sheet_tab=BOUND_SHEET_TAB),
        "description": "Get a high-level summary: counts by status, overdue items, flagged tasks",
        "params": {}
    }
}


# ══════════════════════════════════════════════════════════════════════════════
#  AGENT SYSTEM PROMPT
#  Tells the LLM what kind of agent it is and what decisions to make.
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = f"""You are TaskBot, a dedicated project coordination agent.

YOUR WORKSPACE (fixed at deploy time, never changes):
  - Telegram group : {BOUND_GROUP_ID}
  - Sheet tab      : {BOUND_SHEET_TAB}

YOUR ONLY JOB:
Read messages from the team and keep the task sheet up to date.
You have no other responsibilities.

You will receive:
  - A message from a team member
  - The sender's name
  - The current task list from the sheet (JSON)

You must respond with ONLY a JSON object in this exact format:
{{
  "action": "<tool_name or null>",
  "params": {{ <tool params or empty object> }},
  "reply":  "<short confirmation to send back to chat, or null>"
}}

DECISION RULES:
- Only act if the message clearly relates to a task or work item
- Social chat, off-topic messages → action: null, reply: null
- Match task references loosely: "the landing page" / "my design work" / "the API stuff" are all valid references
- For status, pick the closest match:
    "done" / "finished" / "completed" / "shipped"        → done
    "stuck" / "blocked" / "waiting on" / "can't proceed" → blocked
    "behind" / "delayed" / "going to miss"               → off_track
    "on track" / "going well" / "progressing"            → on_track
    "started" / "working on" / "picked up"               → in_progress
- For new tasks: extract title and owner (default owner = the sender)
- Replies: 1–2 lines max, use ✅ 🟢 🟡 🔴 ⚠️ emojis, never expose tool names or JSON

AVAILABLE TOOLS:
{json.dumps({k: {"description": v["description"], "params": v["params"]} for k, v in TOOLS.items()}, indent=2)}
"""


# ══════════════════════════════════════════════════════════════════════════════
#  MESSAGE HANDLER
#  Called by OpenClaw for every message that passes the group filter.
#  By the time a message reaches here, the chat_id has already been validated.
#  This function applies a second check anyway (defence in depth).
# ══════════════════════════════════════════════════════════════════════════════

def handle_message(event: dict) -> dict:
    """
    Process one Telegram message. Called by OpenClaw.

    event = {
        "message":    str   — raw message text
        "sender":     str   — display name or @handle
        "chat_id":    str   — Telegram chat ID (already validated by OpenClaw)
        "message_id": int   — Telegram message ID
    }
    """
    message    = event.get("message", "").strip()
    sender     = event.get("sender", "Unknown")
    chat_id    = str(event.get("chat_id", ""))
    message_id = event.get("message_id")

    # ── Second-layer group guard ──────────────────────────────────────────────
    if chat_id != str(BOUND_GROUP_ID):
        print(f"[TaskBot] blocked message from unbound group {chat_id}")
        return {"status": "blocked", "reason": "chat_id not in bound group"}

    if not message:
        return {"status": "skipped", "reason": "empty message"}

    # ── Fetch current tasks as LLM context ───────────────────────────────────
    try:
        current_tasks = list_tasks(sheet_tab=BOUND_SHEET_TAB)
    except Exception as e:
        print(f"[TaskBot] warning: could not fetch tasks for context: {e}")
        current_tasks = []

    # ── Ask the LLM what action to take ──────────────────────────────────────
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

    # ── Execute the tool (sheet_tab is baked into each lambda) ───────────────
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

    # ── Reply in chat ─────────────────────────────────────────────────────────
    if reply:
        send_message(chat_id=chat_id, text=reply, reply_to=message_id)

    return result
