from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4
from typing import Literal

class SubtaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"
    AWAITING_HUMAN = "awaiting_human"
    CANCELLED = "cancelled"

class SubtaskType(str, Enum):
    LLM_GENERATION = "llm_generation"
    LLM_ANALYSIS = "llm_analysis"
    TOOL_CALL = "tool_call"
    HUMAN_APPROVAL = "human_approval"
    HUMAN_INPUT = "human_input"
    CONDITIONAL = "conditional"
    AGGREGATION = "aggregation"
    TRANSFORM = "transform"

class SubtaskNode(BaseModel):
    id: str
    name: str
    description: str
    subtask_type: SubtaskType
    dependencies: list[str] = []
    input_mapping: dict[str, str] = {}
    
    prompt_template: str = ""
    tool_name: str = ""
    tool_args: dict = {}
    approval_message: str = ""
    condition: str = ""
    branches: dict[str, list[str]] = {}

    model: str = "deepseek-chat"
    temperature: float = 0.6
    max_tokens: int = 4096
    estimated_cost: float = 0.0
    estimated_duration_seconds: float = 5.0
    max_retries: int = 3
    timeout_seconds: int = 60
    is_critical: bool = True

    status: SubtaskStatus = SubtaskStatus.PENDING
    output: str | None = None
    error: str | None = None
    attempts: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    actual_cost: float = 0.0
    actual_tokens: int = 0

class WorkflowDAG(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    goal: str
    nodes: dict[str, SubtaskNode]
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = {}

    def get_node(self, node_id: str) -> SubtaskNode:
        if node_id not in self.nodes:
            raise ValueError(f"Node '{node_id}' not found in DAG")
        return self.nodes[node_id]

    def get_dependencies(self, node_id: str) -> list[SubtaskNode]:
        node = self.get_node(node_id)
        return [self.get_node(dep_id) for dep_id in node.dependencies]

    def get_dependents(self, node_id: str) -> list[SubtaskNode]:
        return [n for n in self.nodes.values() if node_id in n.dependencies]

    def get_ready_nodes(self) -> list[SubtaskNode]:
        ready = []
        for node in self.nodes.values():
            if node.status != SubtaskStatus.PENDING:
                continue
            deps = self.get_dependencies(node.id)
            if all(d.status == SubtaskStatus.COMPLETED for d in deps):
                ready.append(node)
        return ready

    def get_affected_downstream(self, failed_node_id: str) -> list[SubtaskNode]:
        affected = []
        queue = [failed_node_id]
        visited = set()
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for dependent in self.get_dependents(current):
                affected.append(dependent)
                queue.append(dependent.id)
        return affected

    def topological_sort(self) -> list[str]:
        import networkx as nx
        G = nx.DiGraph()
        for node_id, node in self.nodes.items():
            G.add_node(node_id)
            for dep_id in node.dependencies:
                G.add_edge(dep_id, node_id)
        if not nx.is_directed_acyclic_graph(G):
            cycles = list(nx.simple_cycles(G))
            raise ValueError(f"DAG has cycles: {cycles}")
        return list(nx.topological_sort(G))
