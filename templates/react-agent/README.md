# ReAct Agent Loop

**The foundational agent pattern. Reason → Act → Observe.**

## What It Does

A simple agent loop that:
1. **Reasons** about what to do next
2. **Acts** by calling a tool
3. **Observes** the result
4. Repeats until the task is complete

This is the baseline. If you're building an agent, start here.

## Why This Pattern

- **Transparent.** You can see the agent's reasoning at each step.
- **Debuggable.** When it fails, you know where.
- **Composable.** Easy to add new tools or modify behavior.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Or create a `.env` file:

```
OPENAI_API_KEY=sk-...
```

## Usage

```bash
python agent.py
```

The example task: "What's the weather in San Francisco and should I bring an umbrella?"

Modify the `task` variable in `agent.py` to test different queries.

## How It Works

1. **System prompt** defines the agent's role and available tools
2. **Agent reasons** about which tool to call next (or if it's done)
3. **Tool executor** runs the selected tool
4. **Result** is added to conversation history
5. Loop continues until agent returns a final answer

## Tools

Two example tools included:
- `get_weather(city)` — mock weather API
- `search_web(query)` — mock web search

Add your own tools by:
1. Defining the function
2. Adding it to the `tools` list in JSON schema format
3. Adding it to the `tool_executor` function

## Production Notes

**Max iterations:** Set to prevent infinite loops. Adjust based on task complexity.

**Error handling:** Tools can fail. The agent sees the error and can retry or try a different approach.

**Token management:** Long conversations hit context limits. Implement truncation or summarization for production use.

## Trade-offs

**Pros:**
- Simple to understand and debug
- Works for most agent tasks
- Easy to extend

**Cons:**
- One tool call per iteration (slower for multi-step tasks)
- No parallelization
- No sophisticated planning

For more complex needs, see the other templates.
