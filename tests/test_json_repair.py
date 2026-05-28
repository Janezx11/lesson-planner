"""
Tests for the unified JSON repair module.
"""

import pytest
import json
from llm.json_repair import extract_json_object, repair_json, parse_llm_json
from utils.parser import JSONParsingError


class TestExtractJsonObject:
    def test_simple_json(self):
        text = '{"key": "value"}'
        result = extract_json_object(text)
        assert result == '{"key": "value"}'

    def test_json_with_surrounding_text(self):
        text = 'Here is the output: {"key": "value"} end'
        result = extract_json_object(text)
        assert result == '{"key": "value"}'

    def test_nested_json(self):
        text = 'Result: {"a": {"b": 1}, "c": [1,2]} done'
        result = extract_json_object(text)
        parsed = json.loads(result)
        assert parsed["a"]["b"] == 1

    def test_no_json_raises(self):
        with pytest.raises(JSONParsingError):
            extract_json_object("no json here")

    def test_empty_braces(self):
        text = '{}'
        result = extract_json_object(text)
        assert result == '{}'


class TestRepairJson:
    def test_trailing_comma_in_object(self):
        broken = '{"a": 1, "b": 2,}'
        repaired = repair_json(broken)
        parsed = json.loads(repaired)
        assert parsed == {"a": 1, "b": 2}

    def test_trailing_comma_in_array(self):
        broken = '[1, 2, 3,]'
        repaired = repair_json(broken)
        parsed = json.loads(repaired)
        assert parsed == [1, 2, 3]

    def test_single_quotes(self):
        broken = "{'key': 'value'}"
        repaired = repair_json(broken)
        parsed = json.loads(repaired)
        assert parsed == {"key": "value"}

    def test_unbalanced_braces_close_missing(self):
        broken = '{"a": 1'
        repaired = repair_json(broken)
        parsed = json.loads(repaired)
        assert parsed == {"a": 1}

    def test_unbalanced_brackets_close_missing(self):
        broken = '{"a": [1, 2'
        repaired = repair_json(broken)
        parsed = json.loads(repaired)
        assert parsed == {"a": [1, 2]}

    def test_already_valid(self):
        valid = '{"a": 1, "b": "hello"}'
        repaired = repair_json(valid)
        parsed = json.loads(repaired)
        assert parsed == {"a": 1, "b": "hello"}


class TestParseLlmJson:
    def test_valid_json(self):
        text = '{"name": "test", "value": 42}'
        result = parse_llm_json(text)
        assert result == {"name": "test", "value": 42}

    def test_json_with_text_prefix(self):
        text = 'Here is the result:\n{"name": "test"}\nDone.'
        result = parse_llm_json(text)
        assert result == {"name": "test"}

    def test_json_with_trailing_comma(self):
        text = '{"a": 1, "b": 2,}'
        result = parse_llm_json(text)
        assert result["a"] == 1

    def test_json_with_single_quotes(self):
        text = "{'key': 'val'}"
        result = parse_llm_json(text)
        assert result["key"] == "val"

    def test_no_json_raises(self):
        with pytest.raises(JSONParsingError):
            parse_llm_json("completely empty text")

    def test_complex_real_response(self):
        """Simulate a real LLM response with markdown prefix."""
        text = """根据分析，输出如下：
```json
{
    "lesson_overview": "二次函数基础",
    "stages": [
        {"stage_name": "导入", "duration": "10分钟"}
    ]
}
```
"""
        result = parse_llm_json(text)
        assert result["lesson_overview"] == "二次函数基础"
        assert len(result["stages"]) == 1
