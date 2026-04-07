"""Light concurrent GET /health against a running API (Phase 6 smoke)."""

from __future__ import annotations

import asyncio
import os
import sys

import httpx


async def run(url: str, n: int = 50) -> None:
    async with httpx.AsyncClient() as client:

        async def one(i: int) -> int:
            r = await client.get(f"{url}/health")
            return r.status_code

        codes = await asyncio.gather(*[one(i) for i in range(n)])
    ok = sum(1 for c in codes if c == 200)
    print(f"requests={n} status_200={ok}")
    if ok != n:
        sys.exit(1)


if __name__ == "__main__":
    base = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    asyncio.run(run(base.rstrip("/")))
