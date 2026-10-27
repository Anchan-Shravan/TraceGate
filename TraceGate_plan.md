# TraceGate: Final Plan (v3)

**Headline (the only claim this project makes):** a controlled pilot measuring which gateway interventions (format repair, schema validation, retry) help small local models on *unseen* tool-calling tasks, and at what latency cost.

**Not the claim:** "I built a validate-and-retry gateway." That already exists.

---

## 1. Prior work (cite, don't claim novelty)

| Source | What it does |
|---|---|
| ParallelWorks AI gateway docs (parallelworks.com/docs/ai/ai-providers/tool-calling) | Repairs predictable tool-call format variations locally, makes one corrective retry if validation still fails, then errors out |
| Speakeasy Gram "tool call healing" (speakeasy.com/docs/gram/host-mcp/tool-call-healing) | Validates tool parameters against the JSON schema, returns an error to the LLM so it can self-heal, repairs stringified JSON |
| opencode PR #29412 (github.com/anomalyco/opencode/pull/29412) | Proposes a validate-then-repair layer for shape mistakes open-weight models repeat |
| "Robust and Efficient Tool Orchestration via Layered Execution Structures with Reflective Correction" (arxiv.org/abs/2602.18968) | Schema gate plus error-driven repair under a fixed budget, aimed at small LMs |

**Contribution:** a held-out, controlled comparison on a 4 GB consumer laptop with a deterministic checker, reporting wins, losses, and cost per arm.

---

## 2. Data roles and freeze rules

| Set | Role | Rules |
|---|---|---|
| Existing 30 tasks (TinyToolBench v4) | **Development / exploratory** | Already inspected. Used to build and debug the parser and rules. Results are upward-biased and labeled exploratory |
| New held-out tasks (**20 recommended, 10 minimum**) | **Primary test** | Written and frozen before any repair rule exists. No model inference on them until the gateway is frozen |

**Why 20:** at n=10 one flipped task is 10 points, and 3 runs at temperature 0 are near-duplicates, so the effective sample is the task count. At n=10 call it a pilot and make no ranking claims.

**Holdout mix (mirrors v4 categories, chain-heavy):** n=20 = 4 single, 3 selection, 6 chain, 4 no-tool, 3 robustness. n=10 = 2 / 2 / 3 / 2 / 1.

**Authoring:** same four tools and schemas, varied phrasing, no paraphrasing of dev tasks. If a teammate can write about half, do that, since you have already seen the failure modes and may unconsciously write around them.

**Frozen artifacts (commit + tag + sha256 in the README):**
1. `holdout-frozen`: holdout tasks. Task validator passes; gold answers verified by calling the tools directly, not by running a model.
2. `gateway-frozen`: gateway code, detector, parser, retry template, **and the checker** (the checker hash is recorded in run metadata). No edits to any of these after the tag.
3. Pinned runtime: Ollama version, Python client version, and **model digests** (not just tags, since tags can change), plus a fixed `seed`.

**Pre-committed rule for flawed tasks:** if a holdout task is found to be flawed after freezing, do not edit it. Report it and exclude it from **all arms equally**.

---

## 3. Response taxonomy (resolves the A1/A2/A3 gap)

Every model response is classified into exactly one class before any arm acts.

| Class | Meaning |
|---|---|
| **N-valid** | Native structured tool call(s) that pass schema validation |
| **N-invalid** | Native structured call(s) that fail validation: unknown tool, unparseable args, missing required arg, wrong type, or unknown argument name |
| **T-valid** | Exactly **one** detected text call that converts cleanly and passes schema validation |
| **T-invalid** | Text call(s) **detected** but not convertible: malformed JSON, unknown tool, schema failure, or multiple candidates |
| **P** | Plain text, no call detected |

**Detector (strict, so prose is not mistaken for a call):** a JSON object, fenced block, or known wrapper tag (e.g. `<tool_call>`) containing a `name` equal to an offered tool and an `arguments`/`parameters` value that is an object or JSON string. Prose that merely mentions a tool or shows `add(2,3)` is class **P**. The exact formats seen in logged coder outputs are enumerated from **dev data** in step 6, before the holdout is touched.

---

## 4. Arms

All arms use the same gateway path, model, temperature (0), seed, `think` setting, tools, tasks, and checker. Arms differ by config flags only. The gateway speaks Ollama's `/api/chat` dialect so the runner changes only its base URL.

| Class | A0 | A1 (repair) | A2 (validate + retry) | A3 (A1 + A2 + retry on T-invalid) |
|---|---|---|---|---|
| N-valid | forward | forward | forward | forward |
| N-invalid | forward | forward | **retry** | **retry** |
| T-valid | forward | **convert** | forward | **convert** |
| T-invalid | forward | forward | forward | **retry** |
| P | forward | forward | forward | forward |

- **"Forward"** means unchanged. A0 forwards everything and only logs.
- **A2 acts only on native calls.** On a model that emits text calls (the coder) A2 should be roughly A0. That is an informative result, not a bug.
- **A3's retry on T-invalid** is the answer to "what about malformed text calls": they are treated as invalid and retried once. After an A3 retry, the output is re-classified; a T-valid retry output is converted, anything still invalid is forwarded unchanged.
- **Class P is never retried in any arm.** The gateway cannot know a call was needed without the oracle, and forcing calls would break no-tool tasks.
- **A4 (Ollama structured outputs) is omitted.** Native tool calls and structured outputs are separate mechanisms in Ollama's docs, so it is not a fair drop-in arm.

**Oracle rule:** at run time the gateway sees tool schemas and model output only. It never sees `tasks.json` expected calls or answers. (Offline evaluation of the parser on logged data may use expected calls, since that is scoring, not gateway behavior.)

---

## 5. Retry specification

- **Granularity:** at most **1 retry per model turn**. If any call in a response is invalid, the whole turn is retried once.
- **Context sent on retry:** the original messages, plus the model's invalid output as an assistant message, plus one fixed user message from a template written before freezing: the specific errors and the offered tool schemas, with an instruction to reply with a corrected call using only those tools. The template is never tuned on the holdout.
- **Same settings** as the first attempt (temperature, seed, `think`).
- **If the retry is still invalid:** forward it unchanged (no gateway error). The checker scores it as a failure.
- **Cost accounting:** retry latency and tokens are counted in the arm's overhead.

---

## 6. Scoring semantics

The scored transcript contains only calls the gateway **forwards to the runner**. Intercepted invalid calls and retry messages appear in the trace log but not in the scored transcript. Otherwise the checker's "exactly the expected calls" rule would count the invalid attempt as an extra call and penalize retries unfairly. The checker is unchanged and hash-pinned.

---

## 7. Plan (about 3 weeks)

| # | Step | What it does | Why |
|---|---|---|---|
| 1 | **Write and freeze the holdout** (1-2 days) | Section 2 rules; tag `holdout-frozen` | Must precede all rules and parser work |
| 2 | **Define the failure rubric, then classify v4 dev failures** (1 day) | Write format / schema / semantic decision rules first. Hand-label 20 rows, compare with automated labels, report agreement. Dev data only | Prevents circular labeling from the checker's own "reasons" column. Sets the upper bound on what a gate can fix |
| 3 | **Gateway prototype: A0 only** (2-3 days) | Minimal FastAPI proxy to Ollama `/api/chat` preserving the multi-turn tool-call / tool-result flow. JSONL trace per request: raw output, class, repairs, errors, retries, latency | The runner has a multi-turn loop, but gateway integration is unproven |
| 4 | **Equivalence check** (0.5 day) | Run a few dev tasks per model direct-to-Ollama **twice** and through the gateway once. Compare task-level outcomes | Measures Ollama's own run-to-run agreement first. Gateway agreement must be no worse than that baseline. Otherwise arm differences cannot be trusted |
| 5 | **Parser/detector development on dev data** (1-2 days) | Run on logged v4 outputs. Report (a) detection and conversion rates, (b) whether the converted **first call** exactly matches the expected first call, (c) **false extractions** across all 360 logged outputs | Logged text has no post-tool-result turn, so this is **call-level only** and cannot score chains. Live runs do that |
| 6 | **Implement arms and retry template, then freeze** | Flags `repair`, `validate`, `retry_text`; one code path. Enumerate observed text-call formats. Tag `gateway-frozen` | No rule changes after this tag |
| 7 | **Run: holdout first, then dev** | See run protocol (section 8) | Holdout runs once, after freezing. Dev is exploratory |
| 8 | **Analyze** | Per arm vs A0: tasks won / lost / tied, with a per-task flip list labeled by category. Pass counts with Wilson intervals. Retries per task, added tokens and wall-clock, repaired-but-still-failed rate, **no-tool-task regressions**. No significance claims | Shows effect, cost, and harm |
| 9 | **Write up and stop** | Finding first, cite section 1, state limitations | The README is what recruiters read |

**Progress note (2026-10-27):** The development-only A0 equivalence check matched direct pass/fail outcomes for six no-tool and single-tool model/task pairs. A short chain check also matched for Qwen3 1.7B, but the chain check timed out for Qwen3 4B and was not completed for the coder model. See [`docs/dev-equivalence-check.md`](docs/dev-equivalence-check.md). Treat this as partial evidence; the holdout is still unused, and the gateway is not frozen.

**Cut list:** no UI, auth, Docker, streaming, dashboard.
**Scope cutoff:** if step 2 shows semantic failures dominate and step 5 shows parsing recovers little, drop A2/A3 and ship A0/A1 with the negative result.

---

## 8. Run protocol and compute budget

- **Order:** interleave arms per task (round-robin), not all-A0-then-all-A1, so thermal state, background load, and model-load effects do not line up with one arm. Keep the model warm; record idle GPU memory per session.
- **Overhead metrics:** report added generated tokens and extra calls (deterministic) alongside wall-clock (noisy on a 4 GB GPU with CPU offload).
- **Budget:** v4's 360 attempts took two sessions. Full arms multiply that several-fold. Time one pass before committing.
- **Savings, with verification:** reuse v4 as dev A0 only if the step 4 equivalence check passed. Run an arm live only on tasks where the A0 trace shows an intervention would fire, and verify on a random sample of non-firing tasks that outcomes equal A0. State this assumption in the README, since temperature 0 is not guaranteed bit-exact under CPU offload.
- **Models:** 4B, 1.7B, coder on A0-A3. The 8B runs A0 plus one pre-declared arm only (chosen from dev results before touching the holdout).

---

## 9. Premortem

1. **Retry repeats itself at temperature 0.** Mitigated: the retry changes the prompt (section 5).
2. **False repairs and false detections.** Track repaired-but-still-failed and false extractions separately.
3. **A3 retry harms no-tool tasks.** The strict detector plus the no-tool regression metric guard against this.
4. **Semantic failures dominate.** Schema checks cannot see wrong tool, order, or a missing later step. Step 2 measures it.
5. **Gateway changes outcomes by itself.** Step 4 catches it.
6. **Tiny n.** Report counts and flips, not rankings.
7. **Circular classification.** Fixed by the rubric plus hand-labeled sample.
8. **Timing confounds.** Fixed by interleaving.
9. **Scope creep and 8B compute.** Fixed by the cut list and model limits.

---

## 10. Decision rules (pre-committed)

- If semantic failures are more than half of dev chain failures (step 2): expect little from retry; headline becomes "format repair rescues X; retry rescues little."
- Whatever step 5 and the live holdout show for the coder, **update the TinyToolBench README with the measured number**, saying whether its 2/30 reflects Ollama tool-call compatibility.
- If dev gains far exceed holdout gains, report the gap as evidence of overfitting to dev.
- No arm is declared "best" from holdout results alone at this sample size.

## 11. Timing and applications

Do not gate internship applications on this project. TinyToolBench is already a finished, honest project. Apply now, and list TraceGate only as "in progress" with its true status until step 8 is done.

## 12. Done means

A holdout table (arm x model: tasks passed, wins/losses/ties vs A0, retries, overhead, no-tool regressions), a labeled-exploratory dev table, a failure taxonomy with the hand-label agreement, the tag trail (`holdout-frozen`, `gateway-frozen`), and a README that leads with the finding.
