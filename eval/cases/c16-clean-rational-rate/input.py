from fractions import Fraction

NTSC_RATE = Fraction(30000, 1001)


def caption_start_seconds(frame_count: int) -> Fraction:
    """Return the cue time from an exact rational frame rate."""
    return frame_count / NTSC_RATE
