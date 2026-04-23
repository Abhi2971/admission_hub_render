from datetime import datetime, timedelta
from app.database import get_db

class CollegeSubscription:
    collection_name = 'college_subscriptions'

    @classmethod
    def create(cls, college_id, plan_id, payment_id=None):
        db = get_db()
        plan = db.college_plans.find_one({'_id': plan_id})
        if not plan:
            return None
        start_date = datetime.utcnow()
        # Calculate end date based on billing period
        if plan.get('billing_period') == 'monthly':
            end_date = start_date + timedelta(days=30)
        else:  # yearly
            end_date = start_date + timedelta(days=365)
        
        # Store plan details including features
        plan_details = {
            'plan_name': plan.get('plan_name'),
            'price': plan.get('price', 0),
            'billing_period': plan.get('billing_period', 'monthly'),
            'features': plan.get('features', {}),
            'description': plan.get('description', '')
        }
        
        data = {
            'college_id': college_id,
            'plan_id': plan_id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'active',
            'payment_id': payment_id,
            'created_at': datetime.utcnow(),
            'plan': plan_details,
            'history': [
                {
                    'event': 'subscribed',
                    'date': start_date,
                    'plan_name': plan['plan_name'],
                    'details': f"Subscribed to {plan['plan_name']} plan"
                }
            ]
        }
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_active_by_college(cls, college_id):
        from bson.objectid import ObjectId
        db = get_db()
        now = datetime.utcnow()
        sub = db[cls.collection_name].find_one({
            'college_id': ObjectId(college_id),
            'status': 'active',
            'start_date': {'$lte': now},
            'end_date': {'$gte': now}
        })
        if sub:
            plan = db.college_plans.find_one({'_id': sub['plan_id']})
            if plan:
                sub['plan'] = plan
            # Count current courses and manual students
            courses_count = db.courses.count_documents({'college_id': ObjectId(college_id)})
            students_count = db.students.count_documents({'college_id': ObjectId(college_id), 'created_by': 'admin'})
            sub['usage'] = {
                'courses': courses_count,
                'students': students_count
            }
        return sub

    @classmethod
    def find_history_by_college(cls, college_id, limit=20):
        from bson.objectid import ObjectId
        db = get_db()
        # Return all subscriptions for this college, sorted by start_date desc
        subs = list(db[cls.collection_name].find(
            {'college_id': ObjectId(college_id)}
        ).sort('start_date', -1).limit(limit))
        for sub in subs:
            sub['_id'] = str(sub['_id'])
            sub['college_id'] = str(sub['college_id'])
            sub['plan_id'] = str(sub['plan_id'])
            # Get plan details
            plan = db.college_plans.find_one({'_id': sub['plan_id']})
            if plan:
                sub['plan'] = {
                    '_id': str(plan['_id']),
                    'plan_name': plan.get('plan_name', 'N/A'),
                    'billing_period': plan.get('billing_period', 'N/A'),
                    'price': plan.get('price', 0)
                }
            if 'history' in sub:
                for h in sub['history']:
                    if isinstance(h.get('date'), datetime):
                        h['date'] = h['date'].isoformat()
        return subs

    @classmethod
    def expire_old(cls):
        db = get_db()
        now = datetime.utcnow()
        # Find subscriptions that expired
        expired = db[cls.collection_name].find(
            {'status': 'active', 'end_date': {'$lt': now}}
        )
        for sub in expired:
            # Add history entry
            db[cls.collection_name].update_one(
                {'_id': sub['_id']},
                {
                    '$set': {'status': 'expired'},
                    '$push': {
                        'history': {
                            'event': 'expired',
                            'date': now,
                            'details': 'Subscription expired'
                        }
                    }
                }
            )
        return expired.retrieved