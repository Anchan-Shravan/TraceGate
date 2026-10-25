from gateway.detector import validate_tool_call


SEARCH_NOTES_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                },
                "required": ["keyword"],
            },
        },
    }
]


def test_accepts_known_tool_with_correct_argument_type():
    call = {"name": "search_notes", "args": {"keyword": "meeting"}}

    assert validate_tool_call(call, SEARCH_NOTES_SCHEMA) is True


def test_rejects_unknown_tool():
    call = {"name": "unknown_tool", "args": {}}

    assert validate_tool_call(call, SEARCH_NOTES_SCHEMA) is False


def test_rejects_missing_required_argument():
    call = {"name": "search_notes", "args": {}}

    assert validate_tool_call(call, SEARCH_NOTES_SCHEMA) is False


def test_rejects_wrong_argument_type():
    call = {"name": "search_notes", "args": {"keyword": 123}}

    assert validate_tool_call(call, SEARCH_NOTES_SCHEMA) is False