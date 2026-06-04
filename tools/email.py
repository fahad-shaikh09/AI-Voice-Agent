_sent: list[dict] = []

TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email to a recipient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body text"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_sent_emails",
            "description": "List recently sent emails.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


def send_email(to: str, subject: str, body: str) -> str:
    _sent.append({"to": to, "subject": subject, "body": body})
    return f"Email sent to {to} with subject: '{subject}'"


def list_sent_emails() -> str:
    if not _sent:
        return "No sent emails."
    lines = [f"[{i + 1}] To: {e['to']} — {e['subject']}" for i, e in enumerate(_sent)]
    return "\n".join(lines)
