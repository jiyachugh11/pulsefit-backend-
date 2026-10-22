import os
from contextlib import contextmanager
from fastapi import HTTPException
import redis


@contextmanager
def client():
    connection = None
    try:
        connection = redis.Redis.from_url(
            os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            decode_responses=True, socket_connect_timeout=5, socket_timeout=5,
        )
        yield connection
    except redis.RedisError as exc:
        raise HTTPException(503, 'Redis unavailable. Check setup and .env.') from exc
    finally:
        if connection is not None:
            connection.close()
