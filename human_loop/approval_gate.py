from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal
from planner.dag import SubtaskNode

class HumanDecision(BaseModel):
    action: Literal["approve", "modify", "skip", "cancel", "retry", "custom"]
    modifications: dict = {}
    custom_instruction: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)

class ApprovalContext(BaseModel):
    workflow_goal: str
    message: str
    cost_so_far: float
    total_budget: float

class ApprovalGate:
    async def request_approval(self, context: ApprovalContext) -> HumanDecision:
        print("\n" + "="*50)
        print("🚦 APPROVAL REQUIRED")
        print(f"Workflow: {context.workflow_goal}")
        print(f"Cost so far: ${context.cost_so_far:.2f} / ${context.total_budget:.2f}")
        print(f"REASON: {context.message}")
        print("="*50)
        print("[1] ✅ Approve and continue")
        print("[2] ⏭️ Skip this subtask")
        print("[3] ❌ Cancel workflow")
        choice = input("Select an option (1-3): ").strip()
        
        if choice == "2":
            return HumanDecision(action="skip")
        elif choice == "3":
            return HumanDecision(action="cancel")
        else:
            return HumanDecision(action="approve")

    async def request_failure_decision(self, node: SubtaskNode, error: str) -> HumanDecision:
        print("\n" + "="*50)
        print("⚠️ FAILURE ESCALATION")
        print(f"Subtask '{node.id}' failed")
        print(f"Error: {error}")
        print("="*50)
        print("[1] 🔄 Retry again")
        print("[2] ⏭️ Skip this subtask")
        print("[3] ❌ Cancel workflow")
        choice = input("Select an option (1-3): ").strip()
        
        if choice == "2":
            return HumanDecision(action="skip")
        elif choice == "3":
            return HumanDecision(action="cancel")
        else:
            return HumanDecision(action="retry")
