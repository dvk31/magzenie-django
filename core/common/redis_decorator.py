import redis
import logging
import json
from functools import wraps
from django.conf import settings
from django.http import JsonResponse
from rest_framework import status

# Configure logging
logger = logging.getLogger(__name__)

# Create a Redis connection pool
pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD
)

def redis_connection(use_cache=False, cache_key=None, cache_timeout=3600):
    """
    A decorator for handling Redis operations with built-in connection pooling,
    error handling, and optional caching.

    Parameters:
    - use_cache (bool): Whether to use caching for the decorated function.
    - cache_key (str): The key under which to store the cached result. Required if use_cache is True.
    - cache_timeout (int): The timeout in seconds for the cache.

    Usage:

    @redis_connection(use_cache=True, cache_key='my_cache_key', cache_timeout=600)
    def my_function(redis_client, arg1, arg2):
        # Function logic here
        return "Result"
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            redis_client = redis.Redis(connection_pool=pool)
            if use_cache and cache_key:
                cached_result = redis_client.get(cache_key)
                if cached_result:
                    logger.info(f"Cache hit for key: {cache_key}")
                    return json.loads(cached_result)
                else:
                    logger.info(f"Cache miss for key: {cache_key}")

            try:
                result = func(redis_client, *args, **kwargs)
                if use_cache and cache_key:
                    redis_client.set(cache_key, json.dumps(result), ex=cache_timeout)
                    logger.info(f"Result cached under key: {cache_key} with timeout: {cache_timeout}s")
                return result
            except redis.RedisError as e:
                logger.error(f"Redis error: {e}")
                raise
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                raise
        return wrapper
    return decorator

def redis_cache(key, timeout=3600):
    """
    A decorator to cache function results in Redis.

    Parameters:
    - key (str): The Redis key under which to cache the result.
    - timeout (int): Cache expiration timeout in seconds.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD
            )
            cached_data = redis_client.get(key)
            if cached_data:
                return JsonResponse(json.loads(cached_data), status=status.HTTP_200_OK)

            response = func(*args, **kwargs)
            if response.status_code == 200:
                redis_client.set(key, json.dumps(response.data), ex=timeout)
            return response
        return wrapper
    return decorator