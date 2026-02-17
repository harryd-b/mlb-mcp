"""
Utilities for transforming JSON schemas to be Anthropic-compatible.

Anthropic's tool calling API doesn't support certain JSON Schema features:
- anyOf with null (used by Pydantic for Optional types)
- additionalProperties: true
- Other advanced JSON Schema features

This module provides functions to simplify schemas for compatibility.
"""

from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def simplify_tool_schemas(mcp: "FastMCP") -> None:
    """
    Simplify all tool schemas in a FastMCP instance for Anthropic compatibility.

    This should be called after all tools are registered but before the server
    starts handling requests.

    Args:
        mcp: The FastMCP instance with registered tools
    """
    tools = mcp._tool_manager._tools
    for tool_name, tool in tools.items():
        # Simplify the parameters (inputSchema) in place
        simplified = simplify_schema_for_anthropic(tool.parameters)
        tool.parameters.clear()
        tool.parameters.update(simplified)


def simplify_schema_for_anthropic(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a JSON schema to be compatible with Anthropic's tool calling API.

    Handles:
    - anyOf: [{"type": "X"}, {"type": "null"}] -> {"type": "X"}
    - additionalProperties: true -> removed
    - Recursive handling of nested properties

    Args:
        schema: The original JSON schema

    Returns:
        A simplified schema compatible with Anthropic's API
    """
    if not isinstance(schema, dict):
        return schema

    result = {}

    for key, value in schema.items():
        if key == "anyOf":
            # Handle Optional types: anyOf: [{"type": "X"}, {"type": "null"}]
            simplified = _simplify_any_of(value)
            if simplified:
                result.update(simplified)
            else:
                result[key] = value
        elif key == "additionalProperties":
            # Skip additionalProperties as Anthropic doesn't support it well
            continue
        elif key == "properties":
            # Recursively simplify nested properties
            result[key] = {
                prop_name: simplify_schema_for_anthropic(prop_schema)
                for prop_name, prop_schema in value.items()
            }
        elif key == "items":
            # Recursively simplify array items
            result[key] = simplify_schema_for_anthropic(value)
        elif isinstance(value, dict):
            # Recursively simplify any nested dict
            result[key] = simplify_schema_for_anthropic(value)
        elif isinstance(value, list):
            # Recursively simplify items in lists
            result[key] = [
                simplify_schema_for_anthropic(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    return result


def _simplify_any_of(any_of_value: list) -> Dict[str, Any] | None:
    """
    Simplify an anyOf array, typically used for Optional types.

    Converts anyOf: [{"type": "X"}, {"type": "null"}] to {"type": "X"}

    Args:
        any_of_value: The anyOf array value

    Returns:
        Simplified schema dict, or None if can't simplify
    """
    if not isinstance(any_of_value, list):
        return None

    # Filter out null types
    non_null_types = [
        item for item in any_of_value
        if isinstance(item, dict) and item.get("type") != "null"
    ]

    if len(non_null_types) == 1:
        # Single non-null type - return it directly (simplified)
        return simplify_schema_for_anthropic(non_null_types[0])
    elif len(non_null_types) > 1:
        # Multiple non-null types - can't simplify to single type
        # Return as oneOf instead (Anthropic may still not support this)
        return {"oneOf": [simplify_schema_for_anthropic(t) for t in non_null_types]}

    return None
