#!/usr/bin/env python3
"""
Tool-Calling Agent with Retry Logic
Production-grade error handling for unreliable APIs.

In production, everything fails. This agent knows it and handles it gracefully.
"""

import os
import json
import time
import random
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

load_dotenv()

# Configure logging - essential for debugging production failures
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================================
# CIRCUIT BREAKER - Stop calling dead services
# ============================================================================

@dataclass
class CircuitBreaker:
    """
    Circuit breaker pattern prevents cascading failures.
    
    When a service fails repeatedly, "open" the circuit and fast-fail
    instead of wasting time on retries.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Service is down, fail fast
    - HALF_OPEN: Testing if service recovered
    """
    failure_threshold: int = 5  # Failures before opening circuit
    timeout_seconds: int = 60   # How long to wait before retrying
    
    # Internal state
    failures: Dict[str, int] = field(default_factory=dict)
    opened_at: Dict[str, datetime] = field(default_factory=dict)
    
    def record_success(self, service: str):
        """Service call succeeded - reset failure count"""
        self.failures[service] = 0
        if service in self.opened_at:
            del self.opened_at[service]
            logger.info(f"Circuit breaker CLOSED for {service}")
    
    def record_failure(self, service: str):
        """Service call failed - increment failure count"""
        self.failures[service] = self.failures.get(service, 0) + 1
        
        if self.failures[service] >= self.failure_threshold:
            self.opened_at[service] = datetime.now()
            logger.warning(f"Circuit breaker OPENED for {service} after {self.failures[service]} failures")
    
    def is_open(self, service: str) -> bool:
        """Check if circuit is open for this service"""
        if service not in self.opened_at:
            return False
        
        # Check if timeout has expired
        if datetime.now() - self.opened_at[service] > timedelta(seconds=self.timeout_seconds):
            logger.info(f"Circuit breaker entering HALF_OPEN for {service}")
            # Enter half-open state (allow one test request)
            del self.opened_at[service]
            return False
        
        return True


# Global circuit breaker instance
circuit_breaker = CircuitBreaker()


# ============================================================================
# RETRY LOGIC - Handle transient failures
# ============================================================================

class RetryableError(Exception):
    """Errors that should be retried (network issues, rate limits, etc.)"""
    pass


class PermanentError(Exception):
    """Errors that shouldn't be retried (bad input, auth failures, etc.)"""
    pass


def smart_retry(func: Callable) -> Callable:
    """
    Decorator for retrying with exponential backoff and jitter.
    
    Retries on transient failures, fails fast on permanent errors.
    Uses tenacity library for robust retry logic.
    """
    return retry(
        # Only retry on specific exceptions
        retry=retry_if_exception_type(RetryableError),
        # Stop after 3 attempts
        stop=stop_after_attempt(3),
        # Exponential backoff: 1s, 2s, 4s (with jitter)
        wait=wait_exponential(multiplier=1, min=1, max=10),
        # Log before sleeping
        before_sleep=before_sleep_log(logger, logging.WARNING),
        # Re-raise the last exception if all retries fail
        reraise=True
    )(func)


# ============================================================================
# MOCK TOOLS - Simulate unreliable APIs
# ============================================================================

def unreliable_weather_api(city: str) -> Dict[str, Any]:
    """
    Mock weather API that fails 30% of the time.
    
    In production, this would be a real API call.
    The failure patterns here mirror real-world issues:
    - Timeouts (transient)
    - Rate limits (transient)
    - Invalid input (permanent)
    - Server errors (transient)
    """
    
    # Simulate different types of failures
    failure_type = random.random()
    
    if failure_type < 0.15:
        # Network timeout (should retry)
        logger.warning(f"Weather API timeout for {city}")
        raise RetryableError(f"Timeout calling weather API for {city}")
    
    elif failure_type < 0.25:
        # Rate limit (should retry after backoff)
        logger.warning(f"Weather API rate limit for {city}")
        raise RetryableError(f"Rate limit exceeded for weather API")
    
    elif failure_type < 0.30:
        # Server error (should retry)
        logger.warning(f"Weather API server error for {city}")
        raise RetryableError(f"Weather API server error (500)")
    
    # Success case
    weather_data = {
        "San Francisco": {"temp": 62, "condition": "Foggy", "precipitation": "20%"},
        "New York": {"temp": 75, "condition": "Sunny", "precipitation": "5%"},
        "Seattle": {"temp": 58, "condition": "Rainy", "precipitation": "80%"},
        "London": {"temp": 55, "condition": "Cloudy", "precipitation": "60%"},
    }
    
    if city not in weather_data:
        # Invalid input - don't retry
        raise PermanentError(f"Unknown city: {city}")
    
    logger.info(f"Weather API success for {city}")
    return weather_data[city]


def database_query(query: str) -> str:
    """
    Mock database that occasionally fails.
    
    Simulates connection pool exhaustion, deadlocks, etc.
    """
    if random.random() < 0.2:
        logger.warning(f"Database connection failed")
        raise RetryableError("Database connection pool exhausted")
    
    logger.info(f"Database query success: {query}")
    return f"Database result for: {query}"


# ============================================================================
# TOOL EXECUTOR - Wrap all tools with retry logic
# ============================================================================

@smart_retry
def execute_tool_with_retry(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Execute a tool with automatic retry logic.
    
    This wraps all tool calls with:
    1. Circuit breaker check
    2. Retry logic for transient failures
    3. Error handling and logging
    """
    
    # Check circuit breaker first - don't waste time on dead services
    if circuit_breaker.is_open(tool_name):
        logger.warning(f"Circuit breaker OPEN for {tool_name}, failing fast")
        raise PermanentError(f"{tool_name} is currently unavailable, please try again later")
    
    # Tool registry
    tools = {
        "get_weather": unreliable_weather_api,
        "query_database": database_query,
    }
    
    if tool_name not in tools:
        raise PermanentError(f"Unknown tool: {tool_name}")
    
    try:
        # Execute the tool
        result = tools[tool_name](**arguments)
        
        # Success - reset circuit breaker
        circuit_breaker.record_success(tool_name)
        
        # Convert dict to JSON for consistency
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
        
    except RetryableError as e:
        # Transient failure - will be retried by decorator
        circuit_breaker.record_failure(tool_name)
        logger.error(f"Retryable error in {tool_name}: {e}")
        raise  # Re-raise to trigger retry
        
    except PermanentError as e:
        # Permanent failure - don't retry
        logger.error(f"Permanent error in {tool_name}: {e}")
        return f"Error: {str(e)}"
        
    except Exception as e:
        # Unknown error - treat as permanent (fail safe)
        logger.error(f"Unexpected error in {tool_name}: {e}")
        return f"Unexpected error: {str(e)}"


# ============================================================================
# AGENT LOGIC
# ============================================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city. May be temporarily unavailable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": "Query the database. May fail under high load.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL-like query string"}
                },
                "required": ["query"]
            }
        }
    }
]


def robust_agent(task: str, max_iterations: int = 10) -> str:
    """
    Agent with production-grade error handling.
    
    Handles tool failures gracefully and can complete tasks even when
    some tools are unavailable.
    """
    
    system_prompt = """You are a resilient AI agent that handles tool failures gracefully.

When a tool fails:
1. Check the error message
2. Try alternative approaches if available
3. If a tool is unavailable, work around it or inform the user

Be helpful even when tools fail. Don't give up after one failure."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task}
    ]
    
    for iteration in range(max_iterations):
        print(f"\n{'='*60}")
        print(f"Iteration {iteration + 1}/{max_iterations}")
        print(f"{'='*60}")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        if message.tool_calls:
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })
            
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                print(f"\n🔧 Calling {tool_name}({tool_args})")
                
                # Execute with retry logic
                try:
                    result = execute_tool_with_retry(tool_name, tool_args)
                    print(f"✅ Success: {result}")
                except Exception as e:
                    # All retries exhausted
                    result = f"Error: {str(e)} (all retries exhausted)"
                    print(f"❌ Failed: {result}")
                
                messages.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call.id
                })
        else:
            print(f"\n✅ Final answer:")
            print(message.content)
            return message.content
    
    return f"Error: Task not completed within {max_iterations} iterations"


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    task = "Get the weather for San Francisco, New York, and Seattle. Also query the database for historical weather patterns."
    
    print("="*60)
    print("Robust Tool-Calling Agent")
    print("="*60)
    print(f"\nTask: {task}\n")
    print("Note: Tools will fail randomly to demonstrate retry logic\n")
    
    result = robust_agent(task)
    
    print("\n" + "="*60)
    print("COMPLETED")
    print("="*60)
