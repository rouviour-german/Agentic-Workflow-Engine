from datetime import datetime
from planner.dag import WorkflowDAG, SubtaskNode
from planner.cost_estimator import CostEstimate
import sys

class TrackingEvent:
    def __init__(self, type: str, data: dict):
        self.timestamp = datetime.now()
        self.type = type
        self.data = data

class ExecutionTrace:
    pass

class WorkflowTracker:
    def __init__(self):
        self.events: list[TrackingEvent] = []
        self.start_time: datetime = datetime.now()

    def log_subtask_start(self, node: SubtaskNode) -> None:
        self.events.append(TrackingEvent("start", {"node_id": node.id}))
        print(f"[{self._elapsed():.1f}s] 🚀 Started: {node.id}")

    def log_subtask_complete(self, node: SubtaskNode) -> None:
        self.events.append(TrackingEvent("complete", {"node_id": node.id}))
        print(f"[{self._elapsed():.1f}s] ✅ {node.id} completed (${node.actual_cost:.3f}, {node.actual_tokens} tokens)")

    def log_subtask_fail(self, node: SubtaskNode) -> None:
        self.events.append(TrackingEvent("fail", {"node_id": node.id, "error": node.error}))
        print(f"[{self._elapsed():.1f}s] ❌ {node.id} failed: {node.error}")

    def log_retry(self, node: SubtaskNode) -> None:
        self.events.append(TrackingEvent("retry", {"node_id": node.id, "attempt": node.attempts}))
        print(f"[{self._elapsed():.1f}s] 🔄 Retrying: {node.id} (Attempt {node.attempts}/{node.max_retries})")

    def log_replan(self, node: SubtaskNode, new_dag: WorkflowDAG) -> None:
        self.events.append(TrackingEvent("replan", {"node_id": node.id}))
        print(f"[{self._elapsed():.1f}s] 🧠 Replanning due to failure of: {node.id}")

    def log_skip(self, node: SubtaskNode) -> None:
        self.events.append(TrackingEvent("skip", {"node_id": node.id}))
        print(f"[{self._elapsed():.1f}s] ⏭️ Skipped: {node.id}")

    def log_phase(self, phase: str) -> None:
        self.events.append(TrackingEvent("phase", {"phase": phase}))
        if phase == "executing":
            print("\n▶ Executing...\n")
        else:
            print(f"\n🧠 Phase: {phase.capitalize()}...")

    def log_cost_estimate(self, estimate: CostEstimate) -> None:
        self.events.append(TrackingEvent("estimate", {"estimate": estimate.total_estimated}))
        print(f"\n💰 Cost estimate: ${estimate.total_estimated:.2f} (Within budget: {estimate.is_within_budget})")

    def log_validation_issues(self, issues: list) -> None:
        for issue in issues:
            print(f"⚠️ Validation {issue.severity}: {issue.message} - {issue.suggestion}")

    def _elapsed(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    def get_trace(self) -> list[dict]:
        return [{"timestamp": e.timestamp.isoformat(), "type": e.type, "data": e.data} for e in self.events]
