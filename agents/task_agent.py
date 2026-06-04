from ollama import Client
from config import OLLAMA_HOST, OLLAMA_MODEL
from tools import ALL_TOOLS, dispatch

_client = Client(host=OLLAMA_HOST)


def run(messages: list[dict]) -> str:
    while True:
        response = _client.chat(model=OLLAMA_MODEL, messages=messages, tools=ALL_TOOLS)
        msg = response.message

        tool_calls = msg.tool_calls or []
        if not tool_calls:
            return msg.content or ""

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            result = dispatch(tc.function.name, tc.function.arguments)
            messages.append({
                "role": "tool",
                "content": result,
                "name": tc.function.name,
            })
