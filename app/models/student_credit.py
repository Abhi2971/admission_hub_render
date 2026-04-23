from datetime import datetime
from app.database import get_db

class StudentCredit:
    collection_name = 'student_credits'

    @classmethod
    def create(cls, student_id, initial_credits=0):
        db = get_db()
        data = {
            'student_id': student_id,
            'balance': initial_credits,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_student(cls, student_id):
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'student_id': ObjectId(student_id)})

    @classmethod
    def add_credits(cls, student_id, amount):
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'student_id': ObjectId(student_id)},
            {'$inc': {'balance': amount}, '$set': {'updated_at': datetime.utcnow()}},
            upsert=True
        )
        return result.modified_count > 0

    @classmethod
    def deduct_credits(cls, student_id, amount):
        from bson.objectid import ObjectId
        db = get_db()
        # Ensure balance doesn't go negative
        result = db[cls.collection_name].update_one(
            {'student_id': ObjectId(student_id), 'balance': {'$gte': amount}},
            {'$inc': {'balance': -amount}, '$set': {'updated_at': datetime.utcnow()}}
        )
        return result.modified_count > 0

    @classmethod
    def get_balance(cls, student_id):
        from bson.objectid import ObjectId
        db = get_db()
        record = db[cls.collection_name].find_one({'student_id': ObjectId(student_id)})
        if record:
            return record.get('balance', 0)
        return 0