import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from gateway.detector import tool_call_errors
from gateway.parser import find_text_tool_call_candidates


RETRY_TEMPLATE = (
    "Your previous response attempted a tool call that could not be used.\n"
    "Fix the call using only the offered tools.\n"
    "Validation errors:\n{errors}\n"
    "Offered tool schemas:\n{schemas}\n"
    "Return the corrected tool call only, without an explanation."
)
VALID_ARMS = {"A0", "A1", "A2", "A3"}


def _classify_response(body: dict, tool_schemas: list[dict]) -> tuple[str, list[str], dict | None]:
    message = body.get("message")
    if not isinstance(message, dict):
        return "P", [], None

    native_calls = message.get("tool_calls")
    if isinstance(native_calls, list) and native_calls:
        errors = []
        for index, tool_call in enumerate(native_calls, start=1):
            function = tool_call.get("function") if isinstance(tool_call, dict) else None
            if not isinstance(function, dict):
                errors.append(f"Native tool call {index} has no function object.")
                continue
            call = {"name": function.get("name"), "args": function.get("arguments")}
            errors.extend(
                f"Native tool call {index}: {error}"
                for error in tool_call_errors(call, tool_schemas)
            )
        return ("N-invalid" if errors else "N-valid"), errors, None

    content = message.get("content")
    candidates = find_text_tool_call_candidates(content)
    if not candidates:
        return "P", [], None
    if len(candidates) != 1:
        return "T-invalid", [f"Found {len(candidates)} text tool-call candidates; exactly one is allowed."], None

    candidate = candidates[0]
    if candidate["error"]:
        return "T-invalid", [candidate["error"]], None
    call = candidate["call"]
    errors = tool_call_errors(call, tool_schemas)
    return ("T-invalid" if errors else "T-valid"), errors, call


def _convert_text_call(body: dict, call: dict) -> dict:
    converted = json.loads(json.dumps(body))
    message = converted["message"]
    message["content"] = ""
    message["tool_calls"] = [
        {"function": {"name": call["name"], "arguments": call["args"]}}
    ]
    return converted


def _retry_message(errors: list[str], tool_schemas: list[dict]) -> str:
    return RETRY_TEMPLATE.format(
        errors="\n".join(f"- {error}" for error in errors) or "- The call did not match the required format.",
        schemas=json.dumps(tool_schemas, ensure_ascii=False, indent=2),
    )


def create_app(
    upstream_url: str = "http://localhost:11434",
    trace_path: str | Path = "logs/trace.jsonl",
    transport: httpx.AsyncBaseTransport | None = None,
    arm: str | None = None,
    upstream_timeout: float | None = None,
) -> FastAPI:
    app = FastAPI()
    trace_file = Path(trace_path)
    selected_arm = (arm or os.getenv("TRACEGATE_ARM", "A0")).upper()
    if selected_arm not in VALID_ARMS:
        raise ValueError(f"Unknown TraceGate arm {selected_arm!r}; choose A0, A1, A2, or A3.")
    raw_timeout = (
        upstream_timeout
        if upstream_timeout is not None
        else os.getenv("TRACEGATE_UPSTREAM_TIMEOUT", "600")
    )
    try:
        timeout_seconds = float(raw_timeout)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "The Ollama upstream timeout must be a finite number greater than zero seconds."
        ) from error
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError(
            "The Ollama upstream timeout must be a finite number greater than zero seconds."
        )

    def write_trace(record: dict) -> None:
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        with trace_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    @app.post("/api/chat")
    async def chat(request: Request):
        started = time.perf_counter()
        request_body = await request.body()
        trace = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "arm": selected_arm,
            "request_body": request_body.decode("utf-8", errors="replace"),
            "raw_response_body": "",
            "response_body": "",
            "status_code": 502,
            "classification": "P",
            "final_classification": "P",
            "action": "forwarded_unchanged",
            "errors": [],
            "retries": 0,
            "latency_ms": 0,
        }

        try:
            payload = json.loads(request_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None

        if selected_arm != "A0" and isinstance(payload, dict) and payload.get("stream") is True:
            trace["errors"] = ["Intervention arms require stream=false; streaming is not supported."]
            trace["status_code"] = 400
            trace["response_body"] = json.dumps({"detail": trace["errors"][0]})
            trace["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            write_trace(trace)
            return JSONResponse(status_code=400, content={"detail": trace["errors"][0]})

        try:
            async with httpx.AsyncClient(transport=transport, timeout=timeout_seconds) as client:
                upstream = await client.post(
                    f"{upstream_url.rstrip('/')}/api/chat",
                    content=request_body,
                    headers={"content-type": "application/json"},
                )
                final_response_body = upstream.content
                final_status_code = upstream.status_code
                final_content_type = upstream.headers.get("content-type", "application/json")

                try:
                    response_data = upstream.json()
                except (ValueError, json.JSONDecodeError):
                    response_data = None

                schemas = payload.get("tools", []) if isinstance(payload, dict) else []
                if not isinstance(schemas, list):
                    schemas = []

                if upstream.is_success and isinstance(response_data, dict):
                    classification, errors, parsed_call = _classify_response(response_data, schemas)
                    trace["classification"] = classification
                    trace["final_classification"] = classification
                    trace["errors"] = errors
                    trace["raw_response_body"] = upstream.text

                    should_retry = (
                        selected_arm in {"A2", "A3"} and classification == "N-invalid"
                    ) or (selected_arm == "A3" and classification == "T-invalid")

                    if selected_arm in {"A1", "A3"} and classification == "T-valid":
                        response_data = _convert_text_call(response_data, parsed_call)
                        final_response_body = json.dumps(
                            response_data, ensure_ascii=False
                        ).encode("utf-8")
                        trace["final_classification"] = "N-valid"
                        trace["action"] = "converted_text_call"

                    elif should_retry and isinstance(payload, dict):
                        retry_payload = json.loads(json.dumps(payload))
                        messages = retry_payload.get("messages", [])
                        if not isinstance(messages, list):
                            messages = []
                        invalid_message = response_data.get("message")
                        if isinstance(invalid_message, dict):
                            messages.append(invalid_message)
                        messages.append(
                            {
                                "role": "user",
                                "content": _retry_message(errors, schemas),
                            }
                        )
                        retry_payload["messages"] = messages
                        trace["retries"] = 1
                        trace["action"] = (
                            "retried_native_invalid"
                            if classification == "N-invalid"
                            else "retried_text_invalid"
                        )
                        retry = await client.post(
                            f"{upstream_url.rstrip('/')}/api/chat",
                            json=retry_payload,
                        )
                        final_response_body = retry.content
                        final_status_code = retry.status_code
                        final_content_type = retry.headers.get("content-type", "application/json")
                        trace["retry_response_body"] = retry.text

                        if retry.is_success:
                            try:
                                retry_data = retry.json()
                            except (ValueError, json.JSONDecodeError):
                                retry_data = None
                            if isinstance(retry_data, dict):
                                retry_class, retry_errors, retry_call = _classify_response(retry_data, schemas)
                                trace["final_classification"] = retry_class
                                if selected_arm == "A3" and retry_class == "T-valid":
                                    retry_data = _convert_text_call(retry_data, retry_call)
                                    final_response_body = json.dumps(
                                        retry_data, ensure_ascii=False
                                    ).encode("utf-8")
                                    trace["final_classification"] = "N-valid"
                                    retry_source = (
                                        "text" if classification == "T-invalid" else "native"
                                    )
                                    trace["action"] = (
                                        f"retried_{retry_source}_invalid_then_converted"
                                    )
                                elif retry_class == "N-valid":
                                    trace["action"] += "_then_valid_native"
                                else:
                                    trace["errors"].extend(
                                        f"Retry: {error}" for error in retry_errors
                                    )

                trace["status_code"] = final_status_code
                trace["response_body"] = final_response_body.decode(
                    "utf-8", errors="replace"
                )
                if not trace["raw_response_body"]:
                    trace["raw_response_body"] = upstream.text

        except httpx.HTTPError as error:
            error_detail = type(error).__name__
            if str(error):
                error_detail += f": {error}"
            trace["errors"].append(error_detail)
            trace["response_body"] = json.dumps({"detail": "Ollama upstream request failed."})
            trace["status_code"] = 502
            trace["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            write_trace(trace)
            return JSONResponse(status_code=502, content={"detail": "Ollama upstream request failed."})

        trace["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        write_trace(trace)
        return Response(
            content=final_response_body,
            status_code=final_status_code,
            headers={"content-type": final_content_type},
        )

    return app
