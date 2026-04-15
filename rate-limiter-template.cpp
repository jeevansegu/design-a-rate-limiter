// rate_limiter.cpp
// C++17 LLD Template for Distributed Rate Limiter

#include <iostream>
#include <string>
#include <unordered_map>
#include <memory>
#include <vector>

using namespace std;

/* ========================= ENUMS ========================= */

// Supported rate limiting algorithms
enum class AlgorithmType {
    TOKEN_BUCKET,
    LEAKY_BUCKET,
    FIXED_WINDOW,
    SLIDING_WINDOW_LOG,
    SLIDING_WINDOW_COUNTER
};

// Key types for rate limiting
enum class KeyType {
    USER_ID,
    IP,
    ENDPOINT
};

/* ========================= REQUEST CONTEXT ========================= */

class RequestContext {
public:
    string userId;
    string ip;
    string endpoint;
    long timestamp;

    RequestContext(const string& userId,
                   const string& ip,
                   const string& endpoint,
                   long timestamp)
        : userId(userId), ip(ip), endpoint(endpoint), timestamp(timestamp) {}
};

/* ========================= RATE LIMIT RULE ========================= */

class RateLimitRule {
public:
    int limit;
    int windowSize; // in seconds
    KeyType keyType;
    AlgorithmType algorithmType;

    RateLimitRule(int limit,
                  int windowSize,
                  KeyType keyType,
                  AlgorithmType algorithmType)
        : limit(limit),
          windowSize(windowSize),
          keyType(keyType),
          algorithmType(algorithmType) {}
};

/* ========================= RATE LIMIT RESPONSE ========================= */

class RateLimitResponse {
public:
    bool allowed;
    unordered_map<string, string> headers;

    RateLimitResponse(bool allowed)
        : allowed(allowed) {}
};

/* ========================= STORAGE INTERFACE ========================= */

class Storage {
public:
    virtual ~Storage() = default;

    /**
     * Purpose: Retrieve value for a key from storage
     * Input: key (string)
     * Output: value (long)
     */
    virtual long get(const string& key) = 0;

    /**
     * Purpose: Increment value for a key
     * Input: key (string)
     * Output: incremented value (long)
     */
    virtual long increment(const string& key) = 0;

    /**
     * Purpose: Set expiry for a key
     * Input: key (string), ttl in seconds
     * Output: void
     */
    virtual void setExpiry(const string& key, int ttl) = 0;

    /**
     * Purpose: Add timestamp to sorted set (for sliding log)
     * Input: key (string), timestamp (long)
     * Output: void
     */
    virtual void addToSortedSet(const string& key, long timestamp) = 0;

    /**
     * Purpose: Get elements in a time range from sorted set
     * Input: key (string), startTime (long), endTime (long)
     * Output: vector of timestamps
     */
    virtual vector<long> getSortedSetRange(const string& key,
                                           long startTime,
                                           long endTime) = 0;

    /**
     * Purpose: Remove expired entries from sorted set
     * Input: key (string), threshold timestamp
     * Output: void
     */
    virtual void removeExpired(const string& key, long threshold) = 0;
};

/* ========================= REDIS STORAGE (MOCK) ========================= */

class RedisStorage : public Storage {
public:
    /**
     * Purpose: Retrieve value for a key from Redis
     */
    long get(const string& key) override {
        // TODO: Implement Redis GET
        return 0;
    }

    /**
     * Purpose: Increment value for a key in Redis
     */
    long increment(const string& key) override {
        // TODO: Implement Redis INCR
        return 0;
    }

    /**
     * Purpose: Set expiry for a key in Redis
     */
    void setExpiry(const string& key, int ttl) override {
        // TODO: Implement Redis EXPIRE
    }

    /**
     * Purpose: Add timestamp to sorted set
     */
    void addToSortedSet(const string& key, long timestamp) override {
        // TODO: Implement Redis ZADD
    }

    /**
     * Purpose: Get timestamps in range from sorted set
     */
    vector<long> getSortedSetRange(const string& key,
                                   long startTime,
                                   long endTime) override {
        // TODO: Implement Redis ZRANGEBYSCORE
        return {};
    }

    /**
     * Purpose: Remove expired timestamps from sorted set
     */
    void removeExpired(const string& key, long threshold) override {
        // TODO: Implement Redis ZREMRANGEBYSCORE
    }
};

/* ========================= KEY GENERATOR ========================= */

class KeyGenerator {
public:
    /**
     * Purpose: Generate unique key based on rule and request context
     * Input: RequestContext, RateLimitRule
     * Output: unique key string
     */
    static string generateKey(const RequestContext& context,
                              const RateLimitRule& rule) {
        // TODO: Combine userId/IP/endpoint based on rule.keyType
        return "";
    }
};

/* ========================= STRATEGY BASE CLASS ========================= */

class RateLimitStrategy {
public:
    virtual ~RateLimitStrategy() = default;

    /**
     * Purpose: Decide whether request is allowed based on strategy
     * Input: key, rule, context, storage
     * Output: RateLimitResponse
     */
    virtual RateLimitResponse allowRequest(const string& key,
                                           const RateLimitRule& rule,
                                           const RequestContext& context,
                                           shared_ptr<Storage> storage) = 0;
};

/* ========================= STRATEGY IMPLEMENTATIONS ========================= */

class TokenBucketStrategy : public RateLimitStrategy {
public:
    /**
     * Purpose: Apply Token Bucket algorithm
     */
    RateLimitResponse allowRequest(const string& key,
                                   const RateLimitRule& rule,
                                   const RequestContext& context,
                                   shared_ptr<Storage> storage) override {
        // TODO: Implement Token Bucket logic
        return RateLimitResponse(false);
    }
};

class LeakyBucketStrategy : public RateLimitStrategy {
public:
    /**
     * Purpose: Apply Leaky Bucket algorithm
     */
    RateLimitResponse allowRequest(const string& key,
                                   const RateLimitRule& rule,
                                   const RequestContext& context,
                                   shared_ptr<Storage> storage) override {
        // TODO: Implement Leaky Bucket logic
        return RateLimitResponse(false);
    }
};

class FixedWindowStrategy : public RateLimitStrategy {
public:
    /**
     * Purpose: Apply Fixed Window Counter algorithm
     */
    RateLimitResponse allowRequest(const string& key,
                                   const RateLimitRule& rule,
                                   const RequestContext& context,
                                   shared_ptr<Storage> storage) override {
        // TODO: Implement Fixed Window logic
        return RateLimitResponse(false);
    }
};

class SlidingWindowLogStrategy : public RateLimitStrategy {
public:
    /**
     * Purpose: Apply Sliding Window Log algorithm
     */
    RateLimitResponse allowRequest(const string& key,
                                   const RateLimitRule& rule,
                                   const RequestContext& context,
                                   shared_ptr<Storage> storage) override {
        // TODO: Implement Sliding Window Log logic
        return RateLimitResponse(false);
    }
};

class SlidingWindowCounterStrategy : public RateLimitStrategy {
public:
    /**
     * Purpose: Apply Sliding Window Counter algorithm
     */
    RateLimitResponse allowRequest(const string& key,
                                   const RateLimitRule& rule,
                                   const RequestContext& context,
                                   shared_ptr<Storage> storage) override {
        // TODO: Implement Sliding Window Counter logic
        return RateLimitResponse(false);
    }
};

/* ========================= STRATEGY FACTORY ========================= */

class StrategyFactory {
public:
    /**
     * Purpose: Return appropriate strategy based on algorithm type
     * Input: AlgorithmType
     * Output: RateLimitStrategy instance
     */
    static shared_ptr<RateLimitStrategy> getStrategy(AlgorithmType type) {
        // TODO: Return correct strategy instance
        return nullptr;
    }
};

/* ========================= RULE MANAGER ========================= */

class RuleManager {
public:
    /**
     * Purpose: Fetch applicable rate limit rule for a request
     * Input: RequestContext
     * Output: RateLimitRule
     */
    RateLimitRule getRule(const RequestContext& context) {
        // TODO: Load rule from config/DB/cache
        return RateLimitRule(0, 0, KeyType::USER_ID, AlgorithmType::FIXED_WINDOW);
    }
};

/* ========================= RATE LIMITER ========================= */

class RateLimiter {
private:
    shared_ptr<Storage> storage;
    shared_ptr<RuleManager> ruleManager;

public:
    RateLimiter(shared_ptr<Storage> storage,
                shared_ptr<RuleManager> ruleManager)
        : storage(storage), ruleManager(ruleManager) {}

    /**
     * Purpose: Entry point to check if request should be allowed
     * Input: RequestContext
     * Output: RateLimitResponse
     */
    RateLimitResponse allowRequest(const RequestContext& context) {
        // TODO:
        // 1. Fetch rule
        // 2. Generate key
        // 3. Get strategy
        // 4. Execute allowRequest
        return RateLimitResponse(false);
    }
};

/* ========================= OPTIONAL MIDDLEWARE ========================= */

class RateLimiterMiddleware {
private:
    shared_ptr<RateLimiter> rateLimiter;

public:
    RateLimiterMiddleware(shared_ptr<RateLimiter> rateLimiter)
        : rateLimiter(rateLimiter) {}

    /**
     * Purpose: Middleware wrapper for API requests
     * Input: RequestContext
     * Output: RateLimitResponse
     */
    RateLimitResponse handle(const RequestContext& context) {
        // TODO: Call rateLimiter and attach headers
        return RateLimitResponse(false);
    }
};

/* ========================= MAIN (OPTIONAL TEST ENTRY) ========================= */

int main() {
    // TODO: Initialize components and test flow
    return 0;
}