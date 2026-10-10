import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneOffset;

public final class ExportNames {
    /** Returns the archive file name for the UTC date on the injected clock. */
    public static String archiveName(Clock clock) {
        LocalDate today = LocalDate.now(clock.withZone(ZoneOffset.UTC));
        return "export-" + today + ".csv";
    }
}
