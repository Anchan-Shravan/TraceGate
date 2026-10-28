import json

import httpx
import pytest
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


def test_chat_uses_configured_upstream_timeout(tmp_path, monkeypatch):
    seen_timeouts = []
    monkeypatch.setenv("TRACEGATE_UPSTREAM_TIMEOUT", "600")

    def fake_ollama(request):
        seen_timeouts.append(request.extensions["timeout"]["read"])
        return httpx.Response(
            200,
            json={"model": "test-model", "message": {"role": "assistant", "content": "Done."}},
        )

    from gateway.app import create_app

    app = create_app(
        upstream_url="http://ollama.test",
        trace_path=tmp_path / "trace.jsonl",
        transport=httpx.MockTransport(fake_ollama),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"model": "test-model", "stream": False, "messages": []},
        )

    assert response.status_code == 200
    assert seen_timeouts == [600.0]


@pytest.mark.parametrize("timeout_value", ["0", "-5", "nan", "not-a-number"])
def test_rejects_invalid_upstream_timeout(timeout_value, monkeypatch):
    monkeypatch.setenv("TRACEGATE_UPSTREAM_TIMEOUT", timeout_value)

    from gateway.app import create_app

    with pytest.raises(ValueError, match="finite number greater than zero"):
        create_app()


def test_trace_names_upstream_timeout_error(tmp_path):
    def timed_out(_request):
        raise httpx.ReadTimeout("mock upstream timed out")

    from gateway.app import create_app

    app = create_app(
        upstream_url="http://ollama.test",
        trace_path=tmp_path / "trace.jsonl",
        transport=httpx.MockTransport(timed_out),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"model": "test-model", "stream": False, "messages": []},
        )

    trace = json.loads((tmp_path / "trace.jsonl").read_text(encoding="utf-8"))
    assert response.status_code == 502
    assert trace["errors"] == ["ReadTimeout: mock upstream timed out"]


def test_chat_preserves_upstream_http_error_and_traces_it(tmp_path):
    error_body = {"error": "model is temporarily unavailable"}

    def unavailable(_request):
        return httpx.Response(503, json=error_body)

    from gateway.app import create_app

    app = create_app(
        upstream_url="http://ollama.test",
        trace_path=tmp_path / "trace.jsonl",
        transport=httpx.MockTransport(unavailable),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"model": "test-model", "stream": False, "messages": []},
        )

    trace = json.loads((tmp_path / "trace.jsonl").read_text(encoding="utf-8"))
    assert response.status_code == 503
    assert response.json() == error_body
    assert trace["status_code"] == 503
    assert json.loads(trace["response_body"]) == error_body
