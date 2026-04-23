from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from app.middlewares.rate_limiter import limiter

def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get('role') not in roles:
                return jsonify({'error': 'Access forbidden: insufficient role'}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def rate_limit(limit=5, per=60):
    return limiter.limit(f"{limit} per {per} seconds")