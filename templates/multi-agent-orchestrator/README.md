# Multi-Agent Orchestrator

**When one agent isn't enough. Coordinate specialized agents without losing your mind.**

## What It Does

An orchestrator pattern for coordinating multiple specialized agents:
- **Task routing** - Send tasks to the right specialist
- **Parallel execution** - Run independent tasks concurrently
- **Result aggregation** - Combine outputs into coherent responses
- **Failure isolation** - One agent's failure doesn't crash the system

## Why This Pattern

Single agents hit limits fast:
- **Too many tools** → Confused decision-making
- **Too broad context** → Diluted expertise
- **Too many responsibilities** → Poor performance

Specialized agents are better at specific tasks. But coordination is hard.

This pattern solves it.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

```bash
export OPENAI_API_KEY="sk-..."
```

## Usage

```bash
python orchestrator.py
```

## Architecture

```
Orchestrator (Central Coordinator)
├── Research Agent (Web search, data gathering)
├── Analysis Agent (Data processing, insights)
└── Writing Agent (Content generation, summaries)
```

**Orchestrator decides:**
- Which agents to use
- Task decomposition
- Execution order (parallel vs sequential)
- How to combine results

**Agents focus on:**
- Their specific domain
- Doing one thing well
- Returning structured results

## How It Works

### 1. Task Classification

Orchestrator analyzes the task and determines:
- Which agents are needed
- Whether tasks can run in parallel
- Dependencies between subtasks

### 2. Task Execution

```python
# Sequential (when tasks depend on each other)
research_result = research_agent.run(task)
analysis_result = analysis_agent.run(research_result)

# Parallel (when tasks are independent)
results = await asyncio.gather(
    research_agent.run(task_a),
    analysis_agent.run(task_b)
)
```

### 3. Result Synthesis

Orchestrator combines agent outputs into a final response.

## Production Notes

**Communication overhead:** Inter-agent communication has latency. Don't over-decompose tasks.

**State management:** Agents shouldn't share state directly. Pass data explicitly through the orchestrator.

**Error handling:** If one agent fails, the orchestrator should gracefully degrade or retry with a different strategy.

**Cost control:** Multiple agents = multiple API calls. Monitor token usage carefully.

**Timeouts:** Set per-agent timeouts. Don't let one slow agent block the entire system.

## When to Use This

**Use multi-agent when:**
- Tasks require distinct expertise (research + analysis + writing)
- You want to parallelize independent subtasks
- Single agent performance degrades due to complexity
- You need fault isolation between components

**Don't use multi-agent when:**
- Task is simple and focused
- Overhead exceeds benefits
- Communication costs outweigh specialization gains
- You're just starting (begin with single agent, refactor when needed)

## Scaling Patterns

**Start simple:**
```
User → Agent → Result
```

**Add specialization:**
```
User → Orchestrator → [Specialist Agents] → Result
```

**Scale further:**
```
User → Master Orchestrator
       ├── Team A Orchestrator → [Agents]
       ├── Team B Orchestrator → [Agents]
       └── Team C Orchestrator → [Agents]
```

Only add layers when complexity demands it.

## Trade-offs

**Pros:**
- Clear separation of concerns
- Easier to optimize individual agents
- Parallelization opportunities
- Better fault isolation

**Cons:**
- Higher latency (multiple LLM calls)
- More complex debugging
- Higher API costs
- Coordination overhead

This pattern makes sense when specialization benefits outweigh coordination costs.
