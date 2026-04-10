from __future__ import annotations

import os

from dotenv import load_dotenv
from fastmcp import FastMCP

from database import init_db
from main import build_agent_details
from services.score import ScoreService

load_dotenv()
init_db()

server = FastMCP(
    name="AgentScore MCP Server",
    instructions="Tools to fetch AgentScore trust and x402 policy signals.",
)
score_service = ScoreService()


@server.tool(name="get_agent_score")
def get_agent_score(agent_wallet: str) -> dict:
    details = build_agent_details(agent_wallet)
    recommendation = score_service.recommendation_for_tier(details.tier)
    return {
        "agent_wallet": details.wallet,
        "alias": details.alias,
        "agent_score": details.score,
        "trust_tier": details.tier,
        "x402_access_policy": details.x402_policy.model_dump(mode="json"),
        "score_components": details.score_components.model_dump(mode="json"),
        "falcon_cert": details.falcon_cert.model_dump(mode="json"),
        "recommendation": recommendation,
        "algorand_explorer": details.algorand_explorer_url,
    }


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8001"))

    if transport == "streamable-http":
        server.run(transport="streamable-http", host=host, port=port, path="/mcp")
    elif transport == "sse":
        server.run(transport="sse", host=host, port=port, path="/sse")
    else:
        server.run(transport="stdio")
