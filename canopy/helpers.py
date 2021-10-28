import re


def _validate_enum(value, acceptable_values):
    if not type(value) == list:
        if value in acceptable_values:
            return value
        else:
            raise ValueError(f"{value} not in {acceptable_values}")
    else:
        for v in value:
            if v in acceptable_values:
                return value
            else:
                raise ValueError(f"{value} not in {acceptable_values}")


def _validate_iso8601_string(value):
    """Return the value or raise a ValueError if it is not a string in ISO8601 format."""
    ISO8601_REGEX = (
        r"(\d{4})-(\d{2})-(\d{2})T(\d{2})\:(\d{2})\:(\d{2})([+-](\d{2})\:(\d{2})|Z)"
    )
    if re.match(ISO8601_REGEX, value):
        return value
    else:
        raise ValueError(f"{value} must be in ISO8601 format.")
