from app.agents.tools import (
    get_sales_summary,
    get_inventory_status,
    detect_anomalies,
    get_forecast_accuracy
)
from app.core.logger import get_logger
import json

logger = get_logger(__name__)

MCP_TOOLS = [
    {
        "name": "get_sales_summary",
        "description": "Get sales revenue and units sold by category for a given number of days",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 7)",
                    "default": 7
                }
            }
        }
    },
    {
        "name": "get_inventory_status",
        "description": "Get current inventory levels and alerts for items below reorder point",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "detect_anomalies",
        "description": "Detect anomalies in sales by comparing recent 7 days vs previous 7 days",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_forecast_accuracy",
        "description": "Get ML forecast accuracy metrics and recent forecast vs actual comparisons",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]

TOOL_FUNCTIONS = {
    "get_sales_summary": get_sales_summary,
    "get_inventory_status": get_inventory_status,
    "detect_anomalies": detect_anomalies,
    "get_forecast_accuracy": get_forecast_accuracy,
}

def execute_mcp_tool(tool_name: str, parameters: dict = None) -> dict:
    if tool_name not in TOOL_FUNCTIONS:
        return {"error": f"Tool {tool_name} not found"}
    func = TOOL_FUNCTIONS[tool_name]
    try:
        if parameters:
            result = func(**parameters)
        else:
            result = func()
        logger.info(f"MCP tool executed: {tool_name}")
        return result
    except Exception as e:
        logger.error(f"MCP tool {tool_name} failed: {e}")
        return {"error": str(e)}

def get_mcp_tools_list() -> list:
    return MCP_TOOLS

def mcp_claude_query(user_query: str) -> dict:
    from app.services.llm import client, MODEL
    import anthropic
    logger.info(f"MCP Claude query: {user_query}")
    tools = [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["parameters"]
        }
        for tool in MCP_TOOLS
    ]
    messages = [{"role": "user", "content": user_query}]
    tool_results = []
    max_iterations = 5
    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            tools=tools,
            messages=messages
        )
        if response.stop_reason == "end_turn":
            final_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    final_text = block.text
            return {
                "query": user_query,
                "answer": final_text,
                "tools_used": [t["tool_name"] for t in tool_results],
                "tool_results": tool_results,
                "iterations": iteration
            }
        if response.stop_reason == "tool_use":
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            tool_use_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_result = execute_mcp_tool(
                        block.name,
                        block.input if block.input else {}
                    )
                    tool_results.append({
                        "tool_name": block.name,
                        "parameters": block.input,
                        "result": tool_result
                    })
                    tool_use_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(tool_result)
                    })
            messages.append({
                "role": "user",
                "content": tool_use_results
            })
    return {
        "query": user_query,
        "answer": "Max iterations reached",
        "tools_used": [t["tool_name"] for t in tool_results],
        "iterations": iteration
    }