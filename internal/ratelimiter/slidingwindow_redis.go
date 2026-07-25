package ratelimiter

import (
	"context"
	"strconv"
	"time"

	"github.com/jeevansegu/design-a-rate-limiter/internal/redisstore"
	"github.com/redis/go-redis/v9"
)

type RedisSlidingWindow struct {
	store  *redisstore.Client
	limit  int64
	window time.Duration
}

func NewRedisSlidingWindow(store *redisstore.Client, limit int64, window time.Duration) *RedisSlidingWindow {
	return &RedisSlidingWindow{
		store:  store,
		limit:  limit,
		window: window,
	}
}

func (sw *RedisSlidingWindow) Allow(key string, ctx context.Context) bool {
	rdb := sw.store.RDB()
	redisKey := redisstore.Key("slidingwindow", key)

	now := time.Now()
	windowStart := now.Add(-sw.window).UnixNano()

	var count *redis.IntCmd

	_, err := rdb.TxPipelined(ctx, func(p redis.Pipeliner) error {
		p.ZRemRangeByScore(ctx, redisKey, "0", strconv.FormatInt(windowStart, 10))
		count = p.ZCard(ctx, redisKey)
		return nil
	})
	if err != nil {
		return false
	}

	if count.Val() >= sw.limit {
		return false
	}

	_, err = rdb.TxPipelined(ctx, func(p redis.Pipeliner) error {
		p.ZAdd(ctx, redisKey, redis.Z{
			Score:  float64(now.UnixNano()),
			Member: strconv.FormatInt(now.UnixNano(), 10),
		})

		p.Expire(ctx, redisKey, sw.window)
		return nil
	})

	if err != nil {
		return false
	}
	return true
}
