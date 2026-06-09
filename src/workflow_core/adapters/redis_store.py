from __future__ import annotations

import json

import redis.asyncio as aioredis

from workflow_core.context import Context


class RedisStore:
    """Persists execution context as JSON in Redis."""

    def __init__(self, client: aioredis.Redis, ttl: int = 3600) -> None:
        self._client = client
        self._ttl = ttl

    def _key(self, execution_id: str) -> str:
        return f"workflow:context:{execution_id}"

    async def save(self, execution_id: str, context: Context) -> None:
        await self._client.set(
            self._key(execution_id),
            context.model_dump_json(),
            ex=self._ttl,
        )

    async def load(self, execution_id: str) -> Context | None:
        raw = await self._client.get(self._key(execution_id))
        if raw is None:
            return None
        return Context.model_validate_json(raw)
