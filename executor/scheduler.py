import asyncio
from datetime import datetime
from planner.dag import WorkflowDAG, SubtaskNode, SubtaskStatus

class WorkflowScheduler:
    def __init__(self, dag: WorkflowDAG, max_parallel: int = 5, budget_remaining: float = float('inf')):
        self.dag = dag
        self.max_parallel = max_parallel
        self.budget_remaining = budget_remaining
        self.running_count = 0

    def get_next_batch(self) -> list[SubtaskNode]:
        ready = self.dag.get_ready_nodes()
        ready = [n for n in ready if n.estimated_cost <= self.budget_remaining]

        # Use NetworkX for critical path computation
        try:
            import networkx as nx
            G = self.dag.to_networkx()
            
            # Add weighted edges based on estimated_duration_seconds
            for u, v in G.edges():
                G[u][v]['weight'] = G.nodes[v].get('estimated_duration_seconds', 0)
                
            critical_path = nx.dag_longest_path(G, weight='weight')
            critical_set = set(critical_path)
        except Exception:
            # Fallback
            critical_set = set()

        ready.sort(key=lambda n: (
            not n.is_critical,
            n.id not in critical_set,
            n.estimated_duration_seconds,
        ))

        available_slots = self.max_parallel - self.running_count
        return ready[:max(available_slots, 0)]

    def notify_completed(self, node_id: str, cost: float) -> None:
        self.running_count -= 1
        self.budget_remaining -= cost

    def notify_started(self, node_id: str) -> None:
        self.running_count += 1

    def is_workflow_complete(self) -> bool:
        terminal = {SubtaskStatus.COMPLETED, SubtaskStatus.SKIPPED, SubtaskStatus.CANCELLED}
        return all(n.status in terminal for n in self.dag.nodes.values())

    def is_workflow_stuck(self) -> bool:
        return (
            not self.is_workflow_complete()
            and len(self.get_next_batch()) == 0
            and self.running_count == 0
        )
