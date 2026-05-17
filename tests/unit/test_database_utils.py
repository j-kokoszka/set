import pytest
from decimal import Decimal
from database import to_dynamo_item, from_dynamo_item

def test_to_dynamo_item_floats():
    data = {"weight": 60.5, "reps": 10}
    converted = to_dynamo_item(data)
    assert isinstance(converted["weight"], Decimal)
    assert converted["weight"] == Decimal("60.5")
    assert converted["reps"] == 10

def test_to_dynamo_item_none_removal():
    data = {"id": None, "name": "Test", "notes": None}
    converted = to_dynamo_item(data)
    assert "id" not in converted
    assert "notes" not in converted
    assert converted["name"] == "Test"

def test_to_dynamo_item_nested():
    data = {
        "exercises": [
            {"name": "Squat", "sets": [{"weight": 100.0, "reps": 5}]}
        ]
    }
    converted = to_dynamo_item(data)
    assert isinstance(converted["exercises"][0]["sets"][0]["weight"], Decimal)

def test_from_dynamo_item_decimals():
    item = {"weight": Decimal("60.5"), "reps": Decimal("10")}
    converted = from_dynamo_item(item)
    assert isinstance(converted["weight"], float)
    assert converted["weight"] == 60.5
    assert isinstance(converted["reps"], int)
    assert converted["reps"] == 10

def test_from_dynamo_item_nested():
    item = {
        "exercises": [
            {"name": "Squat", "sets": [{"weight": Decimal("100.0"), "reps": Decimal("5")}]}
        ]
    }
    converted = from_dynamo_item(item)
    # 100.0 % 1 == 0, so it should be int
    assert isinstance(converted["exercises"][0]["sets"][0]["weight"], int)
    assert converted["exercises"][0]["sets"][0]["weight"] == 100

def test_to_dynamo_item_deeply_nested():
    data = {"a": {"b": [{"c": 1.1}]}}
    converted = to_dynamo_item(data)
    assert converted["a"]["b"][0]["c"] == Decimal("1.1")
