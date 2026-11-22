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

## Preliminary held-out baseline (2026-11-22)

One A0 pass-through run was completed for all 20 held-out tasks using `qwen3:4b` (one run per task).

| Task category | Passed |
|---|---:|
| Single-call | 4 / 4 |
| Tool selection | 2 / 3 |
| Chains | 1 / 6 |
| No-tool | 4 / 4 |
| Robustness | 2 / 3 |
| **Overall** | **13 / 20** |

Five tasks returned normally but failed the checker. Two more ended with gateway `502` errors and were counted as failures. For the 18 normally returned tasks, recorded task time totaled 2,511.33 seconds (mean 139.52 seconds; median 75.39 seconds). The runner records zero elapsed seconds for exception rows, so this is not the full wall-clock cost of the run.

This is a **partial, exploratory result**, not the planned experiment: it covers one model, one arm, and one run per task. The run used temperature `0` and Qwen3 `think=false`, but the runner did not set a fixed seed. The benchmark metadata also could not query model details through the A0 gateway; a direct Ollama tags query identified the model digest as `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` (Ollama server `0.40.16`). Because the fixed-seed requirement was not met and A1-A3 were not run, these numbers do not show whether gateway interventions help.

The raw CSV and full response traces stay in the ignored local folder `logs/holdout_runs/20261122/A0_qwen3_4b/`; they are not committed because they contain full model responses. The other planned models `qwen3:1.7b` and `qwen3:8b` were not installed during this run.

Do not change gateway or checker rules based on these holdout results. Complete any remaining comparison under the frozen rules and report this seed and timeout limitation with the findings.

The full plan, including run order and analysis measures, is in [`TraceGate_plan.md`](TraceGate_plan.md).
