# redis_utils.py
import redis
from django.conf import settings

def get_redis_client():
    """Create a Redis client using settings from Django's configuration."""
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB
    )

def get_value_from_redis(key):
    """Retrieve a value from Redis based on the provided key."""
    client = get_redis_client()
    value = client.get(key)
    if value:
        return value.decode('utf-8')  # Assuming the stored data is string encoded as utf-8
    return None