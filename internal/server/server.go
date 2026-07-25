package server

import (
	"net/http"

	"github.com/jeevansegu/design-a-rate-limiter/internal/handlers"
	"github.com/jeevansegu/design-a-rate-limiter/internal/middleware"
	"github.com/jeevansegu/design-a-rate-limiter/internal/ratelimiter"
	"github.com/jeevansegu/design-a-rate-limiter/internal/redisstore"
)

func NewServer(addr string) *http.Server {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", handlers.HealthHandler)

	store := redisstore.New()

	limiter := ratelimiter.NewRedisLeakyBucket(store, 10, 1)
	return &http.Server{
		Addr:    addr,
		Handler: middleware.MainMiddleware(limiter, mux),
	}
}
