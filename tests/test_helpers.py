"""Tests for canopy/helpers.py"""

from datetime import date, datetime

import pytest

from canopy.helpers import _validate_enum, _validate_iso8601_string, coerce_to_iso8601


class TestCoerceToIso8601:
    def test_valid_string_passthrough(self):
        value = "2024-01-15T10:30:00Z"
        assert coerce_to_iso8601(value) == value

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            coerce_to_iso8601("not-a-date")

    def test_date_object(self):
        result = coerce_to_iso8601(date(2024, 1, 15))
        assert result == "2024-01-15T00:00:00+00:00"

    def test_datetime_object(self):
        result = coerce_to_iso8601(datetime(2024, 1, 15, 10, 30, 0))
        assert result == "2024-01-15T10:30:00+00:00"

    def test_string_with_offset(self):
        value = "2024-01-15T10:30:00+07:00"
        assert coerce_to_iso8601(value) == value


class TestValidateEnum:
    def test_valid_single_value(self):
        assert _validate_enum("position", ["position", "name", "due_at"]) == "position"

    def test_invalid_single_value_raises(self):
        with pytest.raises(ValueError):
            _validate_enum("invalid", ["position", "name", "due_at"])

    def test_valid_list(self):
        result = _validate_enum(["position", "name"], ["position", "name", "due_at"])
        assert result == ["position", "name"]

    def test_invalid_list_raises(self):
        with pytest.raises(ValueError):
            _validate_enum(["position", "invalid"], ["position", "name", "due_at"])


class TestValidateIso8601String:
    def test_valid_utc(self):
        assert _validate_iso8601_string("2024-01-15T10:30:00Z") == "2024-01-15T10:30:00Z"

    def test_valid_offset(self):
        assert _validate_iso8601_string("2024-01-15T10:30:00+07:00") == "2024-01-15T10:30:00+07:00"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _validate_iso8601_string("2024-01-15")
