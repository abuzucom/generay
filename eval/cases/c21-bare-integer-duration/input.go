package worker

import "time"

type Config struct {
	RetryDelaySeconds int
}

// Backoff waits before the next delivery attempt.
func Backoff(cfg Config) {
	time.Sleep(time.Duration(cfg.RetryDelaySeconds))
}
