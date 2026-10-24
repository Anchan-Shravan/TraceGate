# Development failure review summary

## What was reviewed

- Source: the old TinyToolBench v4 raw results in `C:\benchmark\results\results_v4.csv`.
- Sample: 20 randomly selected attempts from 360 total attempts.
- Hand-review inputs: task prompt, expected calls and answer, actual calls, status, and final text. The automatic `passed` and `reason` fields were not included in the review sample.
- Labels and row-by-row comparison: `manual_review_sample.csv` and `manual_review_comparison.csv`.

## Agreement

The manual labels matched the existing automatic labels on 14 of 20 attempts (70%). This is a descriptive result for this small sample, not a confidence claim about all runs.

The labels were prepared by the assistant from the raw records at the user's request. The six disagreements should be reviewed by the project owner before describing this as human hand-label agreement in a public report.

## Disagreements to review

| Model / task / run | Manual label | Automatic label | Why they differ |
|---|---|---|---|
| qwen2.5-coder:7b / n3 / 3 | `unexpected_tool_call` | `pass` | The no-tool task asks to add a word to notes. The response is a text-form `search_notes` call, but the runner records no structured call and marks the attempt passed. |
| qwen2.5-coder:7b / n5 / 2 | `unexpected_tool_call` | `pass` | The no-tool joke task received a text-form `search_notes` call, but the runner records no structured call and marks it passed. |
| qwen3:8b / c1 / 1 | `bad_schema` | `wrong_arguments` | The `a` argument is a result-reference object instead of the integer the schema requires. The automatic classifier checks argument names, not value types. |
| qwen3:4b / n1 / 3 | `wrong_final_answer` | `no_tool_call` | No call is correct for this task; the answer about France is missing. The classifier labels any failed row with no structured calls as `no_tool_call`. |
| qwen3:4b / n2 / 3 | `wrong_final_answer` | `pass` | The response discusses the request but does not actually greet the user. The automatic pass appears to accept the expected word mentioned in the response rather than a completed greeting. |
| qwen2.5-coder:7b / n2 / 2 | `unexpected_tool_call` | `tool_call_written_as_text` | The no-tool task received a text-form object with `name: None`; the manual review prioritizes that it attempted a tool call on a no-tool task. |

## Limits and next step

The sample has only 20 rows, and its labels were assistant-prepared rather than independently assigned by a second human. Review the six disagreements and confirm the rubric before using the 70% figure in a public write-up. After that review, continue to the A0 gateway prototype in the project plan.
