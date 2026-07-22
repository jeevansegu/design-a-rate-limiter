package ratelimiter

import (
	"context"
	"strconv"
	"time"

	"github.com/jeevansegu/design-a-rate-limiter/internal/redisstore"
	"github.com/redis/go-redis/v9"
)

type RedisTokenBucket struct {
	store    *redisstore.Client
	capacity int64
	rate     int64
	ttl      time.Duration
}

func NewRedisTokenBucket(store *redisstore.Client, capacity int64, ratePerSecond int64) *RedisTokenBucket {
	return &RedisTokenBucket{
		store:    store,
		capacity: capacity,
		rate:     ratePerSecond,
		ttl:      time.Duration(int64(time.Second) * capacity / ratePerSecond * 2),
	}
}

func (tb *RedisTokenBucket) Allow(key string, ctx context.Context) bool {
	rdb := tb.store.RDB()
	redisKey := redisstore.Key("tokenbucket", key)

	now := time.Now()

	vals, err := rdb.HMGet(ctx, redisKey, "tokens", "last_refill").Result()
	if err != nil && err != redis.Nil {
		return false
	}

	var tokens int64
	var lastRefill time.Time

	if vals[0] == nil || vals[1] == nil {
		tokens = tb.capacity - 1
		lastRefill = now
	} else {
		tokens, err = strconv.ParseInt(vals[0].(string), 10, 64)
		if err != nil {
			tokens = tb.capacity
		}
		nanos, err := strconv.ParseInt(vals[1].(string), 10, 64)
		if err != nil {
			lastRefill = now
		} else {
			lastRefill = time.Unix(0, nanos)
		}

		elapsed := now.Sub(lastRefill).Seconds()
		tokens += int64(elapsed) * tb.rate
		if tokens > tb.capacity {
			tokens = tb.capacity
		}

		if tokens < 1 {
			rdb.HSet(ctx, redisKey, "tokens", strconv.FormatInt(tokens, 10), "last_refill", strconv.FormatInt(now.UnixNano(), 10))
			rdb.Expire(ctx, redisKey, tb.ttl)
			return false
		}
		tokens--
	}
	rdb.HSet(ctx, redisKey, "tokens", strconv.FormatInt(tokens, 10), "last_refill", strconv.FormatInt(now.UnixNano(), 10))
	rdb.Expire(ctx, redisKey, tb.ttl)
	return true
}
