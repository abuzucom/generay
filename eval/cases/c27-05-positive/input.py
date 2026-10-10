def alignment_loop(reference, stream_a, stream_b):
    """Align two streams once at start, then by sample index."""
    offset = reference.offset_at_start()
    while True:
        a, b = stream_a.next(), stream_b.next()
        yield a, b[offset:]
