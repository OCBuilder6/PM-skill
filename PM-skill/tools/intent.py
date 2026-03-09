"""
Intent Parser
=============
Sends a Telegram message to the LLM with full context,
gets back a structured JSON decision about what tool to call.
"""

import os
import json
import re
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def parse_intent(system_prompt: str, message: str, sender: str, tasks: list) -> dict | None:
    """
    Ask Claude to decide what action (if any) to take based on the message.
    Returns a dict: { action, params, reply } or None on failure.
    """
    # Trim task list to avoid huge context — just send titles, IDs, owners, statuses
    task_summary = [
        {
            "id": t.get("id"),
            "title": t.get("title"),
            "owner": t.get("owner"),
            "status": t.get("status"),
            "due_date": t.get("due_date", "")
        }
        for t in (tasks or [])
    ]

    user_content = f"""
Sender: {sender}
Message: "{message}"

Current tasks in sheet:
{json.dumps(task_summary, indent=2)}

Respond ONLY with a valid JSON object. No explanation, no markdown, just JSON.
"""

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}]
        )

        raw = response.content[0].text.strip()

        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"[intent] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"[intent] LLM call failed: {e}")
        return None
