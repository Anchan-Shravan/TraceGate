from gateway.parser import find_text_tool_call_candidates, parse_text_tool_call


def test_parses_json_tool_call_text():
    text = '{"name":"add","arguments":{"a":482,"b":19}}'

    assert parse_text_tool_call(text) == {
        "name": "add",
        "args": {"a": 482, "b": 19},
    }


def test_ordinary_text_is_not_a_tool_call():
    assert parse_text_tool_call("I should add 2 and 3.") is None


def test_malformed_json_is_not_a_tool_call():
    assert parse_text_tool_call('{"name":"add","arguments":') is None


def test_fenced_and_wrapped_calls_are_supported():
    assert parse_text_tool_call('```json\n{"name":"add","arguments":{"a":2,"b":3}}\n```') == {
        "name": "add",
        "args": {"a": 2, "b": 3},
    }
    assert parse_text_tool_call('<tool_call>{"name":"add","arguments":{"a":2,"b":3}}</tool_call>') == {
        "name": "add",
        "args": {"a": 2, "b": 3},
    }


def test_json_string_arguments_are_supported():
    text = '{"name":"add","arguments":"{\\"a\\":2,\\"b\\":3}"}'

    assert parse_text_tool_call(text) == {
        "name": "add",
        "args": {"a": 2, "b": 3},
    }


def test_malformed_and_multiple_call_candidates_are_reported():
    malformed = find_text_tool_call_candidates('{"name":"add","arguments":{"a":2},')
    multiple = find_text_tool_call_candidates(
        '<tool_call>{"name":"add","arguments":{"a":2,"b":3}}</tool_call>'
        '<tool_call>{"name":"add","arguments":{"a":4,"b":5}}</tool_call>'
    )

    assert len(malformed) == 1
    assert malformed[0]["error"]
    assert len(multiple) == 2
