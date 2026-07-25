package ratelimiter

import (
	"context"
	"time"

	"github.com/jeevansegu/design-a-rate-limiter/internal/redisstore"
	"github.com/redis/go-redis/v9"
)

type RedisFixedWindow struct {
	store  *redisstore.Client
	limit  int64
	window time.Duration
}

func NewRedisFixedWindow(store *redisstore.Client, limit int64, window time.Duration) *RedisFixedWindow {
	return &RedisFixedWindow{
		store:  store,
		limit:  limit,
		window: window,
	}
}

func (fw *RedisFixedWindow) Allow(key string, ctx context.Context) bool {
	rdb := fw.store.RDB()
	redisKey := redisstore.Key("fixedwindow", key)

	count, err := rdb.Incr(ctx, redisKey).Result()
	if err != nil && err != redis.Nil {
		return false
	}

	if count == 1 {
		if err := rdb.Expire(ctx, redisKey, fw.window).Err(); err != nil {
			return false
		}
	}

	if count > fw.limit {
		return false
	}
	return true
}
