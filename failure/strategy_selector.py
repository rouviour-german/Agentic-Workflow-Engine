from enum import Enum
from planner.dag import SubtaskNode, WorkflowDAG

class FailureStrategy(str, Enum):
    RETRY = "retry"
    REPLAN = "replan"
    ESCALATE = "escalate"
    SKIP = "skip"

class FailureStrategySelector:
    TRANSIENT_ERRORS = {
        "TimeoutError", "ConnectionError", "RateLimitError",
        "ServiceUnavailableError", "APIError"
    }
    STRUCTURAL_ERRORS = {
        "InvalidInputError", "ToolNotFoundError", "AuthenticationError",
        "ValidationError", "PermissionError", "DependencyNotReadyError", "MissingInputError"
    }

    def select_strategy(self, node: SubtaskNode, error: str, error_type: str, dag: WorkflowDAG) -> FailureStrategy:
        if error_type in self.TRANSIENT_ERRORS and node.attempts < node.max_retries:
            return FailureStrategy.RETRY

        if not node.is_critical:
            downstream_critical = any(d.is_critical for d in dag.get_affected_downstream(node.id))
            if not downstream_critical:
                return FailureStrategy.SKIP

        if error_type in self.STRUCTURAL_ERRORS or node.attempts >= node.max_retries:
            return FailureStrategy.REPLAN

        return FailureStrategy.REPLAN
