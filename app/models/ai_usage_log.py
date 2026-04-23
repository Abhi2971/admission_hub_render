from datetime import datetime
from app.database import get_db

class AIUsageLog:
    collection_name = 'ai_usage_logs'

    @classmethod
    def log(cls, student_id, action, credits_used=1):
        from bson.objectid import ObjectId
        db = get_db()
        data = {
            'student_id': ObjectId(student_id),
            'action': action,
            'credits_used': credits_used,
            'timestamp': datetime.utcnow()
        }
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id