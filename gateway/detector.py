def validate_tool_call(call: dict, tool_schemas: list[dict]) -> bool:
    """Check a parsed call against the tool names and argument types in its schemas."""
    if not isinstance(call, dict) or not isinstance(tool_schemas, list):
        return False

    name = call.get("name")
    arguments = call.get("args")

    if not isinstance(name, str) or not name.strip():
        return False
    if not isinstance(arguments, dict):
        return False

    for tool in tool_schemas:
        if not isinstance(tool, dict):
            continue

        function = tool.get("function")
        if not isinstance(function, dict) or function.get("name") != name:
            continue

        parameters = function.get("parameters")
        if not isinstance(parameters, dict):
            return False

        properties = parameters.get("properties")
        required = parameters.get("required", [])

        if not isinstance(properties, dict) or not isinstance(required, list):
            return False
        if any(key not in arguments for key in required):
            return False
        if any(key not in properties for key in arguments):
            return False

        for key, value in arguments.items():
            property_schema = properties.get(key)
            if not isinstance(property_schema, dict):
                return False

            expected_type = property_schema.get("type")

            if expected_type == "string":
                if not isinstance(value, str):
                    return False
            elif expected_type == "integer":
                if type(value) is not int:
                    return False
            else:
                return False

        return True

    return False