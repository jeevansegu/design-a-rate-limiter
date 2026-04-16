from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
import time


class StrategyType:
    TOKEN_BUCKET = "TOKEN_BUCKET"
    LEAKY_BUCKET = "LEAKY_BUCKET"
    FIXED_WINDOW = "FIXED_WINDOW"
    SLIDING_WINDOW_LOG = "SLIDING_WINDOW_LOG"
    SLIDING_WINDOW_COUNTER = "SLIDING_WINDOW_COUNTER"


class KeyType:
    USER = "user_id"
    IP = "ip"
    ENDPOINT = "endpoint"


class RequestContext:
    def __init__(self, user_id: Optional[str], ip: str, endpoint: str, timestamp: Optional[float] = None):
        self.user_id = user_id
        self.ip = ip
        self.endpoint = endpoint
        self.timestamp = timestamp or time.time()


class RateLimitRule:
    def __init__(self, limit: int, window: int, key_type: str, strategy_type: str):
        self.limit = limit
        self.window = window
        self.key_type = key_type
        self.strategy_type = strategy_type


class RateLimitResponse:
    def __init__(self, allowed: bool, headers: Dict[str, Any]):
        self.allowed = allowed
        self.headers = headers


class Storage(ABC):
    @abstractmethod
    def get(self, key: str) -> Any:
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    def increment(self, key: str, amount: int = 1) -> int:
        pass

    @abstractmethod
    def set_expiry(self, key: str, ttl: int) -> None:
        pass

    @abstractmethod
    def add_to_sorted_set(self, key: str, score: float, value: Any) -> None:
        pass

    @abstractmethod
    def get_sorted_range(self, key: str, start: float, end: float) -> List[Any]:
        pass

    @abstractmethod
    def remove_expired(self, key: str, threshold: float) -> None:
        pass


class RedisStorage(Storage):
    def __init__(self):
        self.store = {}
        self.expiry = {}
        self.sorted_sets = {}

    def _is_expired(self, key: str) -> bool:
        if key in self.expiry:
            if time.time() > self.expiry[key]:
                self.store.pop(key, None)
                self.expiry.pop(key, None)
                self.sorted_sets.pop(key, None)
                return True
        return False

    def get(self, key: str) -> Any:
        if self._is_expired(key):
            return None
        return self.store.get(key, None)

    def set(self, key: str, value: Any) -> None:
        self._is_expired(key)
        self.store[key] = value

    def increment(self, key: str, amount: int = 1) -> int:
        if self._is_expired(key):
            self.store.pop(key, None)
        value = self.store.get(key, 0)
        if not isinstance(value, int):
            raise ValueError("Value is not an integer")
        value += amount
        self.store[key] = value
        return value

    def set_expiry(self, key: str, ttl: int) -> None:
        self.expiry[key] = time.time() + ttl

    def add_to_sorted_set(self, key: str, score: float, value: Any) -> None:
        self._is_expired(key)
        if key not in self.sorted_sets:
            self.sorted_sets[key] = []
        self.sorted_sets[key].append((score, value))
        self.sorted_sets[key].sort(key=lambda x: x[0])

    def get_sorted_range(self, key: str, start: float, end: float) -> List[Any]:
        if self._is_expired(key):
            return []
        if key not in self.sorted_sets:
            return []
        return [
            value
            for score, value in self.sorted_sets[key]
            if start <= score <= end
        ]

    def remove_expired(self, key: str, threshold: float) -> None:
        if self._is_expired(key):
            return
        if key not in self.sorted_sets:
            return
        self.sorted_sets[key] = [
            (score, value)
            for score, value in self.sorted_sets[key]
            if score >= threshold
        ]


class RateLimitStrategy(ABC):
    def __init__(self, storage: Storage):
        self.storage = storage

    @abstractmethod
    def allow_request(self, key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
        pass


class TokenBucketStrategy(RateLimitStrategy):
    def allow_request(self, key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
        bucket = self.storage.get(key)
        if bucket is None:
            bucket = {
                "tokens": rule.limit,
                "last_refill": current_time
            }
        tokens = bucket["tokens"]
        last_refill = bucket["last_refill"]

        refill_rate = rule.limit / rule.window
        elapsed_time = current_time - last_refill

        tokens += elapsed_time * refill_rate
        tokens = min(tokens, rule.limit)

        if tokens >= 1:
            allowed = True
            tokens -= 1
        else:
            allowed = False

        updated_bucket = {
            "tokens": tokens,
            "last_refill": current_time
        }

        self.storage.set(key, updated_bucket)
        self.storage.set_expiry(key, rule.window*2)
        remaining = int(tokens)
        if tokens < 1:
            retry_after = (1 - tokens) / refill_rate
        else:
            retry_after = 0

        headers = {
            "X-RateLimit-Limit": rule.limit,
            "X-RateLimit-Remaining": max(0, remaining),
            "X-RateLimit-Retry-After": round(retry_after, 2)
        }

        return RateLimitResponse(allowed=allowed, headers=headers)


class LeakyBucketStrategy(RateLimitStrategy):
    def allow_request(self, key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
        bucket = self.storage.get(key)
        if bucket is None:
            bucket = {
                "requests": 0.0,
                "last_updated_time": current_time
            }
        requests = bucket["requests"]
        last_updated_time = bucket["last_updated_time"]

        leak_rate = rule.limit / rule.window
        elapsed_time = current_time - last_updated_time

        leaked = elapsed_time * leak_rate
        requests = max(requests-leaked, 0)

        if requests < rule.limit:
            allowed = True
            requests += 1
        else:
            allowed = False

        updated_bucket = {
            "requests": requests,
            "last_updated_time": current_time
        }

        self.storage.set(key, updated_bucket)
        self.storage.set_expiry(key, rule.window * 2)

        if not allowed:
            excess = requests - rule.limit + 1
            retry_after = excess / leak_rate
        else:
            retry_after = 0

        remaining = rule.limit - int(requests)
        headers = {
            "X-RateLimit-Limit": rule.limit,
            "X-RateLimit-Remaining": max(0, int(remaining)),
            "X-RateLimit-Retry-After": round(retry_after, 2)
        }

        return RateLimitResponse(allowed=allowed, headers=headers)


class FixedWindowStrategy(RateLimitStrategy):
    def allow_request(self, key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
        bucket = self.storage.get(key)
        if bucket is None:
            bucket = {
                "count": 0,
                "window_start": current_time
            }
        count = bucket["count"]
        window_start = bucket["window_start"]

        if current_time - window_start >= rule.window:
            count = 0
            window_start = current_time

        if count < rule.limit:
            allowed = True
            count += 1
        else:
            allowed = False

        updated_bucket = {
            "count": count,
            "window_start": window_start
        }

        self.storage.set(key, updated_bucket)
        self.storage.set_expiry(key, rule.window * 2)

        if not allowed:
            retry_after = rule.window - (current_time - window_start)
        else:
            retry_after = 0

        remaining = max(0, rule.limit - count)

        headers = {
            "X-RateLimit-Limit": rule.limit,
            "X-RateLimit-Remaining": remaining,
            "X-RateLimit-Retry-After": round(retry_after, 2)
        }

        return RateLimitResponse(allowed=allowed, headers=headers)


class SlidingWindowLogStrategy(RateLimitStrategy):
    def allow_request(self, key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
        window_start = current_time - rule.window
        self.storage.remove_expired(key, window_start)

        timestamps = self.storage.get_sorted_range(
            key,
            window_start,
            current_time
        )

        current_count = len(timestamps)

        if current_count < rule.limit:
            allowed = True
            self.storage.add_to_sorted_set(key, current_time, current_time)
            current_count += 1
        else:
            allowed = False

        self.storage.set_expiry(key, rule.window * 2)

        if not allowed and timestamps:
            oldest = timestamps[0]
            retry_after = rule.window - (current_time - oldest)
        else:
            retry_after = 0

        remaining = max(0, rule.limit - current_count)

        headers = {
            "X-RateLimit-Limit": rule.limit,
            "X-RateLimit-Remaining": remaining,
            "X-RateLimit-Retry-After": round(retry_after, 2)
        }

        return RateLimitResponse(allowed=allowed, headers=headers)


class SlidingWindowCounterStrategy(RateLimitStrategy):
    def allow_request(self, key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
        bucket = self.storage.get(key)
        if bucket is None:
            bucket = {
                "current_count": 0,
                "previous_count": 0,
                "current_window_start": current_time
            }

        current_count = bucket["current_count"]
        previous_count = bucket["previous_count"]
        current_window_start = bucket["current_window_start"]

        if current_time - current_window_start >= rule.window:
            previous_count = current_count
            current_count = 0
            current_window_start = current_time

        elapsed = current_time - current_window_start
        weight = elapsed / rule.window

        effective_count = current_count + (previous_count * (1 - weight))

        if effective_count < rule.limit:
            allowed = True
            current_count += 1
            effective_count += 1
        else:
            allowed = False

        updated_bucket = {
            "current_count": current_count,
            "previous_count": previous_count,
            "current_window_start": current_window_start
        }

        self.storage.set(key, updated_bucket)
        self.storage.set_expiry(key, rule.window * 2)

        if not allowed:
            retry_after = rule.window - elapsed
        else:
            retry_after = 0

        remaining = max(0, int(rule.limit - effective_count))

        headers = {
            "X-RateLimit-Limit": rule.limit,
            "X-RateLimit-Remaining": remaining,
            "X-RateLimit-Retry-After": round(retry_after, 2)
        }

        return RateLimitResponse(allowed=allowed, headers=headers)


class StrategyFactory:
    def __init__(self, storage: Storage):
        self.storage = storage

    def get_strategy(self, strategy_type: str) -> RateLimitStrategy:
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


class KeyGenerator:
    def generate_key(self, context: RequestContext, rule: RateLimitRule) -> str:
        if rule.key_type == KeyType.USER:
            identifier = context.user_id or "anonymous"

        elif rule.key_type == KeyType.IP:
            identifier = context.ip

        elif rule.key_type == KeyType.ENDPOINT:
            identifier = context.endpoint

        else:
            raise ValueError("Invalid key type")

        key = f"rate_limit:{rule.key_type}:{identifier}:{context.endpoint}"

        return key


class RuleManager:
    def get_rule(self, context: RequestContext) -> RateLimitRule:
        return RateLimitRule(
            limit=10,
            window=60,
            key_type=KeyType.USER,
            strategy_type=StrategyType.FIXED_WINDOW
        )


class RateLimiter:
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
        rule = self.rule_manager.get_rule(context)
        key = self.key_generator.generate_key(context, rule)
        strategy = self.strategy_factory.get_strategy(rule.strategy_type)
        return strategy.allow_request(key, rule, context.timestamp)


class RateLimiterMiddleware:
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter

    def handle(self, context: RequestContext) -> RateLimitResponse:
        return self.rate_limiter.allow_request(context)


def print_rule(rule: RateLimitRule):
    print("Rule Config:")
    print(f"  Limit       : {rule.limit}")
    print(f"  Window      : {rule.window}s")
    print(f"  Key Type    : {rule.key_type}")
    print(f"  Strategy    : {rule.strategy_type}")


def test_all_strategies():
    strategies = [
        StrategyType.TOKEN_BUCKET,
        StrategyType.LEAKY_BUCKET,
        StrategyType.FIXED_WINDOW,
        StrategyType.SLIDING_WINDOW_LOG,
        StrategyType.SLIDING_WINDOW_COUNTER
    ]

    for strat in strategies:
        print(f"\n==============================")
        print(f"Testing Strategy: {strat}")
        print(f"==============================")

        storage = RedisStorage()
        key_generator = KeyGenerator()
        strategy_factory = StrategyFactory(storage)

        class CustomRuleManager(RuleManager):
            def get_rule(self, context):
                return RateLimitRule(
                    limit=5,
                    window=10,
                    key_type=KeyType.USER,
                    strategy_type=strat
                )

        rule_manager = CustomRuleManager()

        rate_limiter = RateLimiter(
            storage,
            rule_manager,
            key_generator,
            strategy_factory
        )

        context = RequestContext(
            user_id="user_1",
            ip="192.168.1.1",
            endpoint="/api/test"
        )

        rule = rule_manager.get_rule(context)
        print_rule(rule)

        for i in range(10):
            response = rate_limiter.allow_request(context)

            print(
                f"Req {i+1}:",
                "ALLOWED" if response.allowed else "DENIED",
                "| Remaining:", response.headers["X-RateLimit-Remaining"],
                "| Retry:", response.headers["X-RateLimit-Retry-After"]
            )

            time.sleep(0.5)


def test_key_types():
    print("\n==============================")
    print("Testing Key Types")
    print("==============================")

    key_types = [
        KeyType.USER,
        KeyType.IP,
        KeyType.ENDPOINT
    ]

    for key_type in key_types:
        print(f"\n--- Key Type: {key_type} ---")

        storage = RedisStorage()
        key_generator = KeyGenerator()
        strategy_factory = StrategyFactory(storage)

        class CustomRuleManager(RuleManager):
            def get_rule(self, context):
                return RateLimitRule(
                    limit=3,
                    window=10,
                    key_type=key_type,
                    strategy_type=StrategyType.FIXED_WINDOW
                )

        rule_manager = CustomRuleManager()

        rate_limiter = RateLimiter(
            storage,
            rule_manager,
            key_generator,
            strategy_factory
        )

        context = RequestContext(
            user_id="user1",
            ip="1.1.1.1",
            endpoint="/api"
        )

        rule = rule_manager.get_rule(context)
        print_rule(rule)

        contexts = [
            RequestContext(user_id="user1", ip="1.1.1.1", endpoint="/api"),
            RequestContext(user_id="user2", ip="1.1.1.1", endpoint="/api"),
            RequestContext(user_id="user1", ip="2.2.2.2", endpoint="/api")
        ]

        for i in range(5):
            print(f"\nIteration {i+1}")
            for ctx in contexts:
                response = rate_limiter.allow_request(ctx)
                print(
                    f"{ctx.user_id} | {ctx.ip} →",
                    "ALLOWED" if response.allowed else "DENIED"
                )


def test_window_reset():
    print("\n==============================")
    print("Testing Window Reset")
    print("==============================")

    storage = RedisStorage()
    key_generator = KeyGenerator()
    strategy_factory = StrategyFactory(storage)

    class CustomRuleManager(RuleManager):
        def get_rule(self, context):
            return RateLimitRule(
                limit=3,
                window=5,
                key_type=KeyType.USER,
                strategy_type=StrategyType.FIXED_WINDOW
            )

    rule_manager = CustomRuleManager()

    rate_limiter = RateLimiter(
        storage,
        rule_manager,
        key_generator,
        strategy_factory
    )

    context = RequestContext(
        user_id="user_reset",
        ip="1.1.1.1",
        endpoint="/api/reset"
    )

    rule = rule_manager.get_rule(context)
    print_rule(rule)

    print("\nSending initial requests:")
    for i in range(5):
        response = rate_limiter.allow_request(context)
        print(f"{i+1}:", response.allowed)

    print("\nWaiting for window reset...")
    time.sleep(5)

    print("\nAfter reset:")
    for i in range(3):
        context.timestamp = time.time()
        response = rate_limiter.allow_request(context)
        print(f"{i+1}:", response.allowed)


def main():
    print("\n🔥 RATE LIMITER TEST SUITE 🔥")

    test_all_strategies()
    test_key_types()
    test_window_reset()


if __name__ == "__main__":
    main()
