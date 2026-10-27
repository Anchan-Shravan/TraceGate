# Development-only A0 equivalence check

**Date:** 2026-10-27  
**Purpose:** Check whether putting the Ollama-compatible A0 gateway between the benchmark runner and Ollama changes task-level checker outcomes.  
**Data boundary:** Development tasks only. No held-out task or result was read or used.

## Method

- Used the existing development runner at `C:\benchmark\run_benchmark.py`, including its normal tool loop and task checker.
- For each sampled model and task, ran the task directly against Ollama, through A0, then directly against Ollama a second time.
- Kept the same tools, prompt, temperature (`0`), Qwen3 thinking setting (`false`), and seed (`42`) in all three paths.
- Used development tasks `n1` (no tool) and `s1` (one tool) for all three models. Also completed `c1` (two dependent tool calls) for Qwen3 1.7B as an extra check.
- Scored each complete task with the benchmark's existing checker. “Same outcome” means the checker returned the same pass/fail result; it does not mean the model's full prose was byte-for-byte identical.

## Results

| Model | `n1` no-tool | `s1` one-tool | Direct repeats agree? | A0 matches both direct runs? |
|---|---:|---:|---|---|
| `qwen3:1.7b` | Pass | Pass | Yes | Yes, 2 of 2 tasks |
| `qwen3:4b` | Fail | Pass | Yes | Yes, 2 of 2 tasks |
| `qwen2.5-coder:7b` | Fail | Fail | Yes | Yes, 2 of 2 tasks |

Across the six model/task pairs, the two direct runs agreed on pass/fail in **6/6**, and A0 matched each direct run on pass/fail in **6/6**. This small sample found no A0-induced pass/fail change.

The A0 trace contains **8 successful request/response hops** for the sampled no-tool and one-tool tasks. All eight returned status 200 and the response body recorded from Ollama exactly matched the body A0 returned.

The extra `c1` check for `qwen3:1.7b` failed the checker in both direct runs and through A0, so those three outcomes also agreed. The `qwen3:4b` `c1` direct attempt exceeded the 300-second client timeout. Its A0 attempt hit the gateway's 180-second upstream timeout and was recorded as a 502. That chain pair is excluded from the six-pair result above. The longer `c4` chain was also too slow to include. The chain check is therefore incomplete for the 4B and coder models, and A0's timeout needs review before freezing the gateway.

## Runtime and model identity

- Ollama: `0.40.11`
- Ollama Python client: `0.6.3`
- Benchmark runner Python: `3.14.3` (the existing `C:\benchmark\.venv-msys` environment)
- Gateway Python: `3.11.5` (TraceGate `.venv`)
- Temperature: `0`; seed: `42`; Qwen3 `think`: `false`

| Model | Ollama digest |
|---|---|
| `qwen3:1.7b` | `8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7` |
| `qwen3:4b` | `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` |
| `qwen2.5-coder:7b` | `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364` |

## What this does and does not show

This is an exploratory equivalence check, not a general proof that the gateway never changes outputs. It covers two short development tasks per model and one extra chain task for one model. The results support continuing A0-based development for these sampled cases, but the slow chain cases still need a practical run protocol before the gateway is frozen. The holdout remains unused.

The raw local run record is `logs/dev_equivalence_20261027.json` and the gateway request trace is `logs/trace.jsonl`; both are ignored by Git because they can contain full model responses.
