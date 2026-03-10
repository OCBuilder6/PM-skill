"""
Telegram Helper
===============
Sends messages back to the Telegram chat via Bot API.
"""

import os
import requests


BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id: str | int, text: str, reply_to: int = None) -> dict:
    """Send a text message to a Telegram chat."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to

    resp = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)
    return resp.json()


def send_summary(chat_id: str | int, summary: dict) -> dict:
    """Format and send a task summary message."""
    by_status = summary.get("by_status", {})

    status_icons = {
        "done":        "✅",
        "on_track":    "🟢",
        "in_progress": "🔵",
        "todo":        "⚪",
        "off_track":   "🟡",
        "blocked":     "🔴",
        "cancelled":   "⛔"
    }

    lines = [f"📋 *Task Summary* — {summary['total']} total tasks\n"]
    for status, count in sorted(by_status.items()):
        icon = status_icons.get(status, "•")
        lines.append(f"{icon} {status.replace('_', ' ').title()}: {count}")

    if summary.get("overdue"):
        lines.append(f"\n⏰ *Overdue ({len(summary['overdue'])}):*")
        for t in summary["overdue"][:5]:
            lines.append(f"  • {t['title']} (due {t['due']})")

    if summary.get("flagged"):
        lines.append(f"\n🚩 *Flagged ({len(summary['flagged'])}):*")
        for t in summary["flagged"][:5]:
            lines.append(f"  • {t['title']}")

    return send_message(chat_id, "\n".join(lines))
