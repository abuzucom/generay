import random
import time


def reset_token() -> str:
    """Return the password reset token emailed to the user."""
    random.seed(time.time())
    return "%032x" % random.getrandbits(128)
