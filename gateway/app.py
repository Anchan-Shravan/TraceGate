import json
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response


def create_app(
    upstream_url: str = "http://localhost:11434",
    trace_path: str | Path = "logs/trace.jsonl",
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    app = FastAPI()
    trace_file = Path(trace_path)

    @app.post("/api/chat")
    async def chat(request: Request):
        # Keep the incoming JSON exactly as it arrived.
        request_body = await request.body()

        # Send it to Ollama's chat endpoint without changing it.
        async with httpx.AsyncClient(transport=transport, timeout=180.0) as client:
            upstream = await client.post(
                f"{upstream_url.rstrip('/')}/api/chat",
                content=request_body,
                headers={"content-type": "application/json"},
            )

        # Save one JSON record per request.
        trace_file.parent.mkdir(parents=True, exist_ok=True)
        trace_record = {
            "request_body": request_body.decode("utf-8"),
            "response_body": upstream.text,
            "status_code": upstream.status_code,
        }
        with trace_file.open("a", encoding="utf-8") as file:
            file.write(json.dumps(trace_record) + "\n")

        # Return Ollama's response and status to the caller.
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers={
                "content-type": upstream.headers.get(
                    "content-type", "application/json"
                )
            },
        )

    return app