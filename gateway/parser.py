import json
import re


_TOOL_CALL_BLOCK = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.IGNORECASE | re.DOTALL)
_FENCED_BLOCK = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)
_MALFORMED_CALL = re.compile(
    r'"name"\s*:\s*(?:"[^"\\]*(?:\\.[^"\\]*)*"|null)'
    r'[\s\S]*?"(?:arguments|parameters)"\s*:',
    re.IGNORECASE,
)


def _normalize_candidate(value: dict) -> dict:
    name = value.get("name")
    if not isinstance(name, str) or not name.strip():
        return {"call": None, "error": "Tool name must be a non-empty string."}

    if "arguments" in value:
        arguments = value["arguments"]
    else:
        arguments = value.get("parameters")

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return {"call": None, "error": "Tool arguments contain invalid JSON."}

    if not isinstance(arguments, dict):
        return {"call": None, "error": "Tool arguments must be a JSON object."}

    return {"call": {"name": name, "args": arguments}, "error": None}


def find_text_tool_call_candidates(text: str) -> list[dict]:
    """Find strict JSON tool-call candidates, including supported wrappers.

    Ordinary prose and examples like ``add(2, 3)`` are ignored. A returned
    candidate may contain an error when it is visibly call-shaped but malformed.
    """
    if not isinstance(text, str) or not text.strip():
        return []

    regions = _TOOL_CALL_BLOCK.findall(text)
    if not regions:
        regions = _FENCED_BLOCK.findall(text)
    if not regions:
        stripped = text.strip()
        if stripped.startswith(("{", "[", "```", "<tool_call")):
            regions = [stripped]
        else:
            return []

    decoder = json.JSONDecoder()
    candidates = []
    for region in regions:
        found_in_region = False
        for index, character in enumerate(region):
            if character != "{":
                continue
            try:
                value, _end = decoder.raw_decode(region, index)
            except json.JSONDecodeError:
                continue
            if not isinstance(value, dict) or "name" not in value:
                continue
            if "arguments" not in value and "parameters" not in value:
                continue
            candidates.append(_normalize_candidate(value))
            found_in_region = True

        if not found_in_region and _MALFORMED_CALL.search(region):
            candidates.append({"call": None, "error": "Tool-call JSON is malformed."})

    return candidates


def parse_text_tool_call(text: str) -> dict | None:
    """Return one valid JSON tool call, or None if it is absent or ambiguous."""
    candidates = find_text_tool_call_candidates(text)
    if len(candidates) != 1 or candidates[0]["error"]:
        return None
    return candidates[0]["call"]
