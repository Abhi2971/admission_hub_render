# backend/app/models/notification.py
"""
Notification model for in-app notifications.
"""
from datetime import datetime
from app.database import get_db

class Notification:
    """Represents a notification for a user (student or admin)."""

    collection_name = 'notifications'

    @classmethod
    def create(cls, data):
        """Create a new notification."""
        db = get_db()
        data['created_at'] = datetime.utcnow()
        data['read'] = False
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_user(cls, user_id, user_type='student', unread_only=False, limit=50):
        """Find notifications for a user."""
        from bson.objectid import ObjectId
        db = get_db()
        query = {'user_id': ObjectId(user_id), 'user_type': user_type}
        if unread_only:
            query['read'] = False
        return list(db[cls.collection_name].find(query).sort('created_at', -1).limit(limit))

    @classmethod
    def mark_as_read(cls, notification_id):
        """Mark a notification as read."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(notification_id)},
            {'$set': {'read': True}}
        )
        return result.modified_count > 0

    @classmethod
    def mark_all_read(cls, user_id, user_type='student'):
        """Mark all notifications for a user as read."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_many(
            {'user_id': ObjectId(user_id), 'user_type': user_type, 'read': False},
            {'$set': {'read': True}}
        )
        return result.modified_count