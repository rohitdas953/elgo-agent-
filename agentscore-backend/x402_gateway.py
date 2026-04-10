from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from x402.http import HTTPFacilitatorClient
from x402.http.middleware.fastapi import payment_middleware_from_config

from database import init_db
from main import build_agent_details
from services.score import ScoreService

load_dotenv()
init_db()

app = FastAPI(title="AgentScore x402 Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

score_service = ScoreService()

pay_to = os.getenv(
    "X402_PAY_TO",
    "0x0000000000000000000000000000000000000000",
)
network = os.getenv("X402_NETWORK", "base-sepolia")
price = os.getenv("X402_PRICE", "0.001")
facilitator_url = os.getenv("X402_FACILITATOR_URL", "https://x402.org/facilitator")

routes = {
    "GET /x402/agent-score/*": {
        "accepts": [
            {
                "scheme": "exact",
                "network": network,
                "maxTimeoutSeconds": 120,
                "resource": "https://agentscore.local/x402/agent-score",
                "description": "Paid AgentScore query",
                "payTo": pay_to,
                "price": price,
                "extra": {"asset": "usdc"},
            }
        ]
    }
}

facilitator = HTTPFacilitatorClient(config={"url": facilitator_url})


@app.middleware("http")
async def x402_middleware(request, call_next):
    middleware = payment_middleware_from_config(
        routes=routes, facilitator_client=facilitator
    )
    return await middleware(request, call_next)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/x402/agent-score/{wallet}")
def paid_agent_score(wallet: str) -> dict:
    details = build_agent_details(wallet)
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
    import uvicorn

    uvicorn.run(
        "x402_gateway:app",
        host="0.0.0.0",
        port=int(os.getenv("X402_PORT", "8002")),
        reload=True,
    )
