_tasks: list[dict] = []

TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a new task with a title and optional due date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "due_date": {"type": "string", "description": "Due date in ISO 8601 format (YYYY-MM-DD)"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List all current tasks.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


def create_task(title: str, due_date: str | None = None) -> str:
    task = {"id": len(_tasks) + 1, "title": title, "due_date": due_date, "done": False}
    _tasks.append(task)
    msg = f"Task created: '{title}'"
    if due_date:
        msg += f" (due {due_date})"
    return msg


def list_tasks() -> str:
    if not _tasks:
        return "No tasks."
    lines = []
    for t in _tasks:
        status = "done" if t["done"] else "pending"
        due = f" — due {t['due_date']}" if t.get("due_date") else ""
        lines.append(f"[{t['id']}] {t['title']}{due} ({status})")
    return "\n".join(lines)
