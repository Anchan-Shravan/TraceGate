# Development parser and schema-check analysis

## Scope

This is an exploratory, call-level analysis of the 360 existing TinyToolBench v4 development outputs. It uses `final_text` from `C:\benchmark\results\results_v4_with_reasons.csv`, the expected calls in `C:\benchmark\tasks.json`, and the current `gateway/parser.py` and `gateway/detector.py`. The source results remain outside this repository. No held-out tasks or results were used.

The parser accepts only a complete JSON object with a non-empty `name` and an object-valued `arguments` field. It does not extract calls from prose, fenced code, or wrapper tags. The schema check verifies tool name, required and extra argument names, and supported argument types. It cannot tell whether a tool call was appropriate for the user's task or whether its values are semantically correct.

## Results

| Measure | Count | Meaning |
|---|---:|---|
| Development outputs checked | 360 | All rows in the v4 results file |
| Text calls parsed | 63 | Complete JSON calls found by the current parser |
| Parsed calls on tasks that expected a tool | 45 | 36 match the expected first call; 9 do not |
| Exact expected first calls | 36 | Exact name and arguments, including the expected first call only |
| Wrong first calls on tool tasks | 9 | The JSON was parsed, but its first call differs from the expected first call |
| Parsed calls on no-tool tasks | 18 | False extractions for this task-level measure |
| Calls accepted by schema validation | 60 | 36 exact calls, 9 wrong first calls, and 15 calls on no-tool tasks |
| Calls rejected by schema validation | 3 | All were `{"name": "None", "arguments": {}}` on qwen2.5-coder:7b task n2, runs 1–3 |

Among the 45 parsed calls from tasks that expected a tool, 36 (80%) exactly match the expected first call. The parser also extracts a call from 18 of the 72 no-tool attempts (25%). Schema validation rejects the three unknown-tool `None` calls, but accepts the other 15 calls from no-tool attempts. It also accepts the 9 wrong first calls because their names and argument types fit a tool schema.

## What this says

The parser can recover some valid text-form calls, but it also extracts calls on no-tool tasks. Schema validation catches malformed or unknown-tool calls; it does not fix wrong values, decide whether a call was needed, or judge the final answer. The results support keeping the detector strict and measuring no-tool regressions in any live arm comparison.

These are exploratory development results, not held-out performance. The v4 file has no post-tool-result continuation suitable for scoring complete chains, so the exact-match number is only for the extracted first call. Do not describe 36/63 as overall task accuracy.
