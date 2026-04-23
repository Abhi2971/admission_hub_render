# backend/app/models/application.py
"""
Application model for student applications.
"""
from datetime import datetime
from app.database import get_db

class Application:
    """Represents a student's application to a course."""

    collection_name = 'applications'

    STATUS_VALUES = ['applied', 'under_review', 'shortlisted', 'rejected', 'offered', 'confirmed']
    
    CATEGORY_VALUES = ['general', 'obc', 'sc', 'st', 'ews', 'pwd', 'nri', 'management']

    @classmethod
    def create(cls, data):
        """Create a new application."""
        db = get_db()
        data['applied_at'] = datetime.utcnow()
        data['updated_at'] = data['applied_at']
        data['status'] = data.get('status', 'applied')
        
        if 'category' not in data:
            data['category'] = 'general'
        
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_id(cls, application_id):
        """Find application by _id."""
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'_id': ObjectId(application_id)})

    @classmethod
    def find_by_student(cls, student_id, status=None):
        """Find applications for a student, optionally filtered by status."""
        from bson.objectid import ObjectId
        db = get_db()
        query = {'student_id': ObjectId(student_id)}
        if status:
            query['status'] = status
        return list(db[cls.collection_name].find(query).sort('applied_at', -1))

    @classmethod
    def find_by_college(cls, college_id, status=None, page=1, per_page=20):
        """Find applications for a college (for admin)."""
        from bson.objectid import ObjectId
        db = get_db()
        skip = (page - 1) * per_page
        query = {'college_id': ObjectId(college_id)}
        if status:
            query['status'] = status
        return list(db[cls.collection_name].find(query).skip(skip).limit(per_page).sort('applied_at', -1))

    @classmethod
    def update_status(cls, application_id, new_status):
        """Update application status."""
        from bson.objectid import ObjectId
        if new_status not in cls.STATUS_VALUES:
            raise ValueError(f"Invalid status: {new_status}")
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(application_id)},
            {'$set': {'status': new_status, 'updated_at': datetime.utcnow()}}
        )
        return result.modified_count > 0

    @classmethod
    def delete(cls, application_id):
        """Delete an application (student withdraw)."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].delete_one({'_id': ObjectId(application_id)})
        return result.deleted_count > 0

    @classmethod
    def count_by_college_and_status(cls, college_id):
        """Get application counts per status for a college."""
        from bson.objectid import ObjectId
        db = get_db()
        pipeline = [
            {'$match': {'college_id': ObjectId(college_id)}},
            {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
        ]
        result = db[cls.collection_name].aggregate(pipeline)
        return {item['_id']: item['count'] for item in result}