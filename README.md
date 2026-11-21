# TraceGate

TraceGate is a local gateway between an application and Ollama. It tests whether lightweight gateway interventions help small local language models use tools correctly, and what extra latency they add.

## Request flow

```text
Application → TraceGate → Ollama → local model
Application ← TraceGate ← Ollama ← local model
```

Ollama and TraceGate run locally. The gateway can pass a reply through, convert a supported text-form tool call, validate a structured call, or ask the model once to correct an invalid call. The four modes are described in [`docs/gateway-arms.md`](docs/gateway-arms.md).

## Evaluation design

- Existing TinyToolBench v4 tasks are development data. They were used while building the parser and gateway rules.
- The 20 tasks in [`holdout/tasks.json`](holdout/tasks.json) are reserved for the final evaluation. They must not be used to change gateway or checker behavior.
- The main comparison is A0 (pass-through) against A1, A2, and A3. The project reports accuracy, task-level changes, retries, latency, and no-tool regressions.
- The checker and task runner are maintained in the separate TinyToolBench repository.

## Frozen inputs

`holdout-frozen` preserves the held-out task set. `gateway-frozen` preserves the gateway and checker versions listed below. The SHA-256 values identify the exact file contents used for that freeze.

| Frozen file | SHA-256 |
|---|---|
| `gateway/app.py` | `886f901935795631dd8dd691437444ee4e073681862098d2e22493dd270cabdf` |
| `gateway/parser.py` | `4f7338aca3bfe3c070cad9af3a87debc56594f533ad5f6c68fe6361b173208bc` |
| `gateway/detector.py` | `83f86c223889b5cff29cc7129f9cd839aaed4f278fd36a5d856bcd2829ac63e8` |
| `C:\benchmark\run_benchmark.py` (runner and checker) | `cccd1663b616eb36c674cb1089993d8753ca43fcd843f7445dbb179e2f5e4c19` |
| `C:\benchmark\tools.py` (tool implementations and schemas) | `fdca250b845aab6626c6a677410f440f2ae2fb1f55758755908c46c071eb2536` |
| `holdout/tasks.json` | `55321566a58dd6ab647a328c7171cde02b2500bb035d45ed333ed281419509dc` |

The benchmark runner now stores its own `runner_sha256` in new run metadata alongside task and tool hashes. The runner version used for this freeze is TinyToolBench commit `6cd30337e27a6402d8c02b6a83df83fd057bf981`.

## Current status

The gateway, parser, detector, and four intervention modes are implemented. The development-only A0 comparison and failure review are documented under `docs/`. The holdout validator passes, and the automated checks pass (24 TraceGate tests and 15 TinyToolBench tests at the time of freeze).

**The held-out model experiment has not been run yet.** The previously installed models include `qwen3:4b` and `qwen2.5-coder:7b`; the planned `qwen3:1.7b` and `qwen3:8b` models were not installed at the freeze check. Do not present the project as having measured which intervention is best until the planned runs and analysis are complete.

The full plan, including run order and analysis measures, is in [`TraceGate_plan.md`](TraceGate_plan.md).
