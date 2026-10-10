from datetime import datetime


def parse_birth_date(text: str):
    """Parse a patient's birth date from the intake form, for example 03/04/25."""
    return datetime.strptime(text, "%d/%m/%y").date()
