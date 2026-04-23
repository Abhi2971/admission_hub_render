import logging
import os
import json
from pathlib import Path
from datetime import datetime
from bson import ObjectId
from flask import Flask
from flask.json.provider import JSONProvider
from flask_cors import CORS
from flask_mail import Mail
from flask_socketio import SocketIO
from dotenv import load_dotenv
from celery import Celery

from app.config import get_config
from app.database import init_db
from app.middlewares.error_handler import register_error_handlers, jwt
from app.middlewares.rate_limiter import limiter

# Custom JSON provider using standard json with ObjectId and datetime handling
class CustomJSONProvider(JSONProvider):
    def dumps(self, obj, **kwargs):
        return json.dumps(obj, default=self._default, **kwargs)

    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)

    def _default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        # For other non-serializable types, let the caller handle it
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

# Load environment variables from the .env file in the backend root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize extensions
mail = Mail()
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
celery = Celery(__name__, broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Set custom JSON provider
    app.json = CustomJSONProvider(app)

    # Disable strict slashes globally
    app.url_map.strict_slashes = False

    # Load configuration
    if not config_name:
        config_name = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(get_config(config_name))

    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    jwt.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app, cors_allowed_origins=app.config['CORS_ORIGINS'])
    celery.conf.update(app.config)

    # Initialize database connection
    init_db(app)

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    from app.routes import register_blueprints
    register_blueprints(app)

    # Import socketio events
    from app.routes import notifications

    # Setup logging
    if not app.debug:
        handler = logging.FileHandler(os.path.join('app', 'logs', 'app.log'))
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)

    app.logger.info('Application started')
    return app