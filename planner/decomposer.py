import json
from llm.client import DeepSeekClient
from llm.config import config
from .dag import WorkflowDAG, SubtaskNode
from typing import Optional

class GoalDecomposer:
    def __init__(self):
        self.llm = DeepSeekClient()

    async def decompose(self, goal: str, available_tools: list[str] = None, budget: Optional[float] = None, constraints: str = "") -> WorkflowDAG:
        available_tools = available_tools or []
        
        system_prompt = """You are a workflow planning expert. Decompose the goal into a DAG (Directed Acyclic Graph) of subtasks.
RULES:
1. Each subtask must be ATOMIC.
2. Identify PARALLEL subtasks.
3. Every subtask must have a clear OUTPUT.
4. Provide dependencies. NO CYCLES.
5. Create input_mapping linking dependencies to prompts.
6. Estimate cost and duration (assume $0.001 per token).

Respond strictly with valid JSON.
Format required:
{
    "dag": {
        "nodes": [
            {
                "id": "...",
                "name": "...",
                "description": "...",
                "subtask_type": "llm_generation|llm_analysis|tool_call|human_approval|aggregation",
                "dependencies": [],
                "input_mapping": {},
                "prompt_template": "...",
                "estimated_cost": 0.05,
                "estimated_duration_seconds": 10,
                "is_critical": true
            }
        ]
    }
}"""
        
        prompt = f"GOAL: {goal}\nAVAILABLE TOOLS: {available_tools}\nBUDGET: ${budget}\nCONSTRAINTS: {constraints}"
        
        response = await self.llm.chat(
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
            model=config.planner_model,
            temperature=config.planner_temperature,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.text)
        nodes_dict = {}
        for node_data in data["dag"]["nodes"]:
            # Clean up missing optional fields
            node_data.setdefault("model", config.executor_model)
            node = SubtaskNode(**node_data)
            nodes_dict[node.id] = node
            
        return WorkflowDAG(goal=goal, nodes=nodes_dict)
