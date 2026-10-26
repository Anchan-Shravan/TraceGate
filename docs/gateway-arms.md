# Gateway intervention arms

TraceGate can run one of four modes (called “arms” in the plan). A0 remains the default, so existing gateway runs continue to pass requests through unchanged.

| Arm | Behavior |
|---|---|
| A0 | Forwards the request and model response unchanged; logs the exchange. |
| A1 | Converts one valid JSON text tool call in the assistant response into Ollama's structured `tool_calls` format. It does not retry. |
| A2 | Checks native structured tool calls against the offered schemas. If a native call is invalid, asks the model once to correct it. It does not convert text calls. |
| A3 | Combines A1 and A2, and also retries a detected invalid text call once. It converts the retry if that retry contains one valid text call. |

The same fixed retry template includes the validation errors and offered tool schemas. A retry adds the invalid assistant message and one corrective user message to the original request, keeping its model and other generation settings. Trace logs record the original response, final response, classification, action, errors, retry count, and total latency.

Plain prose is not treated as a call, even when it mentions a function such as `add(2, 3)`. A text call must be a JSON object, a fenced JSON block, or a `<tool_call>` block with a name and arguments/parameters. A malformed call-shaped JSON block, unknown tool, schema error, or multiple candidates is classified as invalid. At most one retry is made for a model turn. If the retry remains invalid, its response is forwarded unchanged.

Intervention arms require `stream: false`; streaming stays available in A0 only. This matches the project's current scope, which excludes streaming.

## Choose an arm in PowerShell

Set the environment variable in the terminal before starting the server. For example, to run A3:

```powershell
$env:TRACEGATE_ARM = "A3"
.\.venv\Scripts\python.exe -m uvicorn gateway.app:create_app --factory --host 127.0.0.1 --port 8000
```

Replace `A3` with `A0`, `A1`, or `A2` to choose another arm. Stop the server with **Ctrl+C** before changing arms and starting it again. If the variable is not set, the gateway uses A0.

The app factory also accepts `arm="A1"` directly, which is useful for automated tests. This implementation is not frozen yet; run the planned development equivalence and live checks before creating the `gateway-frozen` tag.
