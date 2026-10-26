# Development failure review summary

## What was reviewed

- Source: the old TinyToolBench v4 raw results in `C:\benchmark\results\results_v4.csv`.
- Sample: 20 randomly selected attempts from 360 total attempts.
- Review inputs: task prompt, expected calls and answer, actual calls, status, and final text. The automatic `passed` and `reason` fields were not used to assign the review labels.
- Labels and row-by-row comparison: `manual_review_sample.csv` and `manual_review_comparison.csv`.

## Review result

The rubric-based review labels match the existing automatic labels on 14 of 20 attempts (70%). This is a descriptive result for this small sample, not an estimate of accuracy across all runs.

The labels were assigned by the assistant from the saved development records. No independent human annotator checked them. Therefore, this is **not human hand-label agreement** and should not be presented as independent validation. The six disagreements were rechecked against the written rubric; the decisions and reasons are recorded below.

## Disagreements and rubric decisions

| Model / task / run | Review label | Automatic label | Rubric decision |
|---|---|---|---|
| qwen2.5-coder:7b / n3 / 3 | `unexpected_tool_call` | `pass` | The no-tool task asks to add a word to notes. The final text is JSON shaped like a `search_notes` call, even though the runner records no structured call. The rubric prioritizes an attempted call on a no-tool task. |
| qwen2.5-coder:7b / n5 / 2 | `unexpected_tool_call` | `pass` | The no-tool joke task has the same issue: the final text is JSON shaped like a `search_notes` call, but the runner records no structured call. |
| qwen3:8b / c1 / 1 | `bad_schema` | `wrong_arguments` | The `a` value is a result-reference object, not the integer required by the tool schema. This is a type/schema error, even though the argument name is valid. |
| qwen3:4b / n1 / 3 | `wrong_final_answer` | `no_tool_call` | This is a no-tool task, so making no call is correct. The model fails because it does not answer “Paris.” |
| qwen3:4b / n2 / 3 | `wrong_final_answer` | `pass` | The response repeats the request while explaining why it cannot comply, but it never actually greets the user. Mentioning “hello” is not completing the request. |
| qwen2.5-coder:7b / n2 / 2 | `unexpected_tool_call` | `tool_call_written_as_text` | The no-tool task returns a JSON-shaped call with `name: None`. The rubric prioritizes an attempted tool call on a no-tool task, so this is labeled `unexpected_tool_call`. |

## Limits

The sample has only 20 rows, and the review was not independent. The 70% figure describes agreement between the existing automatic labels and this assistant-applied rubric on this sample only. A separate human review would be needed to claim human agreement. The automatic classifier has known gaps: it misses text-form tool attempts, does not check argument value types, and can treat a no-tool task as passed based on a word appearing in the response.
