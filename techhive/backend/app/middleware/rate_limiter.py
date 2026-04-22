from collections import defaultdict, deque
from functools import wraps
from time import time

from flask import current_app, jsonify, request


_REQUEST_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(scope: str, max_requests_config_key: str, window_seconds_config_key: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            max_requests = current_app.config[max_requests_config_key]
            window_seconds = current_app.config[window_seconds_config_key]
            identifier = request.headers.get("X-Forwarded-For", request.remote_addr or "anonymous")
            bucket_key = f"{scope}:{identifier}"
            now = time()
            bucket = _REQUEST_BUCKETS[bucket_key]

            while bucket and now - bucket[0] >= window_seconds:
                bucket.popleft()

            if len(bucket) >= max_requests:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                response = jsonify(
                    {
                        "error": {
                            "code": "rate_limit_exceeded",
                            "message": "Too many requests. Please try again shortly.",
                        }
                    }
                )
                response.status_code = 429
                response.headers["Retry-After"] = str(retry_after)
                return response

            bucket.append(now)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def reset_rate_limits() -> None:
    _REQUEST_BUCKETS.clear()
