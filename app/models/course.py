from datetime import datetime
from app.database import get_db

class Course:
    collection_name = 'courses'

    # Course categories based on qualification
    COURSE_CATEGORIES = {
        '10th': ['diploma', 'iti'],
        '12th_science': ['btech', 'mbbs', 'bds', 'bpharm', 'bsc', 'bca', 'barch'],
        '12th_commerce': ['bcom', 'bba', 'baf', 'bms'],
        '12th_arts': ['ba', 'bfa', 'bvoc'],
        'diploma': ['btech_lateral', 'degree'],
    }

    # Standard required documents by course type
    REQUIRED_DOCUMENTS = {
        'engineering': ['10th_marksheet', '12th_marksheet', 'entrance_score', 'photo', 'id_proof', 'domicile'],
        'medical': ['10th_marksheet', '12th_marksheet', 'neet_score', 'photo', 'id_proof', 'domicile', 'caste_certificate'],
        'commerce': ['10th_marksheet', '12th_marksheet', 'photo', 'id_proof', 'domicile'],
        'science': ['10th_marksheet', '12th_marksheet', 'entrance_score', 'photo', 'id_proof', 'domicile'],
        'arts': ['10th_marksheet', '12th_marksheet', 'photo', 'id_proof'],
        'management': ['10th_marksheet', '12th_marksheet', 'graduation_marksheet', 'entrance_score', 'photo', 'id_proof', 'domicile', 'experience_letter'],
        'default': ['10th_marksheet', '12th_marksheet', 'photo', 'id_proof', 'domicile']
    }

    @classmethod
    def create(cls, data):
        db = get_db()
        data['created_at'] = datetime.utcnow()
        data['available_seats'] = data.get('seats', 0)
        
        # Set required qualification
        if 'required_qualification' not in data:
            data['required_qualification'] = '12th'
        
        # Set stream if not provided
        if 'required_stream' not in data:
            data['required_stream'] = ['science', 'commerce', 'arts']
        
        # Set course category
        if 'course_category' not in data:
            data['course_category'] = cls._detect_category(data.get('course_name', ''))
        
        # Set required documents based on category
        if 'required_documents' not in data:
            data['required_documents'] = cls.REQUIRED_DOCUMENTS.get(
                data.get('course_category', 'default'),
                cls.REQUIRED_DOCUMENTS['default']
            )
        
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def _detect_category(cls, course_name):
        """Detect course category based on course name."""
        name_lower = course_name.lower()
        if any(x in name_lower for x in ['btech', 'be ', 'engineering', 'mechanical', 'electrical', 'civil', 'computer']):
            return 'engineering'
        elif any(x in name_lower for x in ['mbbs', 'bds', 'b pharm', 'medical', 'nursing', 'pharmacy']):
            return 'medical'
        elif any(x in name_lower for x in ['bba', 'bcom', 'bms', 'baf', 'mba', 'commerce', 'account']):
            return 'commerce'
        elif any(x in name_lower for x in ['bsc', 'msc', 'science', 'physics', 'chemistry', 'math']):
            return 'science'
        elif any(x in name_lower for x in ['ba', 'ma', 'arts', 'history', 'geography', 'political']):
            return 'arts'
        elif any(x in name_lower for x in ['management', 'business']):
            return 'management'
        return 'default'

    @classmethod
    def find_by_id(cls, course_id):
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'_id': ObjectId(course_id)})

    @classmethod
    def find_by_college(cls, college_id):
        from bson.objectid import ObjectId
        db = get_db()
        return list(db[cls.collection_name].find({'college_id': ObjectId(college_id)}))

    @classmethod
    def get_all(cls, filter=None, page=1, per_page=20):
        db = get_db()
        skip = (page - 1) * per_page
        query = filter or {}
        return list(db[cls.collection_name].find(query).skip(skip).limit(per_page))

    @classmethod
    def get_eligible_courses(cls, qualification, stream=None):
        """Get courses eligible for a qualification and stream."""
        from bson.objectid import ObjectId
        db = get_db()
        
        query = {}
        
        if qualification == '10th':
            query['course_category'] = {'$in': ['diploma', 'iti']}
        elif qualification == '12th':
            if stream == 'science':
                query['course_category'] = {'$in': ['engineering', 'medical', 'science']}
            elif stream == 'commerce':
                query['course_category'] = {'$in': ['commerce', 'management']}
            elif stream == 'arts':
                query['course_category'] = {'$in': ['arts', 'commerce']}
            else:
                query['required_qualification'] = '12th'
        elif qualification == 'diploma':
            query['course_category'] = {'$in': ['engineering', 'degree']}
        elif qualification == 'graduation':
            query['required_qualification'] = 'graduation'
        
        return list(db[cls.collection_name].find(query))

    @classmethod
    def update(cls, course_id, updates):
        from bson.objectid import ObjectId
        db = get_db()
        if 'seats' in updates:
            course = cls.find_by_id(course_id)
            if course:
                diff = updates['seats'] - course['seats']
                updates['available_seats'] = course.get('available_seats', 0) + diff
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(course_id)},
            {'$set': updates}
        )
        return result.modified_count > 0

    @classmethod
    def decrement_available_seats(cls, course_id, count=1):
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(course_id), 'available_seats': {'$gte': count}},
            {'$inc': {'available_seats': -count}}
        )
        return result.modified_count > 0

    @classmethod
    def delete(cls, course_id):
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].delete_one({'_id': ObjectId(course_id)})
        return result.deleted_count > 0