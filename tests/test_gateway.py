import json

import httpx
from fastapi.testclient import TestClient


def test_chat_forwards_tool_messages_and_writes_trace(tmp_path):
    requests_seen = []
    upstream_response = {
        "model": "test-model",
        "message": {"role": "assistant", "content": "Done."},
        "done": True,
    }

    def fake_ollama(request):
        requests_seen.append(request)
        return httpx.Response(200, json=upstream_response)

    trace_file = tmp_path / "trace.jsonl"

    # This import will fail for now because we have not built the gateway yet.
    from gateway.app import create_app

    app = create_app(
        upstream_url="http://ollama.test",
        trace_path=trace_file,
        transport=httpx.MockTransport(fake_ollama),
    )

    chat_request = {
        "model": "test-model",
        "stream": False,
        "messages": [
            {"role": "user", "content": "Add 2 and 3."},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "name": "add",
                            "arguments": {"a": 2, "b": 3},
                        }
                    }
                ],
            },
            {"role": "tool", "tool_name": "add", "content": "5"},
        ],
    }

    with TestClient(app) as client:
        response = client.post("/api/chat", json=chat_request)

    assert response.status_code == 200
    assert response.json() == upstream_response
    assert len(requests_seen) == 1
    assert json.loads(requests_seen[0].content) == chat_request

    trace_records = trace_file.read_text(encoding="utf-8").splitlines()
    assert len(trace_records) == 1
    trace = json.loads(trace_records[0])
    assert json.loads(trace["request_body"]) == chat_request
    assert json.loads(trace["response_body"]) == upstream_response
    assert trace["status_code"] == 200