"""Unit tests for schema contract."""
import pytest
from pathlib import Path
from infra.schema_contract import SchemaContract


class TestSchemaContract:
    """Test schema validation and conformance."""

    @pytest.fixture
    def simple_schema(self, tmp_path):
        """Create a simple test schema."""
        schema = {
            "name": "string",
            "age": "string",
            "tags": ["string"]
        }
        import json
        schema_file = tmp_path / "test_schema.json"
        schema_file.write_text(json.dumps(schema))
        return str(schema_file)

    def test_valid_object(self, simple_schema):
        """Test validation of valid object."""
        contract = SchemaContract(schema_path=simple_schema)
        obj = {
            "name": "John",
            "age": "30",
            "tags": ["developer", "python"]
        }
        ok, errors = contract.validate(obj)
        assert ok is True
        assert len(errors) == 0

    def test_missing_field(self, simple_schema):
        """Test validation with missing field."""
        contract = SchemaContract(schema_path=simple_schema)
        obj = {
            "name": "John",
            "tags": []
        }
        ok, errors = contract.validate(obj)
        assert ok is False
        assert any("age" in e for e in errors)

    def test_wrong_type(self, simple_schema):
        """Test validation with wrong type."""
        contract = SchemaContract(schema_path=simple_schema)
        obj = {
            "name": "John",
            "age": 30,  # Should be string
            "tags": []
        }
        ok, errors = contract.validate(obj)
        assert ok is False
        assert any("age" in e and "string" in e for e in errors)

    def test_conform_missing_fields(self, simple_schema):
        """Test conforming object with missing fields."""
        contract = SchemaContract(schema_path=simple_schema)
        obj = {"name": "John"}
        conformed = contract.conform(obj)
        
        assert "name" in conformed
        assert "age" in conformed
        assert "tags" in conformed
        assert conformed["age"] == ""
        assert conformed["tags"] == []

    def test_conform_wrong_types(self, simple_schema):
        """Test conforming object with wrong types."""
        contract = SchemaContract(schema_path=simple_schema)
        obj = {
            "name": 123,  # Wrong type
            "age": "30",
            "tags": "not-a-list"  # Wrong type
        }
        conformed = contract.conform(obj)
        
        assert conformed["name"] == ""  # Coerced to empty string
        assert conformed["age"] == "30"
        assert conformed["tags"] == []  # Coerced to empty list

    def test_template_generation(self, simple_schema):
        """Test template generation from schema."""
        contract = SchemaContract(schema_path=simple_schema)
        template = contract.template()
        
        assert template == {
            "name": "",
            "age": "",
            "tags": []
        }

    def test_nested_schema(self, tmp_path):
        """Test validation with nested objects."""
        schema = {
            "person": {
                "name": "string",
                "contact": {
                    "email": "string"
                }
            }
        }
        import json
        schema_file = tmp_path / "nested_schema.json"
        schema_file.write_text(json.dumps(schema))
        
        contract = SchemaContract(schema_path=str(schema_file))
        
        obj = {
            "person": {
                "name": "John",
                "contact": {
                    "email": "john@example.com"
                }
            }
        }
        ok, errors = contract.validate(obj)
        assert ok is True

    def test_invalid_schema_file(self):
        """Test handling of invalid schema file."""
        contract = SchemaContract(schema_path="nonexistent.json")
        assert contract.schema == {}
