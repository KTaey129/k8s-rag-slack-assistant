"""Internal auth between n8n and FastAPI.

Slack's HMAC request signature is computed over the exact raw request body
it sent. Once n8n receives that webhook and re-serializes the payload before
forwarding it to FastAPI, the raw body no longer matches — so verifying
Slack's signature has to happen at the edge (in n8n, facing the internet),
not here. FastAPI instead trusts a shared secret header, since this endpoint
is only reachable from n8n on the internal docker/k8s network, never
directly from the internet.
"""

import hmac
import os

from fastapi import Header, HTTPException

INTERNAL_SHARED_SECRET = os.environ.get("INTERNAL_SHARED_SECRET", "")


def require_internal_secret(x_internal_secret: str = Header(default="")) -> None:
    if not INTERNAL_SHARED_SECRET:
        raise HTTPException(status_code=500, detail="INTERNAL_SHARED_SECRET not configured")
    if not hmac.compare_digest(x_internal_secret, INTERNAL_SHARED_SECRET):
        raise HTTPException(status_code=401, detail="invalid internal secret")
