import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

public final class InvoiceDates {
    private static final DateTimeFormatter PRINTED = DateTimeFormatter.ofPattern("YYYY-MM-dd");

    /** Formats the issue date printed on legal invoices. */
    public static String printed(LocalDate issued) {
        return PRINTED.format(issued);
    }
}
