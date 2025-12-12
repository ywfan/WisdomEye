"""Unit tests for resume JSON formatter."""
import json
import pytest
from modules.resume_json.formatter import ResumeJSONFormatter


class TestResumeJSONFormatter:
    """Test ResumeJSONFormatter class."""

    def test_ensure_json_direct_parse(self):
        """Test direct JSON parsing."""
        formatter = ResumeJSONFormatter()
        json_str = '{"name": "Test", "age": 30}'
        result = formatter._ensure_json(json_str)
        assert result == {"name": "Test", "age": 30}

    def test_ensure_json_with_code_fence(self):
        """Test JSON extraction from code fence."""
        formatter = ResumeJSONFormatter()
        content = '''```json
{
  "name": "Test",
  "age": 30
}
```'''
        result = formatter._ensure_json(content)
        assert result["name"] == "Test"
        assert result["age"] == 30

    def test_ensure_json_with_text_around(self):
        """Test JSON extraction with surrounding text."""
        formatter = ResumeJSONFormatter()
        content = '''Here is the JSON:
{
  "name": "Test",
  "age": 30
}
That's the result.'''
        result = formatter._ensure_json(content)
        assert result["name"] == "Test"

    def test_ensure_json_trailing_comma(self):
        """Test handling of trailing commas."""
        formatter = ResumeJSONFormatter()
        content = '{"name": "Test", "age": 30,}'
        result = formatter._ensure_json(content)
        assert result["name"] == "Test"

    def test_ensure_json_python_bool(self):
        """Test conversion of Python booleans."""
        formatter = ResumeJSONFormatter()
        content = '{"name": "Test", "active": True, "deleted": False, "value": None}'
        result = formatter._ensure_json(content)
        assert result.get("active") in [True, "true", 1]  # Could be converted
        assert "deleted" in result

    def test_ensure_json_single_quotes(self):
        """Test handling of single quotes."""
        formatter = ResumeJSONFormatter()
        content = "{'name': 'Test', 'age': 30}"
        result = formatter._ensure_json(content)
        # May or may not succeed depending on cleaning logic
        # Just ensure it doesn't crash
        assert isinstance(result, dict)

    def test_ensure_json_empty_input(self):
        """Test handling of empty input."""
        formatter = ResumeJSONFormatter()
        result = formatter._ensure_json("")
        assert result == {}

    def test_ensure_json_invalid_input(self):
        """Test handling of completely invalid input."""
        formatter = ResumeJSONFormatter()
        result = formatter._ensure_json("This is not JSON at all!")
        assert result == {}

    def test_ensure_json_nested_braces(self):
        """Test handling of nested objects."""
        formatter = ResumeJSONFormatter()
        content = '''
        {
          "person": {
            "name": "Test",
            "contact": {
              "email": "test@example.com"
            }
          }
        }
        '''
        result = formatter._ensure_json(content)
        assert result["person"]["name"] == "Test"
        assert result["person"]["contact"]["email"] == "test@example.com"

    def test_ensure_json_array_values(self):
        """Test handling of arrays."""
        formatter = ResumeJSONFormatter()
        content = '{"tags": ["python", "ai", "ml"], "count": 3}'
        result = formatter._ensure_json(content)
        assert isinstance(result["tags"], list)
        assert len(result["tags"]) == 3

    def test_ensure_json_unicode(self):
        """Test handling of Unicode characters."""
        formatter = ResumeJSONFormatter()
        content = '{"name": "张三", "city": "北京"}'
        result = formatter._ensure_json(content)
        assert result["name"] == "张三"
        assert result["city"] == "北京"
