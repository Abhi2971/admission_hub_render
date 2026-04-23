# backend/app/models/student.py
"""
Student model.
"""
from datetime import datetime
from app.database import get_db
import bcrypt

class Student:
    """Represents a student in the system."""

    collection_name = 'students'

    # Qualification levels
    QUALIFICATIONS = ['10th', '12th', 'diploma', 'graduation', 'post_graduation']
    
    # Streams for 12th
    STREAMS = ['science', 'commerce', 'arts', 'vocational']
    
    # Course categories based on qualification
    COURSE_CATEGORIES = {
        '10th': ['diploma', 'iti', '11th', '12th'],
        '12th_science': ['btech', 'mbbs', 'bds', 'bpharm', 'bsc', 'bca', 'barch', 'bvoc'],
        '12th_commerce': ['bcom', 'bba', 'baf', 'bms', 'bsc'],
        '12th_arts': ['ba', 'bfa', 'bvoc', 'bsc'],
        '12th_vocational': ['bvoc', 'bba', 'bcom'],
        'diploma': ['btech_lateral', 'bsc_lateral', 'degree'],
        'graduation': ['mtech', 'mba', 'msc', 'ma', 'mcom', 'mca'],
        'post_graduation': ['phd', 'post_doc']
    }

    @classmethod
    def create(cls, data):
        """Create a new student document."""
        db = get_db()
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = data['created_at']
        if 'password' in data:
            data['password_hash'] = cls._hash_password(data.pop('password'))
        
        # Set default qualification if not provided
        if 'qualification' not in data:
            data['qualification'] = '12th'
        if 'stream' not in data:
            data['stream'] = 'science'
            
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_id(cls, student_id):
        """Find student by _id."""
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'_id': ObjectId(student_id)})

    @classmethod
    def find_by_email(cls, email):
        """Find student by email."""
        db = get_db()
        return db[cls.collection_name].find_one({'email': email})

    @classmethod
    def find_by_mobile(cls, mobile):
        """Find student by mobile."""
        db = get_db()
        return db[cls.collection_name].find_one({'mobile': mobile})

    @classmethod
    def find_by_google_id(cls, google_id):
        """Find student by Google OAuth ID."""
        db = get_db()
        return db[cls.collection_name].find_one({'google_id': google_id})

    @classmethod
    def update(cls, student_id, updates):
        """Update student information."""
        from bson.objectid import ObjectId
        db = get_db()
        updates['updated_at'] = datetime.utcnow()
        if 'password' in updates:
            updates['password_hash'] = cls._hash_password(updates.pop('password'))
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(student_id)},
            {'$set': updates}
        )
        return result.modified_count > 0

    @classmethod
    def verify_password(cls, student, password):
        """Verify password against hash."""
        if 'password_hash' not in student:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), student['password_hash'])

    @staticmethod
    def _hash_password(password):
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)

    @classmethod
    def find_by_criteria(cls, criteria):
        """Find students matching criteria (for admin)."""
        db = get_db()
        query = {}
        if 'college_id' in criteria:
            query['college_id'] = criteria['college_id']
        if 'course' in criteria:
            query['preferred_course'] = criteria['course']
        if 'year' in criteria:
            query['year'] = criteria['year']
        if 'created_by' in criteria:
            query['created_by'] = criteria['created_by']
        if 'qualification' in criteria:
            query['qualification'] = criteria['qualification']
        if 'stream' in criteria:
            query['stream'] = criteria['stream']
        return list(db[cls.collection_name].find(query).sort('created_at', -1))

    @classmethod
    def get_eligible_courses(cls, student_id):
        """Get courses eligible for a student based on their qualification."""
        student = cls.find_by_id(student_id)
        if not student:
            return []
        
        qualification = student.get('qualification', '12th')
        stream = student.get('stream', 'science')
        
        eligible_categories = []
        
        if qualification == '10th':
            eligible_categories = ['diploma', 'iti', '11th']
        elif qualification == '12th':
            stream_key = f"12th_{stream}"
            eligible_categories = cls.COURSE_CATEGORIES.get(stream_key, ['btech', 'bsc', 'bca'])
        elif qualification == 'diploma':
            eligible_categories = ['btech_lateral', 'bsc_lateral']
        elif qualification == 'graduation':
            eligible_categories = ['mba', 'mtech', 'msc']
        else:
            eligible_categories = ['phd']
        
        return eligible_categories