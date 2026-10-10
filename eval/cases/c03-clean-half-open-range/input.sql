-- Daily revenue for one local business date, computed as a half-open range.
SELECT SUM(amount_cents)
FROM payments
WHERE paid_at >= :day_start
  AND paid_at < :next_day_start;
