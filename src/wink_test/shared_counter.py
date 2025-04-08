import redis.asyncio as redis

__all__ = ("SharedCounter",)


class SharedCounter:
    redis_namespace = "shared-counter"

    @property
    def redis_counter_key(self):
        return self.redis_namespace + ":" + self.name

    def __init__(self, redis_client: redis.Redis, name: str) -> None:
        self.redis_client = redis_client
        self.name = name

    async def reset(self):
        await self.redis_client.delete(self.redis_counter_key)

    async def get(self) -> int:
        raw_value = await self.redis_client.get(self.redis_counter_key)
        match raw_value:
            case None:
                return 0
            case bytes():
                return int(raw_value.decode())
            case str():
                return int(raw_value)
            case _:
                raise TypeError

    async def increment(self):
        await self.redis_client.incr(self.redis_counter_key)
