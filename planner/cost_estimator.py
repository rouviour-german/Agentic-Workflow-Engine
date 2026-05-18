from pydantic import BaseModel
from .dag import WorkflowDAG

class Optimization(BaseModel):
    description: str
    potential_savings: float

class CostEstimate(BaseModel):
    estimated_llm_cost: float
    estimated_tool_cost: float
    retry_overhead: float
    replan_overhead: float
    total_estimated: float
    budget_remaining: float | None
    is_within_budget: bool
    optimizations: list[Optimization] = []

class CostEstimator:
    def estimate(self, dag: WorkflowDAG, budget: float | None = None) -> CostEstimate:
        llm_cost = sum(n.estimated_cost for n in dag.nodes.values() if n.subtask_type in ["llm_generation", "llm_analysis"])
        tool_cost = sum(n.estimated_cost for n in dag.nodes.values() if n.subtask_type == "tool_call")
        
        retry_overhead = (llm_cost + tool_cost) * 0.2
        replan_overhead = (llm_cost + tool_cost) * 0.1
        total = llm_cost + tool_cost + retry_overhead + replan_overhead
        
        return CostEstimate(
            estimated_llm_cost=llm_cost,
            estimated_tool_cost=tool_cost,
            retry_overhead=retry_overhead,
            replan_overhead=replan_overhead,
            total_estimated=total,
            budget_remaining=(budget - total) if budget else None,
            is_within_budget=(total <= budget) if budget else True
        )
