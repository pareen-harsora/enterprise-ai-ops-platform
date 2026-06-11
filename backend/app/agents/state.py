from typing import TypedDict, List, Optional
from datetime import datetime

class AgentState(TypedDict):
    messages: List[str]
    current_step: str
    data_collected: dict
    anomalies_found: List[dict]
    recommendations: List[str]
    report: Optional[str]
    iteration_count: int
    should_continue: bool
    error: Optional[str]