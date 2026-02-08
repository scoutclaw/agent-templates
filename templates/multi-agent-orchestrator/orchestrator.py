#!/usr/bin/env python3
"""
Multi-Agent Orchestrator
Coordinate specialized agents without chaos.

One orchestrator decides. Multiple specialists execute.
Clear boundaries, explicit communication, no shared state.
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================================
# AGENT DEFINITIONS
# ============================================================================

class AgentType(Enum):
    """Available specialist agents"""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    WRITING = "writing"


@dataclass
class AgentResult:
    """Standardized result format from any agent"""
    agent_type: AgentType
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class SpecialistAgent:
    """
    Base class for specialist agents.
    
    Each specialist:
    - Has a focused domain
    - Takes structured input
    - Returns structured output
    - Doesn't know about other agents
    """
    
    def __init__(self, agent_type: AgentType, system_prompt: str):
        self.agent_type = agent_type
        self.system_prompt = system_prompt
    
    def run(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Execute the agent's task.
        
        Args:
            task: What to do
            context: Optional data from previous agents
        """
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self._format_task(task, context)}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7
            )
            
            result = response.choices[0].message.content
            
            return AgentResult(
                agent_type=self.agent_type,
                success=True,
                data=result,
                metadata={"tokens": response.usage.total_tokens}
            )
            
        except Exception as e:
            return AgentResult(
                agent_type=self.agent_type,
                success=False,
                data=None,
                error=str(e)
            )
    
    def _format_task(self, task: str, context: Dict[str, Any]) -> str:
        """Format task with optional context from previous agents"""
        if not context:
            return task
        
        context_str = "\n\nContext from previous agents:\n"
        for key, value in context.items():
            context_str += f"\n{key}:\n{value}\n"
        
        return task + context_str


# ============================================================================
# SPECIALIST AGENTS
# ============================================================================

class ResearchAgent(SpecialistAgent):
    """Gathers information and facts"""
    
    def __init__(self):
        system_prompt = """You are a research specialist agent.

Your job: Gather relevant information and facts about a topic.

Output format:
- Key facts (bulleted list)
- Relevant data points
- Important context

Be thorough but concise. Focus on facts, not opinions."""
        
        super().__init__(AgentType.RESEARCH, system_prompt)


class AnalysisAgent(SpecialistAgent):
    """Processes data and extracts insights"""
    
    def __init__(self):
        system_prompt = """You are an analysis specialist agent.

Your job: Process information and extract insights.

Output format:
- Key patterns identified
- Important insights
- Recommendations based on data

Be analytical and data-driven. Support conclusions with evidence."""
        
        super().__init__(AgentType.ANALYSIS, system_prompt)


class WritingAgent(SpecialistAgent):
    """Creates polished content"""
    
    def __init__(self):
        system_prompt = """You are a writing specialist agent.

Your job: Create clear, engaging content.

Output format:
- Well-structured prose
- Clear explanations
- Appropriate tone for audience

Be clear and concise. Avoid jargon unless necessary."""
        
        super().__init__(AgentType.WRITING, system_prompt)


# ============================================================================
# ORCHESTRATOR
# ============================================================================

class Orchestrator:
    """
    Central coordinator for specialist agents.
    
    Responsibilities:
    1. Analyze task and determine which agents to use
    2. Decompose complex tasks into subtasks
    3. Execute agents (parallel when possible)
    4. Aggregate results into final output
    """
    
    def __init__(self):
        # Initialize all available agents
        self.agents = {
            AgentType.RESEARCH: ResearchAgent(),
            AgentType.ANALYSIS: AnalysisAgent(),
            AgentType.WRITING: WritingAgent(),
        }
    
    def run(self, task: str) -> str:
        """
        Main orchestrator loop.
        
        1. Plan: Determine which agents to use
        2. Execute: Run agents in appropriate order
        3. Synthesize: Combine results
        """
        print("="*60)
        print("ORCHESTRATOR: Planning task execution")
        print("="*60)
        
        # Step 1: Create execution plan
        plan = self._create_plan(task)
        print(f"\nExecution plan:")
        for i, step in enumerate(plan["steps"], 1):
            print(f"  {i}. {step['agent']} - {step['task'][:60]}...")
        
        # Step 2: Execute plan
        print("\n" + "="*60)
        print("ORCHESTRATOR: Executing plan")
        print("="*60)
        
        results = self._execute_plan(plan)
        
        # Step 3: Synthesize final answer
        print("\n" + "="*60)
        print("ORCHESTRATOR: Synthesizing results")
        print("="*60)
        
        final_answer = self._synthesize_results(task, results)
        
        return final_answer
    
    def _create_plan(self, task: str) -> Dict[str, Any]:
        """
        Determine which agents to use and in what order.
        
        For complex planning, you could use an LLM here.
        For this example, we use simple heuristics.
        """
        # Simple heuristic-based planning
        # In production, you might use an LLM to generate the plan
        
        task_lower = task.lower()
        
        # Determine which agents are needed
        needs_research = any(word in task_lower for word in ["research", "find", "information", "facts", "data"])
        needs_analysis = any(word in task_lower for word in ["analyze", "insights", "patterns", "why", "compare"])
        needs_writing = any(word in task_lower for word in ["write", "draft", "create", "summarize", "explain"])
        
        steps = []
        
        # Default pipeline: research → analyze → write
        if needs_research:
            steps.append({
                "agent": AgentType.RESEARCH,
                "task": f"Research the following: {task}"
            })
        
        if needs_analysis:
            steps.append({
                "agent": AgentType.ANALYSIS,
                "task": f"Analyze the following: {task}",
                "depends_on": [AgentType.RESEARCH] if needs_research else []
            })
        
        if needs_writing:
            steps.append({
                "agent": AgentType.WRITING,
                "task": f"Write a clear explanation of: {task}",
                "depends_on": [AgentType.ANALYSIS] if needs_analysis else ([AgentType.RESEARCH] if needs_research else [])
            })
        
        # If no specific agents identified, use writing agent as default
        if not steps:
            steps.append({
                "agent": AgentType.WRITING,
                "task": task
            })
        
        return {"steps": steps}
    
    def _execute_plan(self, plan: Dict[str, Any]) -> Dict[AgentType, AgentResult]:
        """
        Execute the plan.
        
        For simplicity, this runs sequentially.
        In production, you'd run independent tasks in parallel.
        """
        results = {}
        context = {}
        
        for step in plan["steps"]:
            agent_type = step["agent"]
            task = step["task"]
            
            print(f"\n🤖 Running {agent_type.value.upper()} agent...")
            
            # Get dependencies from context
            deps = step.get("depends_on", [])
            agent_context = {
                dep.value: results[dep].data 
                for dep in deps 
                if dep in results and results[dep].success
            }
            
            # Execute agent
            result = self.agents[agent_type].run(task, agent_context)
            results[agent_type] = result
            
            if result.success:
                print(f"✅ {agent_type.value.upper()} completed")
                print(f"   Tokens used: {result.metadata.get('tokens', 'unknown')}")
            else:
                print(f"❌ {agent_type.value.upper()} failed: {result.error}")
        
        return results
    
    def _synthesize_results(self, original_task: str, results: Dict[AgentType, AgentResult]) -> str:
        """
        Combine agent outputs into a coherent final answer.
        
        This could be as simple as concatenation or as complex as
        using another LLM call to synthesize.
        """
        # Collect successful results
        successful_results = {
            agent_type: result.data 
            for agent_type, result in results.items() 
            if result.success
        }
        
        if not successful_results:
            return "Error: All agents failed to produce results."
        
        # Simple synthesis: combine in order
        sections = []
        
        if AgentType.RESEARCH in successful_results:
            sections.append(f"## Research Findings\n\n{successful_results[AgentType.RESEARCH]}")
        
        if AgentType.ANALYSIS in successful_results:
            sections.append(f"## Analysis\n\n{successful_results[AgentType.ANALYSIS]}")
        
        if AgentType.WRITING in successful_results:
            # If we have a writing agent, use its output as the primary response
            return successful_results[AgentType.WRITING]
        
        # Otherwise, combine all sections
        return "\n\n".join(sections)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Example tasks that benefit from multiple agents
    
    tasks = [
        "Research the current state of AI agents and write a summary of key trends",
        "Analyze the pros and cons of using multiple specialized agents vs a single general agent",
    ]
    
    orchestrator = Orchestrator()
    
    for i, task in enumerate(tasks, 1):
        print("\n" + "="*60)
        print(f"TASK {i}: {task}")
        print("="*60)
        
        result = orchestrator.run(task)
        
        print("\n" + "="*60)
        print("FINAL RESULT")
        print("="*60)
        print(result)
        print("\n")
        
        if i < len(tasks):
            print("\n" + "━"*60 + "\n")
