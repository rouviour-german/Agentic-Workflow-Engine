import asyncio
from pydantic import BaseModel
from typing import Optional
from llm.client import DeepSeekClient
from planner.dag import WorkflowDAG, SubtaskNode, SubtaskType
from executor.dependency_resolver import DependencyResolver

class SubtaskResult(BaseModel):
    node_id: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    tokens_used: int = 0
    cost: float = 0.0
    duration_seconds: float = 0.0

class ParallelExecutor:
    def __init__(self):
        self.llm = DeepSeekClient()

    async def execute_batch(self, nodes: list[SubtaskNode], dag: WorkflowDAG, dependency_resolver: DependencyResolver) -> list[SubtaskResult]:
        tasks = []
        for node in nodes:
            try:
                inputs = dependency_resolver.resolve_inputs(node, dag)
                prompt = dependency_resolver.render_prompt(node, inputs)
            except Exception as e:
                # Dependency resolution failure
                subtask_result = SubtaskResult(
                    node_id=node.id, 
                    success=False, 
                    error=str(e), 
                    error_type=type(e).__name__
                )
                tasks.append(asyncio.sleep(0.001, result=subtask_result)) # return fake task
                continue
                
            task = asyncio.create_task(self._execute_with_timeout(node, prompt))
            tasks.append((node, task))
            
        real_tasks = [t for n, t in tasks if isinstance(n, SubtaskNode)]
        fake_tasks = [t for t in tasks if not isinstance(t, tuple)]
        
        results = []
        if real_tasks:
            real_results = await asyncio.gather(*real_tasks, return_exceptions=True)
            for (node, _), result in zip([t for t in tasks if isinstance(t, tuple)], real_results):
                if isinstance(result, Exception):
                    results.append(SubtaskResult(
                        node_id=node.id,
                        success=False,
                        error=str(result),
                        error_type=type(result).__name__,
                    ))
                else:
                    results.append(result)
                    
        for ft in fake_tasks:
            results.append(await ft)

        return results

    async def _execute_with_timeout(self, node: SubtaskNode, prompt: str) -> SubtaskResult:
        try:
            result = await asyncio.wait_for(
                self._execute_subtask(node, prompt),
                timeout=node.timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            return SubtaskResult(
                node_id=node.id,
                success=False,
                error=f"Subtask timed out after {node.timeout_seconds}s",
                error_type="TimeoutError"
            )

    async def _execute_subtask(self, node: SubtaskNode, prompt: str) -> SubtaskResult:
        if node.subtask_type in (SubtaskType.LLM_GENERATION, SubtaskType.LLM_ANALYSIS):
            return await self._execute_llm(node, prompt)
        elif node.subtask_type == SubtaskType.TOOL_CALL:
            # Fake tool executor for now
            return SubtaskResult(node_id=node.id, success=True, output=f"Simulated tool call: {node.tool_name}", duration_seconds=1.0)
        elif node.subtask_type in (SubtaskType.HUMAN_APPROVAL, SubtaskType.HUMAN_INPUT):
            # We handle human interventions upstream, but if directly executed here we fake success or raise
            return SubtaskResult(node_id=node.id, success=True, output="Simulated human approval", duration_seconds=1.0)
        elif node.subtask_type == SubtaskType.AGGREGATION:
            return await self._execute_llm(node, prompt)
        
        return SubtaskResult(node_id=node.id, success=False, error=f"Unsupported type {node.subtask_type}", error_type="UnsupportedTypeError")

    async def _execute_llm(self, node: SubtaskNode, prompt: str) -> SubtaskResult:
        response = await self.llm.chat(
            system=f"You are completing a subtask. Subtask: {node.description}",
            messages=[{"role": "user", "content": prompt}],
            model=node.model,
            temperature=node.temperature,
            max_tokens=node.max_tokens,
        )
        return SubtaskResult(
            node_id=node.id,
            success=True,
            output=response.text,
            tokens_used=response.usage["total_tokens"],
            cost=response.usage["estimated_cost"],
            duration_seconds=response.duration,
        )
