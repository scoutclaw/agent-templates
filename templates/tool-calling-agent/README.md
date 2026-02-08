# Tool-Calling Agent with Retry Logic

**Because APIs fail. Handle it or die trying.**

## What It Does

An agent that calls tools with production-grade error handling:
- **Exponential backoff** for transient failures
- **Retry limits** to prevent infinite loops
- **Circuit breaker** to fast-fail when a service is down
- **Graceful degradation** when tools fail

This is what separates demo code from production code.

## Why This Pattern

In the lab, APIs always work. In production:
- Rate limits hit
- Networks timeout
- Services go down
- APIs return garbage

Your agent needs to handle this without crashing or burning through your API budget.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

## Usage

```bash
python agent.py
```

The code includes a mock API that fails randomly to demonstrate retry behavior.

## How It Works

### 1. Retry Decorator

```python
@retry_with_backoff(max_retries=3, base_delay=1.0)
def unreliable_api_call():
    # Your flaky API call here
    pass
```

**Exponential backoff:** Wait 1s, then 2s, then 4s between retries.  
**Jitter:** Add randomness to prevent thundering herd.

### 2. Circuit Breaker

Track failure rates. When a tool fails repeatedly, stop trying:

```python
if circuit_breaker.is_open("api_name"):
    return "Service unavailable, try again later"
```

Prevents wasting time on dead services.

### 3. Tool Execution Wrapper

Every tool call goes through error handling:
- Catches exceptions
- Retries transient failures
- Returns useful error messages
- Logs failures for debugging

## Production Notes

**Idempotency:** Some operations shouldn't be retried (e.g., charging a credit card). Add idempotency keys or skip retries for non-idempotent operations.

**Retry budget:** Limit total retries across all operations. Don't let one bad API call consume your entire timeout.

**Monitoring:** Log retry counts and failure rates. Alert when error rates spike.

**Fallbacks:** When a tool fails permanently, have a backup strategy. Can you use cached data? A different API? Return a partial answer?

## Configuration Options

Tune these based on your SLAs:

- `max_retries`: How many times to retry (3-5 is reasonable)
- `base_delay`: Starting delay between retries (1-2 seconds)
- `max_delay`: Cap on exponential backoff (30-60 seconds)
- `circuit_breaker_threshold`: Failure rate to open circuit (0.5 = 50%)
- `circuit_breaker_timeout`: How long to wait before retrying a failed service

## Trade-offs

**Pros:**
- Handles real-world API failures
- Prevents cascading failures
- Better user experience (eventual success vs immediate crash)

**Cons:**
- Slower when services are flaky
- More complex to debug
- Can mask underlying infrastructure problems

Use this when reliability matters more than raw speed.
