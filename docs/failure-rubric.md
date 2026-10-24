# How we label development-run results

We label one model attempt at a time, using the prompt, expected calls, actual calls, and final answer. During hand review, ignore the automatic `passed` and `reason` fields. Judge what the model actually did.

Give each attempt one main label:

- `pass`: the model made the expected calls, if any, and gave a correct final answer.
- `runtime_error`: the program errored or timed out.
- `unexpected_tool_call`: the task expects no tool, but the model makes a structured call or clearly tries to call a tool in text.
- `tool_call_written_as_text`: the task needs a tool call, but the model writes the call in ordinary text instead of making a structured call.
- `no_tool_call`: the task needs a tool call, but the model makes none.
- `wrong_number_of_calls`: the model makes too many or too few calls.
- `wrong_tool`: the model calls a different tool from the expected one.
- `bad_schema`: the call has the wrong argument names or value types.
- `wrong_arguments`: the tool is right, but its values are wrong.
- `wrong_call_order`: all expected calls are present, but in the wrong order for a task marked as ordered.
- `wrong_final_answer`: the calls are correct, but the final answer is missing or incorrect.

## How to choose one label

Check in this order: runtime error; unexpected call on a no-tool task; pass; text-form call on a task that needs a tool; missing call; wrong call count; wrong tool; bad schema; wrong values; wrong order; wrong final answer.

If a result is unclear, write `uncertain` in the hand-review notes and explain why. Do not guess.

## Limits of the automatic classifier

The existing classifier checks argument names but not argument value types. It can also mark a no-tool task as a pass when the model's text contains a tool-call attempt or misleadingly contains the expected answer. Record these cases according to what the model actually did; count them as disagreements with the automatic label.
