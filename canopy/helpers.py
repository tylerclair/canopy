import re
from datetime import date, datetime


def _validate_enum(value: str | list[str], acceptable_values: list[str]) -> str | list[str]:
    values = value if isinstance(value, list) else [value]
    for v in values:
        if v not in acceptable_values:
            raise ValueError(f"{v!r} not in {acceptable_values}")
    return value


def _validate_iso8601_string(value: str) -> str:
    """Return the value or raise a ValueError if it is not a string in ISO8601 format."""
    ISO8601_REGEX = r"(\d{4})-(\d{2})-(\d{2})T(\d{2})\:(\d{2})\:(\d{2})([+-](\d{2})\:(\d{2})|Z)"
    if re.match(ISO8601_REGEX, value):
        return value
    raise ValueError(f"{value!r} must be in ISO8601 format.")


def coerce_to_iso8601(value: str | date | datetime) -> str:
    """Coerce a string, date, or datetime to an ISO8601 formatted string."""
    if isinstance(value, str):
        return _validate_iso8601_string(value)
    return value.strftime("%Y-%m-%dT%H:%M:%S+00:00")
