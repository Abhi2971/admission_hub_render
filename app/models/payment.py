from datetime import datetime
from app.database import get_db

class Payment:
    """Represents a payment made by a student."""

    collection_name = 'payments'

    @classmethod
    def create(cls, data):
        """Create a new payment record (before verification)."""
        db = get_db()
        data['created_at'] = datetime.utcnow()
        data['status'] = data.get('status', 'created')
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_order_id(cls, razorpay_order_id):
        """Find payment by Razorpay order ID."""
        db = get_db()
        return db[cls.collection_name].find_one({'razorpay_order_id': razorpay_order_id})

    @classmethod
    def update_after_success(cls, razorpay_order_id, razorpay_payment_id, status='success'):
        """Update payment record after successful payment."""
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'razorpay_order_id': razorpay_order_id},
            {'$set': {
                'razorpay_payment_id': razorpay_payment_id,
                'status': status,
                'paid_at': datetime.utcnow()
            }}
        )
        return result.modified_count > 0

    @classmethod
    def find_by_student(cls, student_id):
        """Find payments for a student."""
        from bson.objectid import ObjectId
        db = get_db()
        return list(db[cls.collection_name].find({'student_id': ObjectId(student_id)}).sort('created_at', -1))

    @classmethod
    def find_by_application(cls, application_id):
        """Find payments for an application."""
        from bson.objectid import ObjectId
        db = get_db()
        return list(db[cls.collection_name].find({'application_id': ObjectId(application_id)}))