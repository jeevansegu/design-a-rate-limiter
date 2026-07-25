# Design a Distributed Rate Limiter

A distributed rate limiter implemented in **Go** using **Redis** as the centralized state store.

This project demonstrates the implementation of four commonly used rate limiting algorithms using clean Low-Level Design (LLD) principles, interface-based architecture, and Redis data structures. Every algorithm implements the same interface, allowing the rate limiting strategy to be changed without modifying the middleware or application logic.

---

# Features

* Distributed rate limiting using Redis
* Four rate limiting algorithms
* Interface-based architecture
* HTTP middleware integration
* Automatic Redis key cleanup using TTL
* Modular and extensible project structure

---

# Implemented Algorithms

| Algorithm      | Redis Data Structure | Redis Commands                                |
| -------------- | -------------------- | --------------------------------------------- |
| Token Bucket   | Hash                 | `HMGET`, `HSET`, `EXPIRE`                     |
| Fixed Window   | String               | `INCR`, `EXPIRE`                              |
| Sliding Window | Sorted Set           | `ZREMRANGEBYSCORE`, `ZCARD`, `ZADD`, `EXPIRE` |
| Leaky Bucket   | Hash                 | `HMGET`, `HSET`, `EXPIRE`                     |

---

# Project Structure

```text
design-a-rate-limiter/

├── cmd/
│   └── server/
│       └── main.go
│
├── internal/
│   ├── handlers/
│   │   └── handler.go
│   │
│   ├── middleware/
│   │   └── middleware.go
│   │
│   ├── ratelimiter/
│   │   ├── interface.go
│   │   ├── token_bucket.go
│   │   ├── fixed_window.go
│   │   ├── sliding_window.go
│   │   └── leaky_bucket.go
│   │
│   ├── redisstore/
│   │   └── redis.go
│   │
│   └── server/
│       └── server.go
│
├── docker-compose.yml
├── go.mod
├── go.sum
└── README.md
```

---

# Low Level Design (UML)

## Overall Architecture

```text
                         +----------------------+
                         |      HTTP Client     |
                         +----------+-----------+
                                    |
                                    |
                                    v
                         +----------------------+
                         | RateLimit Middleware |
                         +----------+-----------+
                                    |
                                    |
                                    v
                    +-------------------------------+
                    |        RateLimiter            |
                    |-------------------------------|
                    | + Allow(key string) : bool    |
                    +---------------^---------------+
                                    |
      -------------------------------------------------------------------------
      |                     |                    |                            |
      |                     |                    |                            |
      |                     |                    |                            |
+----------------+   +----------------+   +----------------+         +----------------+
| Token Bucket   |   | Fixed Window   |   | Sliding Window |         | Leaky Bucket   |
+----------------+   +----------------+   +----------------+         +----------------+
| store          |   | store          |   | store          |         | store          |
| capacity       |   | limit          |   | limit          |         | capacity       |
| refillRate     |   | window         |   | window         |         | leakRate       |
| ttl            |   +----------------+   +----------------+         | ttl            |
+----------------+                                              +----------------+
          \                    |                    |                     /
           \                   |                    |                    /
            \__________________|____________________|___________________/
                               |
                               |
                               v
                     +----------------------+
                     |     Redis Store      |
                     +----------+-----------+
                                |
                                |
                                v
                         +---------------+
                         |     Redis     |
                         +---------------+
```

---

## Token Bucket

```text
+------------------------------------------------------+
|                 RedisTokenBucket                     |
+------------------------------------------------------+
| - store       : *redisstore.Client                   |
| - capacity    : int64                                |
| - refillRate  : int64                                |
| - ttl         : time.Duration                        |
+------------------------------------------------------+
| + Allow(key string, ctx context.Context) : bool      |
+------------------------------------------------------+
```

---

## Fixed Window

```text
+------------------------------------------------------+
|                RedisFixedWindow                      |
+------------------------------------------------------+
| - store      : *redisstore.Client                    |
| - limit      : int                                   |
| - window     : time.Duration                         |
+------------------------------------------------------+
| + Allow(key string, ctx context.Context) : bool      |
+------------------------------------------------------+
```

---

## Sliding Window

```text
+------------------------------------------------------+
|               RedisSlidingWindow                     |
+------------------------------------------------------+
| - store      : *redisstore.Client                    |
| - limit      : int                                   |
| - window     : time.Duration                         |
+------------------------------------------------------+
| + Allow(key string, ctx context.Context) : bool      |
+------------------------------------------------------+
```

---

## Leaky Bucket

```text
+------------------------------------------------------+
|                RedisLeakyBucket                      |
+------------------------------------------------------+
| - store      : *redisstore.Client                    |
| - capacity   : int64                                 |
| - leakRate   : int64                                 |
| - ttl        : time.Duration                         |
+------------------------------------------------------+
| + Allow(key string, ctx context.Context) : bool      |
+------------------------------------------------------+
```

---

# Redis Data Models

## Token Bucket

**Redis Hash**

```text
tokens
last_refill
```

---

## Fixed Window

**Redis String**

```text
request_count
```

---

## Sliding Window

**Redis Sorted Set**

```text
Score  → Unix Timestamp

Member → Unique Request Timestamp
```

---

## Leaky Bucket

**Redis Hash**

```text
queue
last_leak
```

---

# Running the Project

### Start Redis

```bash
docker compose up -d
```

---

### Run the Application

```bash
go run ./cmd/server
```

The server starts on:

```
http://localhost:8080
```

---

# Inspecting Redis

### List all keys

```bash
KEYS ratelimiter:*
```

---

### Token Bucket

```bash
HGETALL ratelimiter:tokenbucket:<clientID>
```

---

### Fixed Window

```bash
GET ratelimiter:fixedwindow:<clientID>

TTL ratelimiter:fixedwindow:<clientID>
```

---

### Sliding Window

```bash
ZRANGE ratelimiter:slidingwindow:<clientID> 0 -1 WITHSCORES

ZCARD ratelimiter:slidingwindow:<clientID>

TTL ratelimiter:slidingwindow:<clientID>
```

---

### Leaky Bucket

```bash
HGETALL ratelimiter:leakybucket:<clientID>
```

---

# Technologies Used

* Go
* Redis
* go-redis/v9
* net/http

---

# Concepts Demonstrated

* Low-Level Design (LLD)
* Strategy Pattern
* Interface-based Design
* Dependency Injection
* Composition in Go
* HTTP Middleware
* Distributed Rate Limiting
* Redis Data Structures
* Redis-backed Distributed State Management
