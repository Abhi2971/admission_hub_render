# backend/app/models/activity_log.py
"""
Activity log model for audit trail.
"""
from datetime import datetime
from app.database import get_db

class ActivityLog:
    """Logs user activities for auditing."""

    collection_name = 'activity_logs'

    @classmethod
    def log(cls, user_id, user_type, action, resource, details=None, ip_address=None):
        """Create a new activity log entry."""
        db = get_db()
        log_entry = {
            'user_id': user_id,
            'user_type': user_type,
            'action': action,
            'resource': resource,
            'details': details or {},
            'ip_address': ip_address,
            'timestamp': datetime.utcnow()
        }
        result = db[cls.collection_name].insert_one(log_entry)
        return result.inserted_id

    @classmethod
    def find_by_user(cls, user_id, user_type, limit=50):
        """Find recent activities for a user."""
        from bson.objectid import ObjectId
        db = get_db()
        return list(db[cls.collection_name].find(
            {'user_id': ObjectId(user_id), 'user_type': user_type}
        ).sort('timestamp', -1).limit(limit))

    @classmethod
    def find_by_resource(cls, resource_id, resource_type):
        """Find activities related to a specific resource."""
        db = get_db()
        return list(db[cls.collection_name].find(
            {'resource.id': resource_id, 'resource.type': resource_type}
        ).sort('timestamp', -1))