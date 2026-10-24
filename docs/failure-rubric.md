# How we label development-run results

We label one model attempt at a time. Give each attempt one main result:

- `pass`: the attempt meets the benchmarkâ€™s pass rules.
- `runtime_error`: the program errored or timed out.
- `unexpected_tool_call`: the task expects no tool, but the model calls one.
- `tool_call_written_as_text`: the model writes something that looks like a tool call in its normal text, instead of making a structured tool call.
- `no_tool_call`: the task needs a tool call, but the model makes none.
- `wrong_number_of_calls`: the model makes too many or too few calls.
- `wrong_tool`: the model calls a different tool from the expected one.
- `bad_schema`: the call has the wrong argument names.
- `wrong_arguments`: the tool is right, but its values are wrong.
- `wrong_call_order`: all expected calls are present, but in the wrong order for a task marked as ordered.
- `wrong_final_answer`: the calls are correct, but the final answer is missing or incorrect.

## How to choose one label

Check in this order: runtime error; pass; unnecessary call on a no-tool task; text-form call; missing call; wrong call count; wrong tool; bad schema; wrong values; wrong order; wrong final answer.

If a result is unclear, write `uncertain` in the hand-review notes and explain why. Do not guess.

Note: The existing automatic classifier does not check argument value types. Record a type-only mismatch as a disagreement.
