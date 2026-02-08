#!/usr/bin/env python3
"""
ReAct Agent Loop
A foundational agent pattern: Reason → Act → Observe.

This is the simplest agent architecture that actually works.
No magic, no frameworks — just a loop that thinks, acts, and learns from results.
"""

import os
import json
from typing import Any, Dict, List, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================================
# TOOLS - Define what the agent can do
# ============================================================================

def get_weather(city: str) -> Dict[str, Any]:
    """
    Mock weather API. In production, call a real weather service.
    
    The pattern matters more than the implementation.
    Your tools will fail. Handle it gracefully.
    """
    # Simulate occasional API failures (10% chance)
    import random
    if random.random() < 0.1:
        raise Exception(f"Weather API timeout for {city}")
    
    # Mock weather data
    weather_data = {
        "San Francisco": {"temp": 62, "condition": "Foggy", "precipitation": "20%"},
        "New York": {"temp": 75, "condition": "Sunny", "precipitation": "5%"},
        "Seattle": {"temp": 58, "condition": "Rainy", "precipitation": "80%"},
    }
    
    return weather_data.get(city, {"temp": 70, "condition": "Unknown", "precipitation": "50%"})


def search_web(query: str) -> str:
    """
    Mock web search. In production, use a real search API.
    
    Keep tool interfaces simple. String in, string out when possible.
    Complex return types make debugging harder.
    """
    # Mock search results
    results = {
        "umbrella San Francisco": "Light drizzle expected. Umbrella recommended for afternoon.",
        "current events": "Breaking: AI agents now write their own documentation.",
    }
    
    return results.get(query, f"Search results for: {query}")


# ============================================================================
# TOOL REGISTRY - Map tool names to functions
# ============================================================================

def tool_executor(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Execute a tool by name with given arguments.
    
    This is where your tools live. Keep it simple:
    - Tool name → function mapping
    - Error handling at the boundary
    - Return strings (easier for the LLM to process)
    """
    tools = {
        "get_weather": get_weather,
        "search_web": search_web,
    }
    
    if tool_name not in tools:
        return f"Error: Unknown tool '{tool_name}'"
    
    try:
        result = tools[tool_name](**arguments)
        # Convert dict results to JSON strings for consistency
        if isinstance(result, dict):
            return json.dumps(result, indent=2)
        return str(result)
    except Exception as e:
        # Don't crash. Return the error to the agent.
        # Let it decide what to do next.
        return f"Error executing {tool_name}: {str(e)}"


# ============================================================================
# TOOL SCHEMAS - Tell the LLM what tools exist
# ============================================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather information for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name, e.g. San Francisco"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


# ============================================================================
# AGENT LOOP
# ============================================================================

def react_agent(task: str, max_iterations: int = 10) -> str:
    """
    The ReAct loop. Simple, transparent, reliable.
    
    Parameters:
    - task: What you want the agent to do
    - max_iterations: Safety limit to prevent infinite loops
    
    Returns the agent's final answer or an error message.
    """
    
    # System prompt defines the agent's behavior
    # Be specific. Vague prompts = unpredictable agents.
    system_prompt = """You are a helpful AI agent that can use tools to complete tasks.

For each step:
1. Think about what you need to do next
2. Call a tool if needed, or provide your final answer
3. Observe the result and continue

When you have enough information to answer the user's question, respond directly without calling more tools.
Be concise and helpful."""

    # Conversation history - includes all reasoning and tool results
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task}
    ]
    
    for iteration in range(max_iterations):
        print(f"\n{'='*60}")
        print(f"Iteration {iteration + 1}/{max_iterations}")
        print(f"{'='*60}")
        
        # Agent reasons about what to do next
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use gpt-4 for better reasoning
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"  # Let the model decide when to use tools
        )
        
        message = response.choices[0].message
        
        # Case 1: Agent wants to use a tool
        if message.tool_calls:
            print(f"\n🤔 Agent reasoning: Calling tools...")
            
            # Add the assistant's message (with tool calls) to history
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
            
            # Execute each tool call
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                print(f"🔧 Calling {tool_name}({tool_args})")
                
                # Execute the tool
                result = tool_executor(tool_name, tool_args)
                print(f"📊 Result: {result}")
                
                # Add tool result to conversation history
                messages.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call.id
                })
        
        # Case 2: Agent provides final answer (no tool calls)
        else:
            print(f"\n✅ Agent final answer:")
            print(message.content)
            return message.content
    
    # Hit max iterations without completing
    return f"Error: Agent did not complete task within {max_iterations} iterations"


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Example task - modify this to test different scenarios
    task = "What's the weather in San Francisco and should I bring an umbrella?"
    
    print("="*60)
    print("ReAct Agent")
    print("="*60)
    print(f"\nTask: {task}\n")
    
    result = react_agent(task)
    
    print("\n" + "="*60)
    print("COMPLETED")
    print("="*60)
