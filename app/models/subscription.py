# backend/app/models/subscription.py
"""
Subscription model for college memberships.
"""
from datetime import datetime, timedelta
from app.database import get_db

class Subscription:
    """Represents a college's subscription to a membership plan."""

    collection_name = 'subscriptions'

    STATUS_VALUES = ['active', 'expired', 'cancelled']

    @classmethod
    def create(cls, data):
        """Create a new subscription."""
        db = get_db()
        data['start_date'] = datetime.utcnow()
        data['end_date'] = data['start_date'] + timedelta(days=data.get('duration_days', 30))
        data['status'] = 'active'
        data['created_at'] = datetime.utcnow()
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_id(cls, subscription_id):
        """Find subscription by _id."""
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'_id': ObjectId(subscription_id)})

    @classmethod
    def find_active_by_college(cls, college_id):
        """Find active subscription for a college."""
        from bson.objectid import ObjectId
        db = get_db()
        now = datetime.utcnow()
        return db[cls.collection_name].find_one({
            'college_id': ObjectId(college_id),
            'status': 'active',
            'start_date': {'$lte': now},
            'end_date': {'$gte': now}
        })

    @classmethod
    def update_status(cls, subscription_id, status):
        """Update subscription status."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(subscription_id)},
            {'$set': {'status': status}}
        )
        return result.modified_count > 0

    @classmethod
    def expire_old(cls):
        """Mark expired subscriptions as expired."""
        db = get_db()
        now = datetime.utcnow()
        result = db[cls.collection_name].update_many(
            {'status': 'active', 'end_date': {'$lt': now}},
            {'$set': {'status': 'expired'}}
        )
        return result.modified_count