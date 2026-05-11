import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize without storage_uri (will be configured per app)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def init_limiter(app):
    """Initialize limiter with Redis storage from app config."""
    storage_uri = app.config.get('REDIS_URL', 'memory://')
    limiter.storage_uri = storage_uri