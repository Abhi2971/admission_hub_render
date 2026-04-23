from datetime import datetime
from app.database import get_db
from bson.objectid import ObjectId

class ChatHistory:
    collection_name = 'chat_histories'

    @classmethod
    def save_message(cls, student_id, role, content, intent=None):
        db = get_db()
        
        history = db[cls.collection_name].find_one({'student_id': ObjectId(student_id)})
        
        message = {
            'role': role,
            'content': content,
            'intent': intent,
            'timestamp': datetime.utcnow()
        }
        
        if history:
            db[cls.collection_name].update_one(
                {'student_id': ObjectId(student_id)},
                {
                    '$push': {'messages': message},
                    '$set': {'updated_at': datetime.utcnow()}
                }
            )
        else:
            db[cls.collection_name].insert_one({
                'student_id': ObjectId(student_id),
                'messages': [message],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
        
        return message

    @classmethod
    def get_history(cls, student_id, limit=50):
        db = get_db()
        history = db[cls.collection_name].find_one({'student_id': ObjectId(student_id)})
        
        if history and history.get('messages'):
            return history['messages'][-limit:]
        return []

    @classmethod
    def clear_history(cls, student_id):
        db = get_db()
        db[cls.collection_name].delete_one({'student_id': ObjectId(student_id)})
        return True
