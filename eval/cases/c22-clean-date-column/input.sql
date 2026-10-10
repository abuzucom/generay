CREATE TABLE loans (
  id BIGINT PRIMARY KEY,
  borrower_id BIGINT NOT NULL,
  -- Maturity is a calendar date in the lender's jurisdiction.
  maturity_date DATE NOT NULL
);
