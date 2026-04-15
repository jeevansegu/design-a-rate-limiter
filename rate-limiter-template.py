from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
import time


# =========================
# Constants
# =========================

class StrategyType:
    """Supported rate limiting strategies."""
    TOKEN_BUCKET = "TOKEN_BUCKET"
    LEAKY_BUCKET = "LEAKY_BUCKET"
    FIXED_WINDOW = "FIXED_WINDOW"
    SLIDING_WINDOW_LOG = "SLIDING_WINDOW_LOG"
    SLIDING_WINDOW_COUNTER = "SLIDING_WINDOW_COUNTER"


class KeyType:
    """Supported key dimensions for rate limiting."""
    USER = "user_id"
    IP = "ip"
    ENDPOINT = "endpoint"


# =========================
# Request Context
# =========================

class RequestContext:
    """
    Represents metadata of an incoming request.

    This object is passed through the rate limiter pipeline.
    """

    def __init__(
        self,
        user_id: Optional[str],
        ip: str,
        endpoint: str,
        timestamp: Optional[float] = None
    ):
        """
        Initialize request context.

        Args:
            user_id: Unique user identifier (can be None for anonymous users)
            ip: Client IP address
            endpoint: API endpoint path
            timestamp: Request time (defaults to current time)
        """
        self.user_id = user_id
        self.ip = ip
        self.endpoint = endpoint
        self.timestamp = timestamp or time.time()


# =========================
# Rate Limit Rule
# =========================

class RateLimitRule:
    """
    Defines how rate limiting should be applied.
    """

    def __init__(
        self,
        limit: int,
        window: int,
        key_type: str,
        strategy_type: str
    ):
        """
        Args:
            limit: Maximum allowed requests
            window: Time window in seconds
            key_type: Dimension used for limiting (user/ip/endpoint)
            strategy_type: Algorithm to apply
        """
        self.limit = limit
        self.window = window
        self.key_type = key_type
        self.strategy_type = strategy_type


# =========================
# Response
# =========================

class RateLimitResponse:
    """
    Standard response from rate limiter.
    """

    def __init__(self, allowed: bool, headers: Dict[str, Any]):
        """
        Args:
            allowed: Whether request is allowed
            headers: Metadata such as:
                - X-RateLimit-Limit
                - X-RateLimit-Remaining
                - X-RateLimit-Reset
        """
        self.allowed = allowed
        self.headers = headers


# =========================
# Storage Interface
# =========================

class Storage(ABC):
    """
    Abstract storage layer (Redis, in-memory, etc.)

    All operations should be atomic in production systems.
    """

    @abstractmethod
    def get(self, key: str) -> Any:
        """
        Retrieve value stored at key.

        Used by:
            - Token bucket (tokens, last refill time)
            - Fixed window (counter)
            - Sliding window counter

        Returns:
            Stored value or None if not present
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Store value at key.

        Used to:
            - Initialize counters
            - Store bucket state

        Should overwrite existing value.
        """
        pass

    @abstractmethod
    def increment(self, key: str, amount: int = 1) -> int:
        """
        Atomically increment a numeric counter.

        Used by:
            - Fixed window counter
            - Sliding window counter

        Returns:
            Updated counter value
        """
        pass

    @abstractmethod
    def set_expiry(self, key: str, ttl: int) -> None:
        """
        Set expiration time (TTL) for a key.

        Used to:
            - Auto-clean fixed window counters
            - Avoid memory leaks

        Args:
            ttl: Time to live in seconds
        """
        pass

    @abstractmethod
    def add_to_sorted_set(self, key: str, score: float, value: Any) -> None:
        """
        Add an entry to a sorted set.

        Used by:
            Sliding Window Log strategy

        Args:
            score: Typically timestamp
            value: Unique request identifier
        """
        pass

    @abstractmethod
    def get_sorted_range(self, key: str, start: float, end: float) -> List[Any]:
        """
        Fetch entries in sorted set within score range.

        Used to:
            Count requests within sliding window

        Args:
            start: Start timestamp
            end: End timestamp

        Returns:
            List of entries in range
        """
        pass

    @abstractmethod
    def remove_expired(self, key: str, threshold: float) -> None:
        """
        Remove entries older than threshold.

        Used to:
            Clean sliding window logs

        Args:
            threshold: Oldest allowed timestamp
        """
        pass


# =========================
# Redis Mock
# =========================

class RedisStorage(Storage):
    """
    Mock Redis implementation using in-memory dictionary.

    Replace with actual Redis client in production.
    """

    def __init__(self):
        """Initialize in-memory store."""
        self.store = {}

    def get(self, key: str) -> Any:
        """Fetch value for key from store."""
        pass

    def set(self, key: str, value: Any) -> None:
        """Store value in dictionary."""
        pass

    def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment integer value stored at key.

        Initialize to 0 if key does not exist.
        """
        pass

    def set_expiry(self, key: str, ttl: int) -> None:
        """
        Simulate TTL behavior.

        In real Redis:
            EXPIRE command is used.
        """
        pass

    def add_to_sorted_set(self, key: str, score: float, value: Any) -> None:
        """
        Store (score, value) pair.

        In real Redis:
            ZADD command is used.
        """
        pass

    def get_sorted_range(self, key: str, start: float, end: float) -> List[Any]:
        """
        Return values whose scores fall in [start, end].
        """
        pass

    def remove_expired(self, key: str, threshold: float) -> None:
        """
        Remove entries older than threshold.

        In Redis:
            ZREMRANGEBYSCORE
        """
        pass


# =========================
# Strategy Base
# =========================

class RateLimitStrategy(ABC):
    """
    Base class for all rate limiting algorithms.
    """

    def __init__(self, storage: Storage):
        """
        Args:
            storage: Backend storage (Redis, etc.)
        """
        self.storage = storage

    @abstractmethod
    def allow_request(self, key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
        """
        Core decision-making function.

        Responsibilities:
            1. Read current state from storage
            2. Update state based on algorithm
            3. Decide allow or deny
            4. Compute response headers

        Must return:
            RateLimitResponse
        """
        pass


# =========================
# Strategies
# =========================

class TokenBucketStrategy(RateLimitStrategy):
    """
    Token Bucket Algorithm.

    Logic to implement:
        - Maintain tokens and last refill time
        - Refill tokens based on elapsed time
        - Consume token per request
        - Deny if no tokens left
    """

    def allow_request(self, key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
        pass


class LeakyBucketStrategy(RateLimitStrategy):
    """
    Leaky Bucket Algorithm.

    Logic to implement:
        - Maintain queue size / water level
        - Drain at constant rate
        - Add request if capacity allows
    """

    def allow_request(self, key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
        pass


class FixedWindowStrategy(RateLimitStrategy):
    """
    Fixed Window Counter.

    Logic:
        - Increment counter per window
        - Reset after window expires
    """

    def allow_request(self, key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
        pass


class SlidingWindowLogStrategy(RateLimitStrategy):
    """
    Sliding Window Log.

    Logic:
        - Store timestamps of each request
        - Remove expired entries
        - Count active requests
    """

    def allow_request(self, key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
        pass


class SlidingWindowCounterStrategy(RateLimitStrategy):
    """
    Sliding Window Counter.

    Logic:
        - Maintain current + previous window counters
        - Weight previous window contribution
    """

    def allow_request(self, key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
        pass


# =========================
# Factory
# =========================

class StrategyFactory:
    """
    Creates strategy instances.
    """

    def __init__(self, storage: Storage):
        self.storage = storage

    def get_strategy(self, strategy_type: str) -> RateLimitStrategy:
        """
        Map strategy type to class.

        Raise error if unsupported strategy.
        """
        if strategy_type == StrategyType.TOKEN_BUCKET:
            return TokenBucketStrategy(self.storage)
        elif strategy_type == StrategyType.LEAKY_BUCKET:
            return LeakyBucketStrategy(self.storage)
        elif strategy_type == StrategyType.FIXED_WINDOW:
            return FixedWindowStrategy(self.storage)
        elif strategy_type == StrategyType.SLIDING_WINDOW_LOG:
            return SlidingWindowLogStrategy(self.storage)
        elif strategy_type == StrategyType.SLIDING_WINDOW_COUNTER:
            return SlidingWindowCounterStrategy(self.storage)

        raise ValueError("Invalid strategy type")


# =========================
# Key Generator
# =========================

class KeyGenerator:
    """
    Responsible for generating unique keys for rate limiting.
    """

    def generate_key(self, context: RequestContext, rule: RateLimitRule) -> str:
        """
        Build key based on key_type.

        Examples:
            user -> rate_limit:user:123:/endpoint
            ip   -> rate_limit:ip:1.1.1.1:/endpoint

        Must ensure:
            - uniqueness
            - consistency
        """
        pass


# =========================
# Rule Manager
# =========================

class RuleManager:
    """
    Provides rate limit rules.

    Can be extended to:
        - DB
        - config service
        - feature flags
    """

    def get_rule(self, context: RequestContext) -> RateLimitRule:
        """
        Return rule based on request.

        Can use:
            - endpoint
            - user tier
            - IP

        For now, return default rule.
        """
        return RateLimitRule(
            limit=10,
            window=60,
            key_type=KeyType.USER,
            strategy_type=StrategyType.FIXED_WINDOW
        )


# =========================
# Rate Limiter
# =========================

class RateLimiter:
    """
    Orchestrates the full rate limiting flow.
    """

    def __init__(
        self,
        storage: Storage,
        rule_manager: RuleManager,
        key_generator: KeyGenerator,
        strategy_factory: StrategyFactory
    ):
        self.storage = storage
        self.rule_manager = rule_manager
        self.key_generator = key_generator
        self.strategy_factory = strategy_factory

    def allow_request(self, context: RequestContext) -> RateLimitResponse:
        """
        Steps:
            1. Fetch rule
            2. Generate key
            3. Get strategy
            4. Execute algorithm
        """
        rule = self.rule_manager.get_rule(context)
        key = self.key_generator.generate_key(context, rule)
        strategy = self.strategy_factory.get_strategy(rule.strategy_type)
        return strategy.allow_request(key, rule, context.timestamp)


# =========================
# Middleware
# =========================

class RateLimiterMiddleware:
    """
    Wrapper for integrating into frameworks.
    """

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter

    def handle(self, context: RequestContext) -> RateLimitResponse:
        """
        Call before processing request.

        If denied:
            - return error response (429)
        """
        return self.rate_limiter.allow_request(context)


# =========================
# MAIN
# =========================

def main():
    """
    Entry point for testing.

    Once implementations are added,
    this simulates a real request.
    """

    storage = RedisStorage()
    rule_manager = RuleManager()
    key_generator = KeyGenerator()
    strategy_factory = StrategyFactory(storage)

    rate_limiter = RateLimiter(
        storage,
        rule_manager,
        key_generator,
        strategy_factory
    )

    context = RequestContext(
        user_id="123",
        ip="192.168.1.1",
        endpoint="/api/test"
    )

    response = rate_limiter.allow_request(context)

    print("Allowed:", response.allowed)
    print("Headers:", response.headers)


if __name__ == "__main__":
    main()