from datetime import date


def parse_birth_date(text: str) -> date:
    """Parse a birth date the form submits as ISO YYYY-MM-DD from a date picker."""
    return date.fromisoformat(text)
