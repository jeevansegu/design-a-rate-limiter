package redisstore

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/joho/godotenv"
	"github.com/redis/go-redis/v9"
)

type Client struct {
	rdb *redis.Client
}

func New() *Client {
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found, falling back to environment variables")
	}

	pass := os.Getenv("REDIS_PASS")

	rdb := redis.NewClient(&redis.Options{
		Addr:     "localhost:6379",
		Password: pass,
		DB:       0,
	})

	if err := rdb.Ping(context.Background()).Err(); err != nil {
		log.Fatalf("Failed to connect to RedisL %v", err)
	}

	log.Println("Connected to Redis")
	return &Client{rdb: rdb}
}

func (c *Client) RDB() *redis.Client {
	return c.rdb
}

func Key(strategy, clientID string) string {
	return fmt.Sprintf("ratelimiter:%s:%s", strategy, clientID)
}
