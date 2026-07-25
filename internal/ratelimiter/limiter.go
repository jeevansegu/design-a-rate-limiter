package ratelimiter

import "context"

type RateLimiter interface {
	Allow(key string, ctx context.Context) bool
}
