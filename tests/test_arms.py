import json

import httpx
from fastapi.testclient import TestClient

from gateway.app import create_app


ADD_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
        },
    }
]


def ollama_response(message):
    return {"model": "test-model", "message": message, "done": True}


def test_a1_converts_one_valid_json_text_call(tmp_path):
    upstream_response = ollama_response(
        {
            "role": "assistant",
            "content": '{"name":"add","arguments":{"a":2,"b":3}}',
        }
    )

    def fake_ollama(_request):
        return httpx.Response(200, json=upstream_response)

    app = create_app(
        upstream_url="http://ollama.test",
        trace_path=tmp_path / "trace.jsonl",
        transport=httpx.MockTransport(fake_ollama),
        arm="A1",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"model": "test-model", "stream": False, "tools": ADD_TOOLS, "messages": []},
        )

    assert response.status_code == 200
    assert response.json()["message"]["content"] == ""
    assert response.json()["message"]["tool_calls"] == [
        {"function": {"name": "add", "arguments": {"a": 2, "b": 3}}}
    ]
    trace = json.loads((tmp_path / "trace.jsonl").read_text(encoding="utf-8"))
    assert trace["arm"] == "A1"
    assert trace["action"] == "converted_text_call"
    assert trace["retries"] == 0
    assert trace["final_classification"] == "N-valid"


def test_a2_retries_invalid_native_call_once(tmp_path):
    requests_seen = []
    responses = [
        ollama_response(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "add", "arguments": {"a": 2}}}],
            }
        ),
        ollama_response(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "add", "arguments": {"a": 2, "b": 3}}}
                ],
            }
        ),
    ]

    def fake_ollama(request):
        requests_seen.append(json.loads(request.content))
        return httpx.Response(200, json=responses.pop(0))

    app = create_app(
        upstream_url="http://ollama.test",
        trace_path=tmp_path / "trace.jsonl",
        transport=httpx.MockTransport(fake_ollama),
        arm="A2",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"model": "test-model", "stream": False, "tools": ADD_TOOLS, "messages": []},
        )

    assert response.status_code == 200
    assert len(requests_seen) == 2
    assert requests_seen[1]["messages"][-2]["role"] == "assistant"
    assert requests_seen[1]["messages"][-1]["role"] == "user"
    assert "required" in requests_seen[1]["messages"][-1]["content"]
    assert response.json()["message"]["tool_calls"][0]["function"]["arguments"] == {
        "a": 2,
        "b": 3,
    }
    trace = json.loads((tmp_path / "trace.jsonl").read_text(encoding="utf-8"))
    assert trace["arm"] == "A2"
    assert trace["retries"] == 1
    assert trace["action"] == "retried_native_invalid_then_valid_native"
    assert trace["final_classification"] == "N-valid"


def test_a3_retries_invalid_text_call_and_converts_valid_retry(tmp_path):
    requests_seen = []
    responses = [
        ollama_response(
            {
                "role": "assistant",
                "content": '{"name":"add","arguments":{"a":2}}',
            }
        ),
        ollama_response(
            {
                "role": "assistant",
                "content": '{"name":"add","arguments":{"a":2,"b":3}}',
            }
        ),
    ]

    def fake_ollama(request):
        requests_seen.append(json.loads(request.content))
        return httpx.Response(200, json=responses.pop(0))

    app = create_app(
        upstream_url="http://ollama.test",
        trace_path=tmp_path / "trace.jsonl",
        transport=httpx.MockTransport(fake_ollama),
        arm="A3",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"model": "test-model", "stream": False, "tools": ADD_TOOLS, "messages": []},
        )

    assert response.status_code == 200
    assert len(requests_seen) == 2
    assert response.json()["message"]["tool_calls"][0]["function"]["arguments"] == {
        "a": 2,
        "b": 3,
    }
    trace = json.loads((tmp_path / "trace.jsonl").read_text(encoding="utf-8"))
    assert trace["arm"] == "A3"
    assert trace["retries"] == 1
    assert trace["action"] == "retried_text_invalid_then_converted"
    assert trace["final_classification"] == "N-valid"


def test_a3_converts_valid_text_returned_by_native_call_retry(tmp_path):
    responses = [
        ollama_response(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "add", "arguments": {"a": 2}}}],
            }
        ),
        ollama_response(
            {
                "role": "assistant",
                "content": '{"name":"add","arguments":{"a":2,"b":3}}',
            }
        ),
    ]

    def fake_ollama(_request):
        return httpx.Response(200, json=responses.pop(0))

    app = create_app(
        upstream_url="http://ollama.test",
        trace_path=tmp_path / "trace.jsonl",
        transport=httpx.MockTransport(fake_ollama),
        arm="A3",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"model": "test-model", "stream": False, "tools": ADD_TOOLS, "messages": []},
        )

    assert response.status_code == 200
    assert response.json()["message"]["tool_calls"][0]["function"]["arguments"] == {
        "a": 2,
        "b": 3,
    }
    trace = json.loads((tmp_path / "trace.jsonl").read_text(encoding="utf-8"))
    assert trace["action"] == "retried_native_invalid_then_converted"
    assert trace["final_classification"] == "N-valid"


def test_a3_does_not_retry_plain_text(tmp_path):
    requests_seen = []

    def fake_ollama(request):
        requests_seen.append(request)
        return httpx.Response(
            200,
            json=ollama_response(
                {"role": "assistant", "content": "I should use add(2, 3), but I will answer directly."}
            ),
        )

    app = create_app(
        upstream_url="http://ollama.test",
        trace_path=tmp_path / "trace.jsonl",
        transport=httpx.MockTransport(fake_ollama),
        arm="A3",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"model": "test-model", "stream": False, "tools": ADD_TOOLS, "messages": []},
        )

    assert response.status_code == 200
    assert len(requests_seen) == 1
    assert response.json()["message"]["content"].startswith("I should use")
    trace = json.loads((tmp_path / "trace.jsonl").read_text(encoding="utf-8"))
    assert trace["classification"] == "P"
    assert trace["retries"] == 0
