import os
from dotenv import load_dotenv

load_dotenv()

class EngineConfig:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.max_parallel = int(os.getenv("MAX_PARALLEL_SUBTASKS", "5"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.max_replans = int(os.getenv("MAX_REPLANS", "2"))
        self.total_budget = float(os.getenv("TOTAL_BUDGET_DOLLARS", "5.00"))
        self.require_approval_above_cost = float(os.getenv("REQUIRE_APPROVAL_ABOVE_COST", "1.00"))
        self.planner_model = os.getenv("PLANNER_MODEL", "deepseek-chat")
        self.planner_temperature = float(os.getenv("PLANNER_TEMPERATURE", "0.1"))
        self.executor_model = os.getenv("EXECUTOR_MODEL", "deepseek-chat")
        self.executor_temperature = float(os.getenv("EXECUTOR_TEMPERATURE", "0.6"))

config = EngineConfig()
