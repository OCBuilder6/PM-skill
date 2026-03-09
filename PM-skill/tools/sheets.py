"""
Google Sheets Tool
==================
All task CRUD operations against the Google Sheet.
Sheet structure:
  A: Task ID | B: Title | C: Owner | D: Status | E: Priority | F: Due Date | G: Last Updated | H: Comments | I: Flagged
"""

import os
import json
import re
from datetime import datetime, date
from typing import Optional
import gspread
from google.oauth2.service_account import Credentials

# ─── Auth ─────────────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SHEET_COLUMNS = {
    "id":           "A",
    "title":        "B",
    "owner":        "C",
    "status":       "D",
    "priority":     "E",
    "due_date":     "F",
    "last_updated": "G",
    "comments":     "H",
    "flagged":      "I"
}

COL_INDEX = {v: i+1 for i, (k, v) in enumerate(SHEET_COLUMNS.items())}

STATUS_COLORS = {
    "todo":        {"red": 0.9,  "green": 0.9,  "blue": 0.9},   # light grey
    "in_progress": {"red": 0.8,  "green": 0.9,  "blue": 1.0},   # light blue
    "on_track":    {"red": 0.72, "green": 0.96, "blue": 0.72},   # light green
    "off_track":   {"red": 1.0,  "green": 0.85, "blue": 0.6},    # amber
    "blocked":     {"red": 1.0,  "green": 0.7,  "blue": 0.7},    # light red
    "done":        {"red": 0.82, "green": 0.82, "blue": 0.82},   # grey (done)
    "cancelled":   {"red": 0.95, "green": 0.95, "blue": 0.95},   # pale
}


def _get_sheet(tab_name: str = ""):
    """
    Return the gspread worksheet for the given tab name.
    Resolved from: explicit tab_name arg → GOOGLE_SHEET_TAB env var.
    Creates the tab automatically if it doesn't exist yet.
    """
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id   = os.environ.get("GOOGLE_SHEETS_ID")
    env_tab    = os.environ.get("GOOGLE_SHEET_TAB", "").strip()

    if not creds_json or not sheet_id:
        raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SHEETS_ID env vars")

    resolved_tab = tab_name or env_tab
    if not resolved_tab:
        raise ValueError(
            "No sheet tab specified. Set GOOGLE_SHEET_TAB in your .env "
            "or pass tab_name explicitly."
        )

    creds_data   = json.loads(creds_json)
    creds        = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    client       = gspread.authorize(creds)
    spreadsheet  = client.open_by_key(sheet_id)

    try:
        return spreadsheet.worksheet(resolved_tab)
    except gspread.WorksheetNotFound:
        print(f"[sheets] Tab '{resolved_tab}' not found — creating it")
        return spreadsheet.add_worksheet(title=resolved_tab, rows=1000, cols=20)


def _ensure_headers(sheet):
    """Create headers if the sheet is empty."""
    row1 = sheet.row_values(1)
    if not row1 or row1[0] != "Task ID":
        headers = ["Task ID", "Title", "Owner", "Status", "Priority", "Due Date", "Last Updated", "Comments", "Flagged"]
        sheet.insert_row(headers, 1)
        # Bold + freeze header row
        sheet.format("A1:I1", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
        })


def _next_task_id(sheet) -> str:
    """Generate next sequential task ID."""
    all_ids = sheet.col_values(1)[1:]  # Skip header
    nums = [int(re.sub(r'\D', '', tid)) for tid in all_ids if re.sub(r'\D', '', tid)]
    next_num = max(nums) + 1 if nums else 1
    return f"T{next_num:03d}"


def _find_row(sheet, task_ref: str) -> Optional[int]:
    """Find row number by task ID or fuzzy title match. Returns 1-indexed row."""
    all_values = sheet.get_all_values()
    task_ref_lower = task_ref.lower().strip()

    for i, row in enumerate(all_values[1:], start=2):  # Skip header
        task_id = row[0].lower() if row else ""
        title = row[1].lower() if len(row) > 1 else ""
        if task_ref_lower == task_id or task_ref_lower in title or title in task_ref_lower:
            return i
    return None


def _set_row_color(sheet, row_num: int, status: str):
    """Color the entire row based on status."""
    color = STATUS_COLORS.get(status, STATUS_COLORS["todo"])
    sheet.format(f"A{row_num}:I{row_num}", {"backgroundColor": color})


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ─── Tool Functions ────────────────────────────────────────────────────────────

def create_task(title: str, owner: str = "Unassigned", due_date: str = "",
                priority: str = "medium", sheet_tab: str = "") -> dict:
    """Add a new task row to the sheet."""
    sheet = _get_sheet(sheet_tab)
    _ensure_headers(sheet)

    task_id = _next_task_id(sheet)
    row = [task_id, title, owner, "todo", priority, due_date, _now(), "", ""]
    sheet.append_row(row)

    # Find the row we just added and color it
    row_num = len(sheet.get_all_values())
    _set_row_color(sheet, row_num, "todo")

    return {"task_id": task_id, "title": title, "owner": owner}


def update_task_status(task_ref: str, status: str, note: str = "", sheet_tab: str = "") -> dict:
    """Update the status column (and optionally add a comment)."""
    valid_statuses = ["todo", "in_progress", "on_track", "off_track", "blocked", "done", "cancelled"]
    if status not in valid_statuses:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {valid_statuses}")

    sheet = _get_sheet(sheet_tab)
    row_num = _find_row(sheet, task_ref)
    if not row_num:
        raise ValueError(f"Task not found: '{task_ref}'")

    # Update status
    sheet.update_cell(row_num, COL_INDEX["D"], status)
    sheet.update_cell(row_num, COL_INDEX["G"], _now())

    # Append note to comments if provided
    if note:
        existing = sheet.cell(row_num, COL_INDEX["H"]).value or ""
        new_comment = f"[{_now()}] {note}"
        combined = f"{existing}\n{new_comment}".strip()
        sheet.update_cell(row_num, COL_INDEX["H"], combined)

    _set_row_color(sheet, row_num, status)

    task_title = sheet.cell(row_num, COL_INDEX["B"]).value
    return {"task_ref": task_title, "status": status, "row": row_num}


def assign_task(task_ref: str, owner: str, sheet_tab: str = "") -> dict:
    """Change the owner of a task."""
    sheet = _get_sheet(sheet_tab)
    row_num = _find_row(sheet, task_ref)
    if not row_num:
        raise ValueError(f"Task not found: '{task_ref}'")

    sheet.update_cell(row_num, COL_INDEX["C"], owner)
    sheet.update_cell(row_num, COL_INDEX["G"], _now())

    task_title = sheet.cell(row_num, COL_INDEX["B"]).value
    return {"task_ref": task_title, "new_owner": owner}


def add_comment(task_ref: str, comment: str, sheet_tab: str = "") -> dict:
    """Append a timestamped comment to a task."""
    sheet = _get_sheet(sheet_tab)
    row_num = _find_row(sheet, task_ref)
    if not row_num:
        raise ValueError(f"Task not found: '{task_ref}'")

    existing = sheet.cell(row_num, COL_INDEX["H"]).value or ""
    new_entry = f"[{_now()}] {comment}"
    combined = f"{existing}\n{new_entry}".strip()
    sheet.update_cell(row_num, COL_INDEX["H"], combined)
    sheet.update_cell(row_num, COL_INDEX["G"], _now())

    task_title = sheet.cell(row_num, COL_INDEX["B"]).value
    return {"task_ref": task_title, "comment_added": comment}


def list_tasks(filter_owner: str = "", filter_status: str = "",
               filter_priority: str = "", sheet_tab: str = "") -> list:
    """Return tasks as a list of dicts, with optional filters."""
    sheet = _get_sheet(sheet_tab)
    all_values = sheet.get_all_values()
    if len(all_values) < 2:
        return []

    headers = ["id", "title", "owner", "status", "priority", "due_date", "last_updated", "comments", "flagged"]
    tasks = []
    for row in all_values[1:]:
        if not row or not row[0]:
            continue
        task = dict(zip(headers, row + [""] * (len(headers) - len(row))))

        if filter_owner and filter_owner.lower() not in task["owner"].lower():
            continue
        if filter_status and task["status"] != filter_status:
            continue
        if filter_priority and task["priority"] != filter_priority:
            continue

        tasks.append(task)

    return tasks


def set_due_date(task_ref: str, due_date: str, sheet_tab: str = "") -> dict:
    """Set or update the due date of a task."""
    sheet = _get_sheet(sheet_tab)
    row_num = _find_row(sheet, task_ref)
    if not row_num:
        raise ValueError(f"Task not found: '{task_ref}'")

    sheet.update_cell(row_num, COL_INDEX["F"], due_date)
    sheet.update_cell(row_num, COL_INDEX["G"], _now())

    task_title = sheet.cell(row_num, COL_INDEX["B"]).value
    return {"task_ref": task_title, "due_date": due_date}


def flag_task(task_ref: str, reason: str = "", sheet_tab: str = "") -> dict:
    """Mark a task as flagged/needing attention."""
    sheet = _get_sheet(sheet_tab)
    row_num = _find_row(sheet, task_ref)
    if not row_num:
        raise ValueError(f"Task not found: '{task_ref}'")

    flag_text = f"🚩 FLAGGED: {reason}" if reason else "🚩 FLAGGED"
    sheet.update_cell(row_num, COL_INDEX["I"], flag_text)
    sheet.update_cell(row_num, COL_INDEX["G"], _now())

    # Red highlight
    sheet.format(f"A{row_num}:I{row_num}", {
        "backgroundColor": {"red": 1.0, "green": 0.6, "blue": 0.6}
    })

    task_title = sheet.cell(row_num, COL_INDEX["B"]).value
    return {"task_ref": task_title, "flagged": True, "reason": reason}


def get_sheet_summary(sheet_tab: str = "") -> dict:
    """Return counts by status and any overdue tasks."""
    tasks = list_tasks(sheet_tab=sheet_tab)
    today = date.today().isoformat()

    summary = {
        "total": len(tasks),
        "by_status": {},
        "overdue": [],
        "flagged": [],
        "unassigned": []
    }

    for t in tasks:
        status = t.get("status", "unknown")
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1

        due = t.get("due_date", "")
        if due and due < today and t["status"] not in ("done", "cancelled"):
            summary["overdue"].append({"id": t["id"], "title": t["title"], "due": due})

        if t.get("flagged"):
            summary["flagged"].append({"id": t["id"], "title": t["title"]})

        if t.get("owner", "").lower() in ("", "unassigned"):
            summary["unassigned"].append({"id": t["id"], "title": t["title"]})

    return summary
