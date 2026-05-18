import json
from typing import Dict
from llm.client import DeepSeekClient
from llm.config import config
from .dag import WorkflowDAG, SubtaskNode

class DynamicReplanner:
    def __init__(self):
        self.llm = DeepSeekClient()

    async def replan(self, dag: WorkflowDAG, failed_node: SubtaskNode, error: str, completed_results: Dict[str, str]) -> WorkflowDAG:
        system = """You are a workflow planning expert. A subtask in a workflow DAG failed.
Create an ALTERNATIVE plan for the remaining work that:
1. Reuses completed results.
2. Works around the failed subtask.
3. Achieves the original goal.

Output format must be JSON returning ONLY the replacement nodes in the same format:
{
    "replacement_nodes": [ ... ]
}"""

        prompt = f"""
ORIGINAL GOAL: {dag.goal}
COMPLETED SUBTASKS: {list(completed_results.keys())}
FAILED SUBTASK: {failed_node.id} ({failed_node.description})
ERROR: {error}
"""

        response = await self.llm.chat(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            model=config.planner_model,
            temperature=config.planner_temperature,
            response_format={"type": "json_object"}
        )

        data = json.loads(response.text)
        
        # Merge replacement nodes into a new DAG
        new_nodes = dag.nodes.copy()
        affected = [n.id for n in dag.get_affected_downstream(failed_node.id)]
        
        for n_id in affected + [failed_node.id]:
            if n_id in new_nodes:
                del new_nodes[n_id]
                
        for node_data in data.get("replacement_nodes", []):
            node_data.setdefault("model", config.executor_model)
            node = SubtaskNode(**node_data)
            new_nodes[node.id] = node
            
        new_dag = WorkflowDAG(goal=dag.goal, nodes=new_nodes, metadata=dag.metadata)
        return new_dag
