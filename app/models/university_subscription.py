# backend/app/models/university_subscription.py
"""
University Subscription model for managing university-level subscriptions.
"""
from datetime import datetime, timedelta
from app.database import get_db

class UniversitySubscription:
    """Represents a subscription for a university."""

    collection_name = 'university_subscriptions'

    @classmethod
    def create(cls, university_id, plan_id, payment_id=None):
        """Create a new subscription for university."""
        db = get_db()
        plan = db.college_plans.find_one({'_id': plan_id})
        if not plan:
            return None
        
        start_date = datetime.utcnow()
        if plan.get('billing_period') == 'monthly':
            end_date = start_date + timedelta(days=30)
        else:
            end_date = start_date + timedelta(days=365)
        
        data = {
            'university_id': university_id,
            'plan_id': plan_id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'active',
            'payment_id': payment_id,
            'created_at': datetime.utcnow(),
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
    def find_active_by_university(cls, university_id):
        """Find active subscription for a university."""
        from bson.objectid import ObjectId
        db = get_db()
        now = datetime.utcnow()
        sub = db[cls.collection_name].find_one({
            'university_id': ObjectId(university_id),
            'status': 'active',
            'start_date': {'$lte': now},
            'end_date': {'$gte': now}
        })
        if sub:
            plan = db.college_plans.find_one({'_id': sub['plan_id']})
            if plan:
                sub['plan'] = plan
            # Count current usage
            colleges_count = db.colleges.count_documents({'university_id': ObjectId(university_id)})
            sub['usage'] = {
                'colleges': colleges_count,
                'courses': 0,
                'students': 0
            }
        return sub

    @classmethod
    def find_history_by_university(cls, university_id, limit=20):
        """Get subscription history for a university."""
        from bson.objectid import ObjectId
        db = get_db()
        subs = list(db[cls.collection_name].find(
            {'university_id': ObjectId(university_id)}
        ).sort('start_date', -1).limit(limit))
        for sub in subs:
            sub['_id'] = str(sub['_id'])
            sub['university_id'] = str(sub['university_id'])
            sub['plan_id'] = str(sub['plan_id'])
            if 'history' in sub:
                for h in sub['history']:
                    if isinstance(h.get('date'), datetime):
                        h['date'] = h['date'].isoformat()
        return subs

    @classmethod
    def check_feature_access(cls, university_id, feature):
        """Check if university has access to a feature."""
        sub = cls.find_active_by_university(university_id)
        if not sub:
            return False
        
        plan = sub.get('plan', {})
        features = plan.get('features', {})
        
        # Check specific feature access
        if feature == 'unlimited_colleges':
            return features.get('max_colleges') == -1 or features.get('max_colleges', 0) > 100
        if feature == 'api_access':
            return features.get('api_access', False)
        if feature == 'custom_branding':
            return features.get('custom_branding', False)
        if feature == 'advanced_analytics':
            analytics = features.get('analytics', [])
            return 'advanced' in analytics or 'realtime' in analytics
        
        return True

    @classmethod
    def check_college_limit(cls, university_id):
        """Check if university can add more colleges."""
        sub = cls.find_active_by_university(university_id)
        if not sub:
            return {'can_add': False, 'reason': 'No active subscription'}
        
        plan = sub.get('plan', {})
        max_colleges = plan.get('features', {}).get('max_colleges', 0)
        
        if max_colleges == -1:
            return {'can_add': True, 'remaining': float('inf')}
        
        current_count = sub.get('usage', {}).get('colleges', 0)
        if current_count >= max_colleges:
            return {'can_add': False, 'reason': 'College limit reached', 'max': max_colleges}
        
        return {'can_add': True, 'remaining': max_colleges - current_count, 'max': max_colleges}
