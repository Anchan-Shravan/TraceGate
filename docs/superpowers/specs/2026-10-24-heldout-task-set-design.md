# TraceGate held-out task set design

## Goal

Create a separate set of 20 new tool-use tasks for TraceGate's main experiment. These tasks will be kept apart from the existing TinyToolBench v4 development tasks and will not be sent to a model until the gateway is frozen.

## Source and boundaries

- The reference benchmark lives at `C:\benchmark`.
- Reuse its four offered tools and their schemas: `add`, `multiply`, `get_price`, and `search_notes`.
- Reuse the fixed price and note data defined in `C:\benchmark\tools.py` so expected tool results can be checked directly.
- Keep the original benchmark folder unchanged. TraceGate's holdout files live under `D:\TraceGate\holdout`.
- Do not copy, lightly reword, or run a model on any of the 30 existing development tasks when creating or validating the holdout.

## Task mix

Create 20 tasks with these categories:

| Category | Count | Simple meaning |
|---|---:|---|
| `single` | 4 | One clear tool call |
| `selection` | 3 | Choose the right tool from the four available tools |
| `chain` | 6 | Make multiple calls where later calls use earlier results |
| `no_tool` | 4 | Answer without calling a tool |
| `robustness` | 3 | Handle a typo or an item/note that is not in the fixed data |

The wording must be new and should not be a paraphrase of any development prompt. Use different numbers, items, note keys, and combinations where possible. Since the available tool data is fixed, some broad task patterns will naturally repeat; the exact prompts and expected arguments must still be new.

## Files and responsibilities

- `holdout/tasks.json`: the 20 prompts and their expected calls/answers, in the same basic task format used by the benchmark.
- `holdout/validate_holdout.py`: a small offline checker for unique task IDs, exactly 20 tasks, the category counts above, valid tool names and arguments, required arguments, and basic JSON structure. It must not call Ollama or any model.
- `holdout/README.md`: plain-language notes explaining that the tasks are reserved, how to run the validator, and that a human must directly verify expected results using the fixed tool functions before freezing.

## Expected call and answer rules

- Store expected calls in their correct order for chains.
- A no-tool task has an empty `expected_calls` list.
- For a known price or note, expected answers must agree with the fixed data in `tools.py`.
- For arithmetic, expected answers must match the arithmetic represented by the calls.
- For unknown items, the expected call should still use the lookup tool with the requested unknown name; the tool result is the fixed not-found response.
- Do not use a model as an answer key. The task validator checks structure; direct tool calls and hand calculations verify the gold answers.

## Freeze and safety rules

- The holdout is not used to develop parser, detector, repair, retry, or checker rules.
- Once reviewed and verified, record a SHA-256 hash and freeze the task file before gateway development.
- If a task is later found to be flawed, report it and exclude it from all experiment arms equally. Do not edit the frozen task in place.

## Completion check

The first milestone is complete when all 20 tasks meet the category counts, the offline validator passes, each expected result has been directly checked or hand-calculated, and the user has reviewed the task wording before the holdout is frozen.
