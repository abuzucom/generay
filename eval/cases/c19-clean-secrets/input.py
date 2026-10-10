import secrets


def reset_token() -> str:
    """Return the password reset token emailed to the user."""
    return secrets.token_urlsafe(32)
