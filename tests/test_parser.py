from gateway.parser import parse_text_tool_call


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