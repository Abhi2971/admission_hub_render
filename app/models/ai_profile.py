# backend/app/models/ai_profile.py
"""
AI profile model to store student's career preferences for recommendations.
"""
from datetime import datetime
from app.database import get_db

class AIProfile:
    """Stores student's interests, skills, and career goals for AI recommendations."""

    collection_name = 'ai_profiles'

    @classmethod
    def create(cls, data):
        """Create a new AI profile."""
        db = get_db()
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = data['created_at']
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_student(cls, student_id):
        """Find AI profile by student ID."""
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'student_id': ObjectId(student_id)})

    @classmethod
    def update(cls, student_id, updates):
        """Update AI profile."""
        from bson.objectid import ObjectId
        db = get_db()
        updates['updated_at'] = datetime.utcnow()
        result = db[cls.collection_name].update_one(
            {'student_id': ObjectId(student_id)},
            {'$set': updates},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None