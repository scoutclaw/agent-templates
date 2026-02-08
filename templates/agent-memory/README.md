# Agent Memory & State Management

**Agents that remember. Conversation context, long-term memory, state persistence.**

## What It Does

A memory system for agents that need to remember:
- **Conversation history** - Recent messages and context
- **Long-term memory** - Important facts across sessions
- **State persistence** - Save and restore agent state
- **Context window management** - Handle token limits gracefully

Stateless agents forget everything. Stateful agents are useful.

## Why This Pattern

Without memory:
- Agents repeat themselves
- Can't reference past conversations
- No learning or adaptation
- Context lost between sessions

With memory:
- Coherent multi-turn conversations
- Remembers user preferences
- Builds on past interactions
- Survives restarts

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
python agent.py
```

The agent will:
1. Load existing memory from disk (if available)
2. Process your conversation
3. Save memory to disk
4. Remember context in future runs

## Memory Types

### 1. Short-Term Memory (Conversation History)

Recent messages in the conversation. Lives in the context window.

**Implementation:** List of messages sent to LLM.

**Problem:** Context windows fill up fast.

**Solution:** Truncate old messages, but keep important context.

### 2. Long-Term Memory (Persistent Facts)

Important information that should persist across sessions.

**Implementation:** JSON file with key-value pairs.

**Examples:**
- User preferences ("user prefers concise answers")
- Important facts ("user is working on project X")
- Learned behaviors ("user dislikes verbose explanations")

### 3. Working Memory (Current State)

Temporary state needed during task execution.

**Implementation:** In-memory dict, optionally persisted.

**Examples:**
- Current task progress
- Intermediate results
- Agent goals and subgoals

## How It Works

### Memory Lifecycle

```python
# 1. Load memory
memory = Memory.load("user_123")

# 2. Add to conversation
messages = memory.get_conversation_context()
messages.append({"role": "user", "content": "Hello"})

# 3. Get response
response = llm.chat(messages)

# 4. Update memory
memory.add_message("user", "Hello")
memory.add_message("assistant", response)
memory.add_fact("last_greeting", "Hello")

# 5. Save memory
memory.save()
```

### Context Window Management

When conversation history exceeds token limit:

**Option 1: Truncate old messages**
- Keep system prompt + recent N messages
- Simple but loses context

**Option 2: Summarize old context**
- Use LLM to summarize old messages
- Append summary, keep recent messages
- Better context retention

**Option 3: Semantic pruning**
- Keep messages relevant to current topic
- Requires embedding similarity search
- Most sophisticated but complex

This template uses Option 2 (summarization) as a good balance.

## Production Notes

**Storage:** This uses JSON files for simplicity. In production, use:
- Redis for fast in-memory state
- PostgreSQL for structured data
- Vector DB (Pinecone, Weaviate) for semantic search

**Concurrency:** File-based storage has race conditions. Use proper locking or a database.

**Privacy:** Memory contains user data. Encrypt at rest, handle with care.

**Memory decay:** Old facts become stale. Implement expiration or confidence scoring.

**Cost control:** Larger context = more tokens = higher cost. Monitor and optimize.

## Memory Strategies

### Conservative (Low Cost)
- Small context window (10-20 messages)
- Aggressive summarization
- Minimal long-term storage

### Balanced (Default)
- Medium context window (50-100 messages)
- Summarize when needed
- Store key facts only

### Comprehensive (High Fidelity)
- Large context window (500+ messages)
- Detailed long-term memory
- Higher API costs but better continuity

Choose based on your use case and budget.

## Trade-offs

**Pros:**
- Coherent conversations
- Personalization
- Cross-session continuity
- Better user experience

**Cons:**
- Higher token costs
- Storage requirements
- Complexity in managing state
- Privacy/security concerns

For production agents, memory is usually worth it.

## Debugging Memory Issues

**Agent forgets things:**
- Check if memory is being saved
- Verify memory is loaded on startup
- Ensure important facts are in long-term storage

**Context window errors:**
- Reduce messages in conversation history
- Implement summarization earlier
- Use a model with larger context window

**Inconsistent behavior:**
- Memory corruption or race conditions
- Check for concurrent writes
- Add validation when loading memory
