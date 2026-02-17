"""
Tests for schema utilities that simplify JSON schemas for Anthropic compatibility.
"""

import pytest

from mlb_stats_mcp.schema_utils import simplify_schema_for_anthropic


class TestSimplifySchemaForAnthropic:
    """Test suite for schema simplification."""

    def test_simplifies_optional_int(self):
        """Should convert anyOf with null to simple type."""
        schema = {
            "anyOf": [
                {"type": "integer"},
                {"type": "null"}
            ],
            "default": None,
            "title": "Season"
        }
        result = simplify_schema_for_anthropic(schema)
        assert result == {
            "type": "integer",
            "default": None,
            "title": "Season"
        }

    def test_simplifies_optional_string(self):
        """Should convert anyOf string/null to simple string type."""
        schema = {
            "anyOf": [
                {"type": "string"},
                {"type": "null"}
            ],
            "default": None
        }
        result = simplify_schema_for_anthropic(schema)
        assert result == {
            "type": "string",
            "default": None
        }

    def test_removes_additional_properties(self):
        """Should remove additionalProperties from schema."""
        schema = {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "name": {"type": "string"}
            }
        }
        result = simplify_schema_for_anthropic(schema)
        assert "additionalProperties" not in result
        assert result["properties"]["name"]["type"] == "string"

    def test_preserves_array_items(self):
        """Should preserve array items definition."""
        schema = {
            "type": "array",
            "items": {"type": "integer"},
            "title": "Player Ids"
        }
        result = simplify_schema_for_anthropic(schema)
        assert result == schema

    def test_simplifies_nested_properties(self):
        """Should recursively simplify nested properties."""
        schema = {
            "type": "object",
            "properties": {
                "season": {
                    "anyOf": [
                        {"type": "integer"},
                        {"type": "null"}
                    ],
                    "default": None
                },
                "team_id": {
                    "type": "integer"
                }
            },
            "required": ["team_id"]
        }
        result = simplify_schema_for_anthropic(schema)
        assert result["properties"]["season"] == {
            "type": "integer",
            "default": None
        }
        assert result["properties"]["team_id"] == {"type": "integer"}
        assert result["required"] == ["team_id"]

    def test_handles_non_nullable_anyof(self):
        """Should handle anyOf with multiple non-null types."""
        schema = {
            "anyOf": [
                {"type": "integer"},
                {"type": "string"}
            ]
        }
        result = simplify_schema_for_anthropic(schema)
        # Should convert to oneOf since we can't simplify to single type
        assert "oneOf" in result
        assert len(result["oneOf"]) == 2

    def test_preserves_simple_types(self):
        """Should preserve simple type definitions unchanged."""
        schema = {
            "type": "string",
            "title": "Name",
            "description": "Player name"
        }
        result = simplify_schema_for_anthropic(schema)
        assert result == schema

    def test_handles_empty_schema(self):
        """Should handle empty schema."""
        result = simplify_schema_for_anthropic({})
        assert result == {}

    def test_handles_non_dict_input(self):
        """Should return non-dict input unchanged."""
        assert simplify_schema_for_anthropic("string") == "string"
        assert simplify_schema_for_anthropic(123) == 123
        assert simplify_schema_for_anthropic(None) is None
