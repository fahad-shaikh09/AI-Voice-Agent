from . import calendar, email, tasks

ALL_TOOLS: list[dict] = [
    *calendar.TOOL_DEFS,
    *email.TOOL_DEFS,
    *tasks.TOOL_DEFS,
]

_DISPATCH = {
    "create_event": calendar.create_event,
    "list_events": calendar.list_events,
    "send_email": email.send_email,
    "list_sent_emails": email.list_sent_emails,
    "create_task": tasks.create_task,
    "list_tasks": tasks.list_tasks,
}


def dispatch(name: str, args: dict) -> str:
    fn = _DISPATCH.get(name)
    if fn is None:
        return f"Unknown tool: {name}"
    return fn(**args)
