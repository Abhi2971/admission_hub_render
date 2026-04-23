from datetime import datetime
from app.database import get_db

class Document:
    collection_name = 'documents'

    @classmethod
    def create(cls, data):
        db = get_db()
        data['uploaded_at'] = datetime.utcnow()
        data['verification_status'] = data.get('verification_status', 'pending')
        data['rejection_reason'] = data.get('rejection_reason', None)
        data['is_active'] = data.get('is_active', True)
        data['is_profile_document'] = data.get('is_profile_document', False)
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_id(cls, document_id):
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'_id': ObjectId(document_id)})

    @classmethod
    def find_by_application(cls, application_id):
        from bson.objectid import ObjectId
        db = get_db()
        if application_id:
            return list(db[cls.collection_name].find(
                {'application_id': ObjectId(application_id), 'is_active': True}
            ))
        return []

    @classmethod
    def find_by_student(cls, student_id):
        from bson.objectid import ObjectId
        db = get_db()
        return list(db[cls.collection_name].find(
            {'student_id': ObjectId(student_id), 'is_active': True}
        ).sort('uploaded_at', -1))

    @classmethod
    def find_by_type(cls, student_id, document_type):
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one(
            {'student_id': ObjectId(student_id), 'document_type': document_type, 'is_active': True}
        )

    @classmethod
    def update_verification(cls, document_id, status, rejection_reason=None):
        from bson.objectid import ObjectId
        db = get_db()
        update = {'verification_status': status}
        if rejection_reason is not None:
            update['rejection_reason'] = rejection_reason
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(document_id)},
            {'$set': update}
        )
        return result.modified_count > 0

    @classmethod
    def soft_delete(cls, document_id):
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(document_id)},
            {'$set': {'is_active': False}}
        )
        return result.modified_count > 0

    @classmethod
    def delete(cls, document_id):
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].delete_one({'_id': ObjectId(document_id)})
        return result.deleted_count > 0