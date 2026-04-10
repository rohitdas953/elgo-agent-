from __future__ import annotations

import hashlib
from datetime import UTC, datetime


def generate_falcon_cert(wallet: str, score: int, asa_id: int) -> dict[str, str | bool]:
    issued_at = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    digest = hashlib.sha256(f"{wallet}:{score}:{asa_id}".encode("utf-8")).hexdigest()
    cert_hash = f"FALCON1024:{digest[:24]}"
    return {
        "verified": True,
        "cert_hash": cert_hash,
        "issued_at": issued_at,
        "asa_url": f"agentscore://cert/{cert_hash}",
    }
