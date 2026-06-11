from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.nodes import (
    collect_sales_data,
    collect_inventory_data,
    detect_anomaly_node,
    generate_recommendations,
    generate_report,
    should_continue_check
)
from app.core.logger import get_logger

logger = get_logger(__name__)

def build_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("collect_sales", collect_sales_data)
    workflow.add_node("collect_inventory", collect_inventory_data)
    workflow.add_node("detect_anomalies", detect_anomaly_node)
    workflow.add_node("generate_recommendations", generate_recommendations)
    workflow.add_node("generate_report", generate_report)
    workflow.set_entry_point("collect_sales")
    workflow.add_edge("collect_sales", "collect_inventory")
    workflow.add_edge("collect_inventory", "detect_anomalies")
    workflow.add_edge("detect_anomalies", "generate_recommendations")
    workflow.add_edge("generate_recommendations", "generate_report")
    workflow.add_edge("generate_report", END)
    return workflow.compile()

def run_ops_agent() -> dict:
    logger.info("Starting autonomous operations agent")
    graph = build_agent_graph()
    initial_state = AgentState(
        messages=[],
        current_step="starting",
        data_collected={},
        anomalies_found=[],
        recommendations=[],
        report=None,
        iteration_count=0,
        should_continue=True,
        error=None
    )
    try:
        final_state = graph.invoke(initial_state)
        logger.info(
            f"Agent completed in {final_state['iteration_count']} steps"
        )
        return {
            "status": "completed",
            "steps_taken": final_state["iteration_count"],
            "agent_log": final_state["messages"],
            "anomalies_found": final_state["anomalies_found"],
            "recommendations": final_state["recommendations"],
            "report": final_state["report"],
            "data_collected": final_state["data_collected"]
        }
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }