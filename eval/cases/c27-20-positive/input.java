public final class TripTimer {
    /** Returns trip duration in milliseconds from the last GPS fix. */
    public static long durationMs(android.location.Location fix) {
        return System.currentTimeMillis() - fix.getTime();
    }
}
