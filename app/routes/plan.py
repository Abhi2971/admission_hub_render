# backend/app/routes/plan.py
"""
Plan management routes for SuperAdmin.
Allows SuperAdmin to create/manage plans for Universities, Colleges, and Students.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from app.models.plan import Plan, Subscription
from app.middlewares.auth_middleware import role_required

plan_bp = Blueprint('plan', __name__)


def convert_objectid(obj):
    """Convert ObjectId to string for JSON serialization."""
    if isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == '_id':
                result['id'] = str(v)
            elif isinstance(v, ObjectId):
                result[k] = str(v)
            elif isinstance(v, datetime):
                result[k] = v.isoformat()
            elif isinstance(v, list):
                result[k] = convert_objectid(v)
            elif isinstance(v, dict):
                result[k] = convert_objectid(v)
            else:
                result[k] = v
        return result
    return obj


# ============================================================
# PLAN MANAGEMENT (SuperAdmin Only)
# ============================================================

@plan_bp.route('', methods=['GET'])
@jwt_required()
@role_required('super_admin')
def get_all_plans():
    """Get all plans, optionally filtered by type."""
    plan_type = request.args.get('type')  # university, college, student
    
    try:
        if plan_type:
            plans = Plan.get_by_type(plan_type)
        else:
            plans = Plan.get_all(include_inactive=True)
        
        return jsonify({'plans': convert_objectid(plans)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@plan_bp.route('/plans', methods=['GET'])
@jwt_required()
@role_required('super_admin')
def get_all_plans_alias():
    """Get all plans, optionally filtered by type."""
    plan_type = request.args.get('type')  # university, college, student
    
    try:
        if plan_type:
            plans = Plan.get_by_type(plan_type)
        else:
            plans = Plan.get_all()
        
        return jsonify({'plans': convert_objectid(plans)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@plan_bp.route('/plans/university', methods=['GET'])
@jwt_required()
def get_university_plans():
    """Get all university plans (public)."""
    try:
        plans = Plan.get_by_type('university')
        return jsonify({'plans': convert_objectid(plans)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@plan_bp.route('/plans/college', methods=['GET'])
@jwt_required()
def get_college_plans():
    """Get all college plans (public)."""
    try:
        plans = Plan.get_by_type('college')
        return jsonify({'plans': convert_objectid(plans)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@plan_bp.route('/plans/student', methods=['GET'])
@jwt_required()
def get_student_plans():
    """Get all student plans (public)."""
    try:
        plans = Plan.get_by_type('student')
        return jsonify({'plans': convert_objectid(plans)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@plan_bp.route('/plans', methods=['POST'])
@jwt_required()
@role_required('super_admin')
def create_plan():
    """Create a new plan."""
    data = request.get_json()
    
    required = ['plan_name', 'plan_type', 'price', 'billing_period']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400
    
    if data['plan_type'] not in Plan.PLAN_TYPES:
        return jsonify({'error': 'Invalid plan type'}), 400
    
    # Check if plan with same name and type exists
    existing = Plan.find_by_name_and_type(data['plan_name'], data['plan_type'])
    if existing:
        return jsonify({'error': 'Plan with this name already exists'}), 409
    
    plan_data = {
        'plan_name': data['plan_name'],
        'plan_type': data['plan_type'],
        'price': float(data['price']),
        'billing_period': data['billing_period'],
        'description': data.get('description', ''),
        'features': data.get('features', {})
    }
    
    try:
        plan_id = Plan.create(plan_data)
        return jsonify({
            'message': 'Plan created',
            'plan_id': plan_id
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@plan_bp.route('/plans/<plan_id>', methods=['GET'])
@jwt_required()
@role_required('super_admin')
def get_plan(plan_id):
    """Get single plan details."""
    plan = Plan.find_by_id(plan_id)
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
    
    return jsonify({'plan': convert_objectid(plan)}), 200


@plan_bp.route('/plans/<plan_id>', methods=['PUT'])
@jwt_required()
@role_required('super_admin')
def update_plan(plan_id):
    """Update plan details."""
    data = request.get_json()
    
    allowed = ['plan_name', 'price', 'billing_period', 'description', 'features', 'is_active']
    updates = {k: v for k, v in data.items() if k in allowed}
    
    try:
        Plan.update(plan_id, updates)
        return jsonify({'message': 'Plan updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@plan_bp.route('/plans/<plan_id>', methods=['DELETE'])
@jwt_required()
@role_required('super_admin')
def delete_plan(plan_id):
    """Delete (deactivate) a plan."""
    try:
        Plan.delete(plan_id)
        return jsonify({'message': 'Plan deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# SUBSCRIPTION MANAGEMENT
# ============================================================

@plan_bp.route('/subscriptions', methods=['POST'])
@jwt_required()
def create_subscription():
    """Create a new subscription (purchase a plan)."""
    data = request.get_json()
    
    required = ['plan_id', 'entity_id', 'entity_type']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400
    
    if data['entity_type'] not in ['university', 'college', 'student']:
        return jsonify({'error': 'Invalid entity type'}), 400
    
    # Check if entity already has active subscription
    existing = Subscription.find_active(data['entity_id'], data['entity_type'])
    if existing:
        return jsonify({'error': 'Entity already has an active subscription'}), 409
    
    try:
        sub_id = Subscription.create(
            entity_id=data['entity_id'],
            plan_id=data['plan_id'],
            entity_type=data['entity_type'],
            payment_id=data.get('payment_id')
        )
        
        if not sub_id:
            return jsonify({'error': 'Invalid plan'}), 400
        
        return jsonify({
            'message': 'Subscription created',
            'subscription_id': sub_id
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@plan_bp.route('/subscriptions/<entity_id>/<entity_type>/active', methods=['GET'])
@jwt_required()
def get_active_subscription(entity_id, entity_type):
    """Get active subscription for an entity."""
    try:
        subscription = Subscription.find_active(entity_id, entity_type)
        if not subscription:
            return jsonify({'subscription': None}), 200
        
        return jsonify({'subscription': convert_objectid(subscription)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@plan_bp.route('/subscriptions/<entity_id>/<entity_type>/history', methods=['GET'])
@jwt_required()
def get_subscription_history(entity_id, entity_type):
    """Get subscription history for an entity."""
    try:
        subscriptions = Subscription.find_by_entity(entity_id, entity_type)
        return jsonify({'subscriptions': convert_objectid(subscriptions)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# AI ACCESS CHECK
# ============================================================

@plan_bp.route('/check-ai-access/<entity_id>/<entity_type>', methods=['GET'])
@jwt_required()
def check_ai_access(entity_id, entity_type):
    """Check if entity has AI access."""
    try:
        has_access = Subscription.has_ai_access(entity_id, entity_type)
        credits = Subscription.get_ai_credits(entity_id, entity_type)
        
        return jsonify({
            'has_ai_access': has_access,
            'ai_credits': credits
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# LIMIT CHECKS
# ============================================================

@plan_bp.route('/check-limit/<entity_id>/<entity_type>/<resource>', methods=['GET'])
@jwt_required()
def check_limit(entity_id, entity_type, resource):
    """Check if entity can add more of a resource."""
    try:
        limit_info = Subscription.check_limit(entity_id, entity_type, resource)
        return jsonify(limit_info), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
