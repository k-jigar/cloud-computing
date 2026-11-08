import json
import pytest
from service.app import validate_schema, ALLOWED_INTENTS, EXPECTED_KEYS

def test_valid_schema():
    valid_data = {
        "intent": "weather_query",
        "date": "today",
        "time": "morning",
        "place": "paris"
    }
    assert validate_schema(valid_data) is True

def test_invalid_keys():
    # Missing 'place'
    missing_key = {"intent": "weather_query", "date": "today", "time": "morning"}
    assert validate_schema(missing_key) is False

    # Extra unexpected key
    extra_key = {
        "intent": "weather_query",
        "date": "today",
        "time": "morning",
        "place": "paris",
        "extra": "bad"
    }
    assert validate_schema(extra_key) is False

def test_invalid_intent():
    invalid_intent = {
        "intent": "non_existent_intent",
        "date": None,
        "time": None,
        "place": None
    }
    assert validate_schema(invalid_intent) is False

def test_slot_null_and_types():
    # Nulls are valid
    all_nulls = {
        "intent": "alarm_query",
        "date": None,
        "time": None,
        "place": None
    }
    assert validate_schema(all_nulls) is True

    # Non-string slot is invalid
    wrong_type = {
        "intent": "alarm_query",
        "date": 12345,
        "time": None,
        "place": None
    }
    assert validate_schema(wrong_type) is False

