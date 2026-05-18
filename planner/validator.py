from pydantic import BaseModel
from typing import Literal
from .dag import WorkflowDAG, SubtaskNode

class ValidationIssue(BaseModel):
    severity: Literal["error", "warning", "info"]
    node_id: str | None
    message: str
    suggestion: str

class ValidationResult(BaseModel):
    is_valid: bool
    issues: list[ValidationIssue]

class DAGValidator:
    def validate(self, dag: WorkflowDAG, budget: float | None = None, max_duration: float | None = None) -> ValidationResult:
        issues = []
        issues.extend(self._check_cycles(dag))
        issues.extend(self._check_missing_dependencies(dag))
        issues.extend(self._check_input_mappings(dag))
        
        return ValidationResult(
            is_valid=all(i.severity != "error" for i in issues),
            issues=issues
        )
        
    def _check_cycles(self, dag: WorkflowDAG) -> list[ValidationIssue]:
        issues = []
        try:
            dag.topological_sort()
        except ValueError as e:
            issues.append(ValidationIssue(severity="error", node_id=None, message=str(e), suggestion="Remove cycle in dependencies"))
        return issues

    def _check_missing_dependencies(self, dag: WorkflowDAG) -> list[ValidationIssue]:
        issues = []
        for node_id, node in dag.nodes.items():
            for dep in node.dependencies:
                if dep not in dag.nodes:
                    issues.append(ValidationIssue(severity="error", node_id=node_id, message=f"Missing dependency: {dep}", suggestion="Add node or remove dependency"))
        return issues
        
    def _check_input_mappings(self, dag: WorkflowDAG) -> list[ValidationIssue]:
        issues = []
        for node_id, node in dag.nodes.items():
            for input_key, source_ref in node.input_mapping.items():
                if "." not in source_ref:
                    issues.append(ValidationIssue(severity="error", node_id=node_id, message=f"Invalid mapping format {source_ref}", suggestion="Use node_id.output format"))
                    continue
                src_id, field = source_ref.rsplit(".", 1)
                if src_id not in dag.nodes:
                    issues.append(ValidationIssue(severity="error", node_id=node_id, message=f"Mapping reference missing node {src_id}", suggestion="Fix reference"))
                elif src_id not in node.dependencies:
                    issues.append(ValidationIssue(severity="error", node_id=node_id, message=f"Mapping source {src_id} not in dependencies", suggestion="Add dependency"))
        return issues
