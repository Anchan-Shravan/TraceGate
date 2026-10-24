import json
import sys
from pathlib import Path

# Let Python find the original benchmark's tools.py file.
sys.path.insert(0, r"C:\benchmark")
from tools import TOOL_FUNCS

tasks_file = Path(__file__).with_name("tasks.json")
tasks = json.loads(tasks_file.read_text(encoding="utf-8"))

def normalize(value):
    # Ignore commas and capitalization when comparing answers.
    return str(value).replace(",", "").lower()

for task in tasks:
    calls = task["expected_calls"]

    if not calls:
        answer = task.get("expected_answer", "(no fixed answer)")
        print(f"MANUAL {task['id']}: no tool call; answer to review: {answer}")
        continue

    results = []
    try:
        for call in calls:
            tool = TOOL_FUNCS[call["name"]]
            result = tool(**call["args"])
            results.append(result)

        expected = task.get("expected_answer")
        actual = results[-1]

        if expected is None:
            print(f"CALLS OK {task['id']}: last tool result is {actual}")
        elif normalize(expected) in normalize(actual):
            print(f"PASS {task['id']}: expected answer matches tool result")
        else:
            print(
                f"CHECK {task['id']}: expected {expected!r}, "
                f"but the last tool returned {actual!r}"
            )

    except Exception as error:
        print(f"ERROR {task['id']}: {error}")