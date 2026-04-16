from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
import time


# =========================
# Constants
# =========================

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
    def __init__(self, allowed: bool, headers: Dict[str,Any]):
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

    def get_sorted_range(self, key:str, start:float, end:float) -> List[Any]:
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
    def allow_request(self,key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
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
    def allow_request(self,key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
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
    def allow_request(self,key: str, rule: RateLimitRule, current_time: float) -> RateLimitResponse:
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
        else:
            allowed = False

        updated_bucket = {
            "current_count": current_count,
            "previous_count": previous_count,
            "current_window_start": current_window_start
        }

        self.storage.set(key, updated_bucket)
        self.storage.set_expiry(key, window_size * 2)

        if not allowed:
            retry_after = window_size - elapsed
        else:
            retry_after = 0

        remaining = max(0, int(rule.limit - effective_count))

        headers = {
            "X-RateLimit-Limit": rule.limit,
            "X-RateLimit-Remaining": remaining,
            "X-RateLimit-Retry-After": round(retry_after, 2)
        }

        return RateLimitResponse(allowed=allowed, headers=headers)

