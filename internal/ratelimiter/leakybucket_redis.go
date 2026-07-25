package ratelimiter

import (
	"context"
	"strconv"
	"time"

	"github.com/jeevansegu/design-a-rate-limiter/internal/redisstore"
	"github.com/redis/go-redis/v9"
)

type RedisLeakyBucket struct {
	store    *redisstore.Client
	capacity int64
	leakRate int64
	ttl      time.Duration
}

func NewRedisLeakyBucket(store *redisstore.Client, capacity int64, leakRatePerSecond int64) *RedisLeakyBucket {
	return &RedisLeakyBucket{
		store:    store,
		capacity: capacity,
		leakRate: leakRatePerSecond,
		ttl:      time.Duration(int64(time.Second) * capacity / leakRatePerSecond * 2),
	}
}

func (lb *RedisLeakyBucket) Allow(key string, ctx context.Context) bool {
	rdb := lb.store.RDB()
	redisKey := redisstore.Key("leakybucket", key)

	now := time.Now()

	vals, err := rdb.HMGet(ctx, redisKey, "queue", "last_leak").Result()
	if err != nil && err != redis.Nil {
		return false
	}

	var queue int64
	var lastLeak time.Time

	if vals[0] == nil || vals[1] == nil {
		queue = 1
		lastLeak = now
	} else {
		queue, err = strconv.ParseInt(vals[0].(string), 10, 64)
		if err != nil {
			queue = 0
		}
		nanos, err := strconv.ParseInt(vals[1].(string), 10, 64)
		if err != nil {
			lastLeak = now
		} else {
			lastLeak = time.Unix(0, nanos)
		}

		elapsed := now.Sub(lastLeak).Seconds()
		queue -= int64(elapsed) * lb.leakRate
		if queue < 0 {
			queue = 0
		}

		if queue >= lb.capacity {
			rdb.HSet(ctx, redisKey, "queue", strconv.FormatInt(queue, 10), "last_leak", strconv.FormatInt(now.UnixNano(), 10))
			rdb.Expire(ctx, redisKey, lb.ttl)
			return false
		}
		queue++
	}
	rdb.HSet(ctx, redisKey, "queue", strconv.FormatInt(queue, 10), "last_leak", strconv.FormatInt(now.UnixNano(), 10))
	rdb.Expire(ctx, redisKey, lb.ttl)
	return true
}
