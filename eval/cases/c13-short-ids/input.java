import java.time.ZoneId;

public final class FeedZones {
    /** Resolves the zone abbreviation a partner feed sends with each shipment time. */
    public static ZoneId fromFeed(String abbreviation) {
        return ZoneId.of(abbreviation, ZoneId.SHORT_IDS);
    }
}
