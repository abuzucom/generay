CREATE TABLE loans (
  id BIGINT PRIMARY KEY,
  borrower_id BIGINT NOT NULL,
  maturity_at TIMESTAMP NOT NULL
);
