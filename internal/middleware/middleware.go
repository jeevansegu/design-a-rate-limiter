package middleware

import (
	"encoding/json"
	"log"
	"net/http"
	"strings"

	"github.com/jeevansegu/design-a-rate-limiter/internal/ratelimiter"
)

func MainMiddleware(limiter ratelimiter.RateLimiter, next http.Handler) http.Handler {
	return loggerMiddleware(rateLimiterMiddleware(limiter, next))
}

func rateLimiterMiddleware(limiter ratelimiter.RateLimiter, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		key := clientKey(r)
		if !limiter.Allow(key, r.Context()) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusTooManyRequests)
			json.NewEncoder(w).Encode(map[string]string{
				"error": "rate limit exceeded",
			})
			return
		}
		next.ServeHTTP(w, r)
	})
}

func loggerMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		log.Printf("Incoming request: %s %s %s", r.Method, r.URL.Path, r.Header.Get("X-Requested-With"))
		next.ServeHTTP(w, r)
	})
}

func clientKey(r *http.Request) string {
	if xrw := r.Header.Get("X-Requested-With"); xrw != "" {
		return strings.TrimSpace(strings.Split(xrw, ",")[0])
	}
	ip := r.RemoteAddr
	if idx := strings.LastIndex(ip, ":"); idx != -1 {
		ip = ip[:idx]
	}
	return ip
}
