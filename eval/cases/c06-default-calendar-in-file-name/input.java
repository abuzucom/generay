import java.util.Calendar;

public final class ExportNames {
    /** Returns the archive file name for today's export. */
    public static String archiveName() {
        Calendar now = Calendar.getInstance();
        return String.format("export-%04d-%02d-%02d.csv",
            now.get(Calendar.YEAR), now.get(Calendar.MONTH) + 1, now.get(Calendar.DAY_OF_MONTH));
    }
}
