import asyncio
from datetime import datetime
from pydantic import BaseModel
from llm.config import EngineConfig, config
from planner.decomposer import GoalDecomposer
from planner.validator import DAGValidator
from planner.cost_estimator import CostEstimator
from planner.replanner import DynamicReplanner
from planner.dag import SubtaskStatus, WorkflowDAG
from executor.scheduler import WorkflowScheduler
from executor.parallel import ParallelExecutor
from executor.dependency_resolver import DependencyResolver
from failure.strategy_selector import FailureStrategySelector, FailureStrategy
from human_loop.approval_gate import ApprovalGate, ApprovalContext
from monitoring.tracker import WorkflowTracker

class WorkflowResult(BaseModel):
    success: bool
    reason: str | None = None
    goal: str | None = None
    output: str | None = None
    dag: dict | None = None
    execution_trace: list[dict] | None = None
    total_cost: float = 0.0
    total_tokens: int = 0
    total_duration: float = 0.0
    subtask_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    replan_count: int = 0

class WorkflowEngine:
    def __init__(self, cfg: EngineConfig = None):
        self.config = cfg or config
        self.decomposer = GoalDecomposer()
        self.validator = DAGValidator()
        self.cost_estimator = CostEstimator()
        self.scheduler = None
        self.executor = ParallelExecutor()
        self.resolver = DependencyResolver()
        self.failure_handler = FailureStrategySelector()
        self.replanner = DynamicReplanner()
        self.tracker = WorkflowTracker()
        self.approval = ApprovalGate()

    async def run(self, goal: str, budget: float | None = None, require_approval: bool = True) -> WorkflowResult:
        budget = budget or self.config.total_budget

        self.tracker.log_phase("planning")
        dag = await self.decomposer.decompose(goal, budget=budget)

        self.tracker.log_phase("validating")
        validation = self.validator.validate(dag, budget=budget)
        if not validation.is_valid:
            self.tracker.log_validation_issues(validation.issues)
            return WorkflowResult(success=False, reason="DAG Validation Failed", dag=dag.model_dump())

        estimate = self.cost_estimator.estimate(dag, budget=budget)
        self.tracker.log_cost_estimate(estimate)

        if require_approval and estimate.total_estimated > self.config.require_approval_above_cost:
            ctx = ApprovalContext(
                workflow_goal=goal,
                message=f"Estimated cost: ${estimate.total_estimated:.2f}. Subtasks: {len(dag.nodes)}. Proceed?",
                cost_so_far=0.0,
                total_budget=budget
            )
            decision = await self.approval.request_approval(ctx)
            if decision.action != "approve":
                return WorkflowResult(success=False, reason="User declined execution", dag=dag.model_dump())

        self.tracker.log_phase("executing")
        self.scheduler = WorkflowScheduler(dag=dag, max_parallel=self.config.max_parallel, budget_remaining=budget)

        replan_count = 0

        while not self.scheduler.is_workflow_complete():
            if self.scheduler.is_workflow_stuck():
                if replan_count < self.config.max_replans:
                    # Generic replan for stuck state could be complex, simple abort for now if stuck and not fail driven
                    break
                else:
                    break

            batch = self.scheduler.get_next_batch()
            if not batch:
                await asyncio.sleep(0.5)
                continue

            for node in batch:
                node.status = SubtaskStatus.RUNNING
                node.started_at = datetime.now()
                self.scheduler.notify_started(node.id)
                self.tracker.log_subtask_start(node)

            results = await self.executor.execute_batch(batch, dag, self.resolver)

            for result in results:
                node = dag.get_node(result.node_id)
                
                if result.success:
                    node.status = SubtaskStatus.COMPLETED
                    node.output = result.output
                    node.completed_at = datetime.now()
                    node.actual_cost = result.cost
                    node.actual_tokens = result.tokens_used
                    self.scheduler.notify_completed(node.id, result.cost)
                    self.tracker.log_subtask_complete(node)
                else:
                    node.attempts += 1
                    node.error = result.error
                    self.tracker.log_subtask_fail(node)
                    
                    strategy = self.failure_handler.select_strategy(node, result.error, result.error_type, dag)
                    
                    if strategy == FailureStrategy.RETRY:
                        if node.attempts < node.max_retries:
                            node.status = SubtaskStatus.PENDING
                            self.tracker.log_retry(node)
                        else:
                            strategy = FailureStrategy.REPLAN

                    if strategy == FailureStrategy.REPLAN:
                        if replan_count < self.config.max_replans:
                            node.status = SubtaskStatus.FAILED
                            completed_results = {n.id: n.output for n in dag.nodes.values() if n.status == SubtaskStatus.COMPLETED}
                            dag = await self.replanner.replan(dag, node, result.error, completed_results)
                            self.scheduler = WorkflowScheduler(dag=dag, max_parallel=self.config.max_parallel, budget_remaining=self.scheduler.budget_remaining)
                            replan_count += 1
                            self.tracker.log_replan(node, dag)
                        else:
                            strategy = FailureStrategy.ESCALATE

                    if strategy == FailureStrategy.ESCALATE:
                        node.status = SubtaskStatus.FAILED
                        human_decision = await self.approval.request_failure_decision(node, result.error)
                        if human_decision.action == "skip":
                            strategy = FailureStrategy.SKIP
                        elif human_decision.action == "retry":
                            node.attempts = 0
                            node.status = SubtaskStatus.PENDING
                            self.tracker.log_retry(node)
                        else:
                            return WorkflowResult(success=False, reason="Escalated failure cancelled by user", dag=dag.model_dump())
                    
                    if strategy == FailureStrategy.SKIP:
                        node.status = SubtaskStatus.SKIPPED
                        for downstream in dag.get_affected_downstream(node.id):
                            if not downstream.is_critical:
                                downstream.status = SubtaskStatus.SKIPPED
                        self.tracker.log_skip(node)
                        self.scheduler.notify_completed(node.id, 0.0)

        self.tracker.log_phase("aggregating")
        terminal_nodes = [n for n in dag.nodes.values() if not dag.get_dependents(n.id) and n.status == SubtaskStatus.COMPLETED]
        final_output = "\n\n".join([f"=== {n.name} ===\n{n.output}" for n in terminal_nodes])

        completed = sum(1 for n in dag.nodes.values() if n.status == SubtaskStatus.COMPLETED)
        failed = sum(1 for n in dag.nodes.values() if n.status == SubtaskStatus.FAILED)
        is_success = failed == 0 and completed > 0

        return WorkflowResult(
            success=is_success,
            goal=goal,
            output=final_output,
            dag=dag.model_dump(),
            execution_trace=self.tracker.get_trace(),
            total_cost=sum(n.actual_cost for n in dag.nodes.values()),
            total_tokens=sum(n.actual_tokens for n in dag.nodes.values()),
            total_duration=(datetime.now() - dag.created_at).total_seconds(),
            subtask_count=len(dag.nodes),
            completed_count=completed,
            failed_count=failed,
            replan_count=replan_count,
        )
