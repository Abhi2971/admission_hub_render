# backend/app/models/membership_plan.py
"""
Membership plan model for college subscriptions.
"""
from datetime import datetime
from app.database import get_db

class MembershipPlan:
    """Represents a membership plan for colleges."""

    collection_name = 'membership_plans'

    @classmethod
    def create(cls, data):
        """Create a new membership plan."""
        db = get_db()
        data['created_at'] = datetime.utcnow()
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_id(cls, plan_id):
        """Find plan by _id."""
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'_id': ObjectId(plan_id)})

    @classmethod
    def find_by_name(cls, plan_name):
        """Find plan by name."""
        db = get_db()
        return db[cls.collection_name].find_one({'plan_name': plan_name})

    @classmethod
    def get_all_active(cls):
        """Get all active plans."""
        db = get_db()
        return list(db[cls.collection_name].find())

    @classmethod
    def update(cls, plan_id, updates):
        """Update plan details."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(plan_id)},
            {'$set': updates}
        )
        return result.modified_count > 0

    @classmethod
    def delete(cls, plan_id):
        """Delete a plan."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].delete_one({'_id': ObjectId(plan_id)})
        return result.deleted_count > 0