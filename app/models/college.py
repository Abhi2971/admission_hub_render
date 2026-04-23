# backend/app/models/college.py
"""
College model.
"""
from datetime import datetime
from app.database import get_db

class College:
    """Represents a college."""

    collection_name = 'colleges'

    @classmethod
    def create(cls, data):
        """Create a new college."""
        db = get_db()
        data['created_at'] = datetime.utcnow()
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_id(cls, college_id):
        """Find college by _id."""
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'_id': ObjectId(college_id)})

    @classmethod
    def find_by_code(cls, code):
        """Find college by unique code."""
        db = get_db()
        return db[cls.collection_name].find_one({'code': code})

    @classmethod
    def get_all(cls, filter=None, page=1, per_page=20):
        """Get paginated list of colleges."""
        db = get_db()
        skip = (page - 1) * per_page
        query = filter or {}
        return list(db[cls.collection_name].find(query).skip(skip).limit(per_page))

    @classmethod
    def update(cls, college_id, updates):
        """Update college details."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(college_id)},
            {'$set': updates}
        )
        return result.modified_count > 0

    @classmethod
    def delete(cls, college_id):
        """Delete a college (soft delete maybe)."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].delete_one({'_id': ObjectId(college_id)})
        return result.deleted_count > 0