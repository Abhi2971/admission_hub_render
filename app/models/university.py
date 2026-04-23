# backend/app/models/university.py
"""
University model.
"""
from datetime import datetime
from app.database import get_db

class University:
    """Represents a university that manages multiple colleges."""

    collection_name = 'universities'

    @classmethod
    def create(cls, data):
        """Create a new university."""
        db = get_db()
        data['created_at'] = datetime.utcnow()
        data['is_active'] = True
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_id(cls, university_id):
        """Find university by _id."""
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'_id': ObjectId(university_id)})

    @classmethod
    def find_by_code(cls, code):
        """Find university by unique code."""
        db = get_db()
        return db[cls.collection_name].find_one({'code': code})

    @classmethod
    def get_all(cls, filter=None, page=1, per_page=20):
        """Get paginated list of universities."""
        db = get_db()
        skip = (page - 1) * per_page
        query = filter or {}
        return list(db[cls.collection_name].find(query).skip(skip).limit(per_page))

    @classmethod
    def get_all_as_dict(cls):
        """Get all universities as a list."""
        db = get_db()
        return list(db[cls.collection_name].find({'is_active': True}))

    @classmethod
    def update(cls, university_id, updates):
        """Update university details."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(university_id)},
            {'$set': updates}
        )
        return result.modified_count > 0

    @classmethod
    def delete(cls, university_id):
        """Delete a university."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(university_id)},
            {'$set': {'is_active': False}}
        )
        return result.modified_count > 0
