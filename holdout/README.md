# TraceGate held-out tasks

This folder contains 20 tasks reserved for the final TraceGate experiment.

## Task categories

- 4 single-call tasks
- 3 tool-selection tasks
- 6 multi-step tasks (chains)
- 4 no-tool tasks
- 3 robustness tasks

## Keep these tasks reserved

Do not send these prompts to a model while building or changing the gateway, parser, detector, repair rules, retry message, or checker. Use them for the experiment only after the gateway is frozen.

If a task is later found to be flawed, report it and leave it out of every experiment arm equally. Do not quietly edit the frozen file.

## Files

- `tasks.json` contains the prompts and expected calls.
- `verify_holdout.py` checks expected tool calls against the fixed tools in `C:\benchmark\tools.py`. It does not run a model.

Run the checker from the TraceGate project folder:

```powershell
python .\holdout\verify_holdout.py
## Held-out task fingerprint

SHA-256 of `tasks.json`: `<55321566A58DD6AB647A328C7171CDE02B2500BB035D45ED333ED281419509DC  >`

