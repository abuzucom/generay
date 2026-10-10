def caption_start_seconds(frame_count: int) -> float:
    """Return the caption cue time for an NTSC broadcast master."""
    return frame_count / 30
