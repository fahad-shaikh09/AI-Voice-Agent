_events: list[dict] = []

TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "Create a calendar event with a title, date, and optional time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Event title"},
                    "date": {"type": "string", "description": "Event date in ISO 8601 format (YYYY-MM-DD)"},
                    "time": {"type": "string", "description": "Event time in HH:MM 24-hour format"},
                },
                "required": ["title", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_events",
            "description": "List upcoming calendar events.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


def create_event(title: str, date: str, time: str | None = None) -> str:
    event = {"id": len(_events) + 1, "title": title, "date": date, "time": time}
    _events.append(event)
    when = f"{date} at {time}" if time else date
    return f"Event created: '{title}' on {when}"


def list_events() -> str:
    if not _events:
        return "No upcoming events."
    lines = []
    for e in sorted(_events, key=lambda x: (x["date"], x.get("time") or "")):
        when = f"{e['date']} {e['time']}" if e.get("time") else e["date"]
        lines.append(f"[{e['id']}] {e['title']} — {when}")
    return "\n".join(lines)
