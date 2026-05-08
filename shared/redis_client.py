import redis
from .config import config

redis_client = redis.Redis(
    host=config.REDIS_HOST,         
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    password=config.REDIS_PASSWORD if config.REDIS_PASSWORD else None,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_keepalive=True,
    ssl=config.REDIS_SSL,
)
