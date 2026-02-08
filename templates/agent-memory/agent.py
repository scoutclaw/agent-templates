#!/usr/bin/env python3
"""
Agent Memory & State Management
Agents that remember across conversations.

Memory types:
1. Short-term: Recent conversation history
2. Long-term: Persistent facts and preferences
3. Working: Temporary state during execution

Handles context limits, state persistence, and memory retrieval.
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from openai import OpenAI
from dotenv import load_dotenv
import tiktoken

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================================
# TOKEN COUNTING - Essential for context window management
# ============================================================================

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text using tiktoken.
    
    Context windows are measured in tokens, not characters.
    Always count tokens, never guess.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")  # Fallback
    
    return len(encoding.encode(text))


def count_messages_tokens(messages: List[Dict[str, str]], model: str = "gpt-4") -> int:
    """Count total tokens in a message list"""
    # Rough approximation: messages have overhead beyond just content
    total = 0
    for msg in messages:
        total += count_tokens(msg.get("content", ""), model)
        total += 4  # Message overhead (role, formatting, etc.)
    return total


# ============================================================================
# MEMORY STORAGE
# ============================================================================

@dataclass
class MemoryEntry:
    """A single long-term memory fact"""
    key: str
    value: str
    timestamp: str
    importance: int = 5  # 1-10 scale
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Memory:
    """
    Agent memory system with short-term and long-term storage.
    
    Short-term: Recent conversation (in context window)
    Long-term: Important facts (persisted to disk)
    """
    
    def __init__(
        self,
        user_id: str,
        max_context_tokens: int = 4000,
        memory_dir: str = "./memory_data"
    ):
        self.user_id = user_id
        self.max_context_tokens = max_context_tokens
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        # Short-term memory (conversation history)
        self.conversation: List[Dict[str, str]] = []
        
        # Long-term memory (persistent facts)
        self.facts: Dict[str, MemoryEntry] = {}
        
        # Working memory (current session state)
        self.working_state: Dict[str, Any] = {}
    
    # ========================================================================
    # PERSISTENCE
    # ========================================================================
    
    def _get_memory_file(self) -> Path:
        """Get the memory file path for this user"""
        return self.memory_dir / f"{self.user_id}_memory.json"
    
    def save(self):
        """
        Save memory to disk.
        
        In production:
        - Use a proper database
        - Add file locking for concurrent access
        - Encrypt sensitive data
        - Handle write failures gracefully
        """
        memory_data = {
            "user_id": self.user_id,
            "updated_at": datetime.now().isoformat(),
            "facts": {k: v.to_dict() for k, v in self.facts.items()},
            "last_conversation": self.conversation[-20:],  # Keep recent messages only
        }
        
        with open(self._get_memory_file(), 'w') as f:
            json.dump(memory_data, f, indent=2)
        
        print(f"💾 Memory saved for user {self.user_id}")
    
    @classmethod
    def load(cls, user_id: str, memory_dir: str = "./memory_data") -> "Memory":
        """Load memory from disk or create new"""
        memory = cls(user_id, memory_dir=memory_dir)
        memory_file = memory._get_memory_file()
        
        if memory_file.exists():
            with open(memory_file, 'r') as f:
                data = json.load(f)
            
            # Load long-term facts
            memory.facts = {
                k: MemoryEntry(**v) 
                for k, v in data.get("facts", {}).items()
            }
            
            # Load recent conversation
            memory.conversation = data.get("last_conversation", [])
            
            print(f"📂 Loaded memory for user {user_id}")
            print(f"   - {len(memory.facts)} facts")
            print(f"   - {len(memory.conversation)} messages")
        else:
            print(f"📝 Created new memory for user {user_id}")
        
        return memory
    
    # ========================================================================
    # CONVERSATION MANAGEMENT
    # ========================================================================
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        self.conversation.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_conversation_context(
        self,
        system_prompt: str,
        include_facts: bool = True
    ) -> List[Dict[str, str]]:
        """
        Get conversation context for LLM, respecting token limits.
        
        Strategy:
        1. Always include system prompt
        2. Add important facts from long-term memory
        3. Add recent conversation
        4. If over limit, summarize older messages
        """
        messages = []
        
        # Start with system prompt (always included)
        system_content = system_prompt
        
        # Add important facts to system prompt
        if include_facts and self.facts:
            facts_summary = self._format_facts()
            system_content += f"\n\n{facts_summary}"
        
        messages.append({"role": "system", "content": system_content})
        
        # Calculate remaining token budget
        used_tokens = count_tokens(system_content)
        remaining_tokens = self.max_context_tokens - used_tokens - 500  # Reserve for response
        
        # Add conversation messages (newest first, then reverse)
        conversation_to_include = []
        for msg in reversed(self.conversation):
            msg_tokens = count_tokens(msg["content"])
            if used_tokens + msg_tokens > remaining_tokens:
                # Would exceed limit - stop here
                break
            
            conversation_to_include.insert(0, {
                "role": msg["role"],
                "content": msg["content"]
            })
            used_tokens += msg_tokens
        
        # If we couldn't fit all messages, add a summary of what was cut
        if len(conversation_to_include) < len(self.conversation):
            cut_count = len(self.conversation) - len(conversation_to_include)
            summary_msg = {
                "role": "system",
                "content": f"[Earlier conversation history of {cut_count} messages omitted to fit context window]"
            }
            conversation_to_include.insert(0, summary_msg)
        
        messages.extend(conversation_to_include)
        
        return messages
    
    # ========================================================================
    # LONG-TERM MEMORY (FACTS)
    # ========================================================================
    
    def add_fact(self, key: str, value: str, importance: int = 5):
        """
        Add or update a long-term memory fact.
        
        Facts are things the agent should remember across sessions:
        - User preferences
        - Important context
        - Learned behaviors
        """
        self.facts[key] = MemoryEntry(
            key=key,
            value=value,
            timestamp=datetime.now().isoformat(),
            importance=importance
        )
    
    def get_fact(self, key: str) -> Optional[str]:
        """Retrieve a specific fact"""
        entry = self.facts.get(key)
        return entry.value if entry else None
    
    def _format_facts(self) -> str:
        """Format facts for inclusion in system prompt"""
        if not self.facts:
            return ""
        
        # Sort by importance (most important first)
        sorted_facts = sorted(
            self.facts.values(),
            key=lambda x: x.importance,
            reverse=True
        )
        
        facts_text = "Important context from previous conversations:\n"
        for fact in sorted_facts[:10]:  # Limit to top 10 facts
            facts_text += f"- {fact.key}: {fact.value}\n"
        
        return facts_text
    
    # ========================================================================
    # WORKING MEMORY (TEMPORARY STATE)
    # ========================================================================
    
    def set_state(self, key: str, value: Any):
        """Set temporary working state"""
        self.working_state[key] = value
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get temporary working state"""
        return self.working_state.get(key, default)


# ============================================================================
# STATEFUL AGENT
# ============================================================================

class StatefulAgent:
    """
    An agent with memory.
    
    Remembers conversation history and important facts across sessions.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory = Memory.load(user_id)
        
        self.system_prompt = """You are a helpful AI assistant with memory.

You remember important facts about the user and past conversations.
When you learn something important, acknowledge it and remember it for future interactions.

Be helpful, concise, and build on previous context."""
    
    def chat(self, user_message: str) -> str:
        """
        Process a user message and return a response.
        
        Handles:
        1. Adding message to memory
        2. Getting conversation context
        3. Calling LLM
        4. Saving memory
        """
        print(f"\n{'='*60}")
        print(f"User: {user_message}")
        print(f"{'='*60}")
        
        # Add user message to memory
        self.memory.add_message("user", user_message)
        
        # Get conversation context with memory
        messages = self.memory.get_conversation_context(self.system_prompt)
        
        print(f"\n📊 Context: {count_messages_tokens(messages)} tokens")
        print(f"   - {len(messages)} messages")
        print(f"   - {len(self.memory.facts)} long-term facts")
        
        # Get response from LLM
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        
        assistant_message = response.choices[0].message.content
        
        # Add response to memory
        self.memory.add_message("assistant", assistant_message)
        
        # Auto-extract and save important facts
        # In production, you'd use a more sophisticated extraction method
        self._extract_facts(user_message, assistant_message)
        
        # Save memory to disk
        self.memory.save()
        
        print(f"\n{'='*60}")
        print(f"Assistant: {assistant_message}")
        print(f"{'='*60}")
        
        return assistant_message
    
    def _extract_facts(self, user_msg: str, assistant_msg: str):
        """
        Simple fact extraction from conversation.
        
        In production, use:
        - Separate LLM call to extract key facts
        - Named entity recognition
        - Semantic similarity to detect important info
        """
        # Simple heuristics for demo purposes
        user_lower = user_msg.lower()
        
        # Detect preferences
        if "i prefer" in user_lower or "i like" in user_lower:
            self.memory.add_fact(
                f"preference_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                user_msg,
                importance=7
            )
        
        # Detect personal info
        if "my name is" in user_lower:
            name = user_msg.split("my name is")[-1].strip().split()[0]
            self.memory.add_fact("user_name", name, importance=10)


# ============================================================================
# MAIN - Interactive Demo
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("Stateful Agent with Memory")
    print("="*60)
    print("\nThis agent remembers your conversations across sessions.")
    print("Try telling it your name, preferences, or asking it to remember facts.")
    print("\nCommands:")
    print("  - 'quit' or 'exit' to stop")
    print("  - 'facts' to see stored memories")
    print("  - 'reset' to clear memory")
    print("="*60)
    
    # Use a test user ID (in production, this would come from auth)
    agent = StatefulAgent("demo_user")
    
    # Demo conversation flow
    demo_messages = [
        "Hi! My name is Alex.",
        "I prefer concise answers without too much explanation.",
        "What's my name?",
        "Remember that I'm working on an AI agent project.",
        "What do you know about me?",
    ]
    
    print("\n🎬 Running demo conversation...\n")
    
    for msg in demo_messages:
        agent.chat(msg)
        print("\n")
    
    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("\nMemory has been saved to ./memory_data/")
    print("Run this script again to see the agent remember the conversation!")
    print("\nTry modifying the demo_messages or running interactively:")
    print("  python agent.py --interactive")
