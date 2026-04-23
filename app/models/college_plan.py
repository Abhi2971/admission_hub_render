from datetime import datetime
from app.database import get_db

class CollegePlan:
    collection_name = 'college_plans'

    @classmethod
    def create(cls, data):
        db = get_db()
        data['created_at'] = datetime.utcnow()
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_id(cls, plan_id):
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'_id': ObjectId(plan_id)})

    @classmethod
    def get_all(cls, include_inactive=False):
        db = get_db()
        query = {} if include_inactive else {'is_active': True}
        return list(db[cls.collection_name].find(query))

    @classmethod
    def update(cls, plan_id, updates):
        from bson.objectid import ObjectId
        from bson.errors import InvalidId
        db = get_db()
        try:
            obj_id = ObjectId(plan_id)
        except InvalidId:
            return False
        result = db[cls.collection_name].update_one(
            {'_id': obj_id},
            {'$set': updates}
        )
        return result.modified_count > 0