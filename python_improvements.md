# 🚀 Step-by-Step Upgrade Guide (Actionable)

---

## 1. ⚡ Replace In-Memory Storage with Real Redis

### Goal

Replace your current `RedisStorage` (dict-based) with actual Redis.

### Steps

1. Install dependencies:

```bash
pip install redis
```

2. Start Redis locally:

```bash
redis-server
```

3. Create Redis client:

```python
import redis

self.client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
```

4. Replace methods one-by-one:

### Replace `get`

```python
def get(self, key):
    value = self.client.get(key)
    return json.loads(value) if value else None
```

### Replace `set`

```python
def set(self, key, value):
    self.client.set(key, json.dumps(value))
```

### Replace `increment`

```python
def increment(self, key, amount=1):
    return self.client.incrby(key, amount)
```

### Replace expiry

```python
def set_expiry(self, key, ttl):
    self.client.expire(key, ttl)
```

### Replace sorted set ops

```python
def add_to_sorted_set(self, key, score, value):
    self.client.zadd(key, {str(value): score})

def get_sorted_range(self, key, start, end):
    return self.client.zrangebyscore(key, start, end)

def remove_expired(self, key, threshold):
    self.client.zremrangebyscore(key, 0, threshold)
```

---

## 2. 🔒 Make Sliding Window Log Atomic (Lua Script)

### Goal

Avoid race conditions in sliding window

### Steps

1. Create Lua script:

```python
lua_script = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1])
local count = redis.call('ZCARD', KEYS[1])

if count < tonumber(ARGV[2]) then
    redis.call('ZADD', KEYS[1], ARGV[3], ARGV[3])
    return {1, count + 1}
else
    return {0, count}
end
"""
```

2. Register script:

```python
self.script = self.client.register_script(lua_script)
```

3. Call it inside strategy:

```python
result = self.script(
    keys=[key],
    args=[window_start, rule.limit, current_time]
)

allowed = result[0] == 1
count = result[1]
```

---

## 3. 🧠 Fix Retry-After Logic (Precise)

### Sliding Window Log Fix

Replace:

```python
oldest = timestamps[0]
retry_after = rule.window - (current_time - oldest)
```

With:

```python
oldest = float(timestamps[0])
retry_after = max(0, oldest + rule.window - current_time)
```

---

## 4. 📊 Add Metrics Tracking

### Goal

Track usage

### Steps

1. Add in RateLimiter:

```python
self.metrics = {
    "allowed": 0,
    "blocked": 0
}
```

2. Update in allow_request:

```python
response = strategy.allow_request(...)

if response.allowed:
    self.metrics["allowed"] += 1
else:
    self.metrics["blocked"] += 1
```

3. Print metrics:

```python
print(self.metrics)
```

---

## 5. 🔑 Improve Key Generation

### Steps

1. Import hash:

```python
import hashlib
```

2. Modify KeyGenerator:

```python
raw = f"{rule.key_type}:{identifier}:{context.endpoint}"
hashed = hashlib.md5(raw.encode()).hexdigest()

return f"rl:{hashed}"
```

---

## 6. ⚙️ Dynamic Rule Manager (DB Simulation)

### Step-by-step

1. Create fake DB:

```python
RULE_DB = {
    "user_1": (5, 10),
    "user_2": (10, 10)
}
```

2. Modify RuleManager:

```python
def get_rule(self, context):
    limit, window = RULE_DB.get(context.user_id, (3, 10))

    return RateLimitRule(
        limit=limit,
        window=window,
        key_type=KeyType.USER,
        strategy_type=StrategyType.FIXED_WINDOW
    )
```

---

## 7. 🌍 Distributed Setup (Local Simulation)

### Goal

Simulate multiple servers

### Steps

1. Create 2 rate limiter instances:

```python
rl1 = RateLimiter(...)
rl2 = RateLimiter(...)
```

2. Use SAME Redis storage:

```python
storage = RedisStorage()  # must be shared Redis in real
```

3. Alternate requests:

```python
for i in range(10):
    rl = rl1 if i % 2 == 0 else rl2
    response = rl.allow_request(context)
```

---

## 8. 🧪 Convert Tests to Proper Assertions

### Replace print tests

Example:

```python
def test_fixed_window():
    storage = RedisStorage()
    strategy = FixedWindowStrategy(storage)

    rule = RateLimitRule(3, 10, KeyType.USER, StrategyType.FIXED_WINDOW)

    key = "test"

    assert strategy.allow_request(key, rule, time.time()).allowed
    assert strategy.allow_request(key, rule, time.time()).allowed
    assert strategy.allow_request(key, rule, time.time()).allowed
    assert not strategy.allow_request(key, rule, time.time()).allowed
```

---

## 9. 🧵 Convert to Async (FastAPI Ready)

### Steps

1. Install:

```bash
pip install fastapi uvicorn aioredis
```

2. Change functions:

```python
async def allow_request(...)
```

3. Replace Redis client with:

```python
import aioredis
self.client = await aioredis.from_url(...)
```

---

## 10. 🔌 Plug Into API (FastAPI)

### Steps

1. Create app:

```python
from fastapi import FastAPI

app = FastAPI()
```

2. Add middleware:

```python
@app.middleware("http")
async def rate_limit(request, call_next):
    context = RequestContext(...)

    response = limiter.allow_request(context)

    if not response.allowed:
        return JSONResponse(status_code=429, content=response.headers)

    return await call_next(request)
```

---

## 11. 📉 Limit Memory Growth

### Sliding Window Log Fix

Add before insert:

```python
if len(timestamps) > rule.limit:
    self.storage.remove_expired(key, current_time - rule.window)
```

---

## 12. 🔐 Multi-Tenant Rules

### Steps

1. Extend context:

```python
context.plan = "premium"
```

2. Modify RuleManager:

```python
if context.plan == "premium":
    limit = 100
else:
    limit = 10
```

---

## 13. 🧩 Hybrid Strategy

### Steps

1. Create wrapper:

```python
class HybridStrategy(RateLimitStrategy):
    def __init__(self, storage):
        self.token = TokenBucketStrategy(storage)
        self.window = SlidingWindowLogStrategy(storage)
```

2. Apply both:

```python
if not self.token.allow_request(...).allowed:
    return denied

return self.window.allow_request(...)
```

---

# ✅ What You Should Do (Execution Plan)

Follow this exact order:

1. Replace storage with Redis
2. Fix retry logic
3. Add metrics
4. Improve key generation
5. Add dynamic rules
6. Add proper tests
7. Convert to async
8. Integrate with API
9. Add atomic Lua scripts
10. Optimize memory

---
