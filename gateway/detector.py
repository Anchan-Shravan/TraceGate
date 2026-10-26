def tool_call_errors(call: dict, tool_schemas: list[dict]) -> list[str]:
    """Return schema problems for a normalized call; an empty list means valid."""
    if not isinstance(call, dict):
        return ["Tool call must be an object."]
    if not isinstance(tool_schemas, list):
        return ["Tool schemas must be a list."]

    name = call.get("name")
    arguments = call.get("args")
    if not isinstance(name, str) or not name.strip():
        return ["Tool name must be a non-empty string."]
    if not isinstance(arguments, dict):
        return ["Tool arguments must be a JSON object."]

    matched_tool = None
    for tool in tool_schemas:
        if not isinstance(tool, dict):
            continue
        function = tool.get("function")
        if isinstance(function, dict) and function.get("name") == name:
            matched_tool = function
            break

    if matched_tool is None:
        return [f"Unknown tool: {name}."]

    parameters = matched_tool.get("parameters")
    if not isinstance(parameters, dict):
        return [f"The schema for {name} has no valid parameters object."]
    properties = parameters.get("properties")
    required = parameters.get("required", [])
    if not isinstance(properties, dict) or not isinstance(required, list):
        return [f"The schema for {name} has invalid properties or required fields."]

    errors = []
    missing = [key for key in required if key not in arguments]
    extra = [key for key in arguments if key not in properties]
    if missing:
        errors.append("Missing required arguments: " + ", ".join(map(str, missing)) + ".")
    if extra:
        errors.append("Unknown arguments: " + ", ".join(map(str, extra)) + ".")

    for key, value in arguments.items():
        property_schema = properties.get(key)
        if not isinstance(property_schema, dict):
            continue
        expected_type = property_schema.get("type")
        if expected_type == "string" and not isinstance(value, str):
            errors.append(f"Argument {key} must be a string.")
        elif expected_type == "integer" and type(value) is not int:
            errors.append(f"Argument {key} must be an integer.")
        elif expected_type not in ("string", "integer"):
            errors.append(f"Argument {key} has an unsupported schema type.")

    return errors


def validate_tool_call(call: dict, tool_schemas: list[dict]) -> bool:
    """Check a normalized call against its tool name and JSON argument schema."""
    return not tool_call_errors(call, tool_schemas)
