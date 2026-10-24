import json


def parse_text_tool_call(text: str) -> dict | None:
    """Read a complete JSON tool call from text, or return None if it isn't one."""
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(value, dict):
        return None

    name = value.get("name")
    arguments = value.get("arguments")

    if not isinstance(name, str) or not name.strip():
        return None

    if not isinstance(arguments, dict):
        return None

    return {
        "name": name,
        "args": arguments,
    }