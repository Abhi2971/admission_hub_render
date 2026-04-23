# backend/app/models/plan.py
"""
Unified Plan model for managing all subscription plans.
Handles University, College, and Student plans in one model.
"""
from datetime import datetime, timedelta
from app.database import get_db


class Plan:
    """Unified Plan model for all roles."""
    
    collection_name = 'plans'

    PLAN_TYPES = ['university', 'college', 'student']
    
    @classmethod
    def create(cls, data):
        """Create a new plan."""
        db = get_db()
        data['created_at'] = datetime.utcnow()
        data['is_active'] = True
        data['created_by'] = 'super_admin'
        
        # Set default features if not provided
        if 'features' not in data:
            data['features'] = {}
        
        result = db[cls.collection_name].insert_one(data)
        return str(result.inserted_id)

    @classmethod
    def find_by_id(cls, plan_id):
        """Find plan by _id."""
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'_id': ObjectId(plan_id)})

    @classmethod
    def find_by_name_and_type(cls, plan_name, plan_type):
        """Find plan by name and type."""
        db = get_db()
        return db[cls.collection_name].find_one({
            'plan_name': plan_name,
            'plan_type': plan_type
        })

    @classmethod
    def get_all(cls, plan_type=None, include_inactive=False):
        """Get all plans, optionally filtered by type."""
        db = get_db()
        query = {}
        if plan_type:
            query['plan_type'] = plan_type
        if not include_inactive:
            query['is_active'] = True
        return list(db[cls.collection_name].find(query).sort('price', 1))

    @classmethod
    def get_by_type(cls, plan_type):
        """Get all active plans of a specific type."""
        db = get_db()
        return list(db[cls.collection_name].find({
            'plan_type': plan_type,
            'is_active': True
        }).sort('price', 1))

    @classmethod
    def update(cls, plan_id, updates):
        """Update plan details."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(plan_id)},
            {'$set': updates}
        )
        return result.modified_count > 0

    @classmethod
    def delete(cls, plan_id):
        """Soft delete a plan (set is_active to False)."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(plan_id)},
            {'$set': {'is_active': False}}
        )
        return result.modified_count > 0

    @classmethod
    def has_ai_access(cls, plan):
        """Check if a plan has AI features enabled."""
        if not plan:
            return False
        features = plan.get('features', {})
        return features.get('ai_enabled', False)

    @classmethod
    def get_ai_credits(cls, plan):
        """Get AI credits from a plan."""
        if not plan:
            return 0
        features = plan.get('features', {})
        return features.get('ai_credits', 0)


class Subscription:
    """Unified Subscription model for all roles."""
    
    collection_name = 'subscriptions'

    @classmethod
    def create(cls, entity_id, plan_id, entity_type, payment_id=None):
        """Create a new subscription."""
        db = get_db()
        
        plan = Plan.find_by_id(plan_id)
        if not plan:
            return None
        
        # Calculate subscription dates
        start_date = datetime.utcnow()
        billing_period = plan.get('billing_period', 'monthly')
        if billing_period == 'monthly':
            end_date = start_date + timedelta(days=30)
        elif billing_period == 'yearly':
            end_date = start_date + timedelta(days=365)
        else:
            end_date = start_date + timedelta(days=30)
        
        data = {
            'entity_id': entity_id,  # university_id, college_id, or student_id
            'entity_type': entity_type,  # 'university', 'college', 'student'
            'plan_id': plan_id,
            'plan_name': plan.get('plan_name'),
            'start_date': start_date,
            'end_date': end_date,
            'status': 'active',
            'payment_id': payment_id,
            'billing_period': billing_period,
            'amount': plan.get('price', 0),
            'created_at': datetime.utcnow(),
            'history': [
                {
                    'event': 'subscribed',
                    'date': start_date,
                    'plan_name': plan.get('plan_name'),
                    'amount': plan.get('price', 0)
                }
            ]
        }
        
        result = db[cls.collection_name].insert_one(data)
        return str(result.inserted_id)

    @classmethod
    def find_active(cls, entity_id, entity_type):
        """Find active subscription for an entity."""
        from bson.objectid import ObjectId
        db = get_db()
        now = datetime.utcnow()
        
        subscription = db[cls.collection_name].find_one({
            'entity_id': str(entity_id),
            'entity_type': entity_type,
            'status': 'active',
            'start_date': {'$lte': now},
            'end_date': {'$gte': now}
        })
        
        if subscription:
            # Attach plan details
            plan = Plan.find_by_id(subscription['plan_id'])
            if plan:
                subscription['plan'] = plan
        
        return subscription

    @classmethod
    def find_by_entity(cls, entity_id, entity_type, limit=10):
        """Find all subscriptions for an entity."""
        from bson.objectid import ObjectId
        db = get_db()
        
        subscriptions = list(db[cls.collection_name].find({
            'entity_id': str(entity_id),
            'entity_type': entity_type
        }).sort('created_at', -1).limit(limit))
        
        for sub in subscriptions:
            sub['_id'] = str(sub['_id'])
            plan = Plan.find_by_id(sub['plan_id'])
            if plan:
                sub['plan'] = plan
        
        return subscriptions

    @classmethod
    def cancel(cls, subscription_id):
        """Cancel a subscription."""
        from bson.objectid import ObjectId
        db = get_db()
        
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(subscription_id)},
            {'$set': {'status': 'cancelled', 'cancelled_at': datetime.utcnow()}}
        )
        return result.modified_count > 0

    @classmethod
    def has_ai_access(cls, entity_id, entity_type):
        """Check if entity has AI access via subscription."""
        subscription = cls.find_active(entity_id, entity_type)
        if not subscription:
            return False
        return Plan.has_ai_access(subscription.get('plan'))

    @classmethod
    def get_ai_credits(cls, entity_id, entity_type):
        """Get available AI credits for an entity."""
        subscription = cls.find_active(entity_id, entity_type)
        if not subscription:
            return 0
        return Plan.get_ai_credits(subscription.get('plan'))

    @classmethod
    def check_limit(cls, entity_id, entity_type, resource):
        """Check if entity can add more resources."""
        subscription = cls.find_active(entity_id, entity_type)
        if not subscription:
            return {'can_add': False, 'reason': 'No active subscription', 'max': 0, 'used': 0}
        
        plan = subscription.get('plan', {})
        features = plan.get('features', {})
        max_value = features.get(f'max_{resource}', -1)  # -1 means unlimited
        
        if max_value == -1:
            return {'can_add': True, 'max': -1, 'used': 0, 'remaining': -1}
        
        # Get current usage
        db = get_db()
        entity_id_str = str(entity_id)
        
        if entity_type == 'university':
            if resource == 'colleges':
                used = db.colleges.count_documents({'university_id': entity_id_str})
            else:
                used = 0
        elif entity_type == 'college':
            if resource == 'courses':
                used = db.courses.count_documents({'college_id': entity_id_str})
            else:
                used = 0
        else:
            used = 0
        
        can_add = used < max_value
        return {
            'can_add': can_add,
            'max': max_value,
            'used': used,
            'remaining': max_value - used if max_value > 0 else -1,
            'reason': 'Limit reached' if not can_add else None
        }
