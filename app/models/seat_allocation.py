# backend/app/models/seat_allocation.py
"""
Seat Allocation Rules model for managing category-wise seat distribution.
"""
from datetime import datetime
from app.database import get_db

class SeatAllocation:
    """Manages seat allocation rules for courses."""

    collection_name = 'seat_allocations'

    CATEGORIES = ['general', 'obc', 'sc', 'st', 'ews', 'pwd', 'nri', 'management']

    @classmethod
    def create(cls, data):
        """Create seat allocation rule for a course."""
        db = get_db()
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = data['created_at']
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_course(cls, course_id):
        """Find seat allocation for a specific course."""
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'course_id': ObjectId(course_id)})

    @classmethod
    def find_by_college(cls, college_id):
        """Find all seat allocations for a college."""
        from bson.objectid import ObjectId
        db = get_db()
        return list(db[cls.collection_name].find({'college_id': ObjectId(college_id)}))

    @classmethod
    def update(cls, course_id, allocations):
        """Update seat allocation for a course."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'course_id': ObjectId(course_id)},
            {
                '$set': {
                    'allocations': allocations,
                    'updated_at': datetime.utcnow()
                }
            },
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None

    @classmethod
    def get_filled_seats(cls, course_id, category):
        """Get count of filled seats for a category."""
        from bson.objectid import ObjectId
        db = get_db()
        count = db.applications.count_documents({
            'course_id': ObjectId(course_id),
            'category': category,
            'status': {'$in': ['shortlisted', 'offered', 'confirmed']}
        })
        return count

    @classmethod
    def check_availability(cls, course_id, category):
        """Check if seats are available for a category."""
        from bson.objectid import ObjectId
        db = get_db()
        
        allocation = cls.find_by_course(course_id)
        if not allocation:
            return True
        
        allocated = allocation.get('allocations', {}).get(category, 0)
        filled = cls.get_filled_seats(course_id, category)
        
        return filled < allocated

    @classmethod
    def delete(cls, course_id):
        """Delete seat allocation for a course."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].delete_one({'course_id': ObjectId(course_id)})
        return result.deleted_count > 0
