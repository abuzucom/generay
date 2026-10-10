import java.time.ZoneId;

public final class FeedZones {
    /** Resolves the IANA zone the partner contract requires; unknown IDs throw. */
    public static ZoneId fromFeed(String ianaId) {
        return ZoneId.of(ianaId);
    }
}
