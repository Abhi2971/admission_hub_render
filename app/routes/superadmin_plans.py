import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.middlewares.auth_middleware import role_required
from app.models.college_plan import CollegePlan
from app.models.student_plan import StudentPlan

superadmin_plans_bp = Blueprint('superadmin_plans', __name__)
logger = logging.getLogger(__name__)

# ========== College Plan CRUD ==========
@superadmin_plans_bp.route('/college-plans', methods=['GET'])
@jwt_required()
@role_required('super_admin')
def get_college_plans():
    plans = CollegePlan.get_all()
    for p in plans:
        p['_id'] = str(p['_id'])
    return jsonify(plans), 200

@superadmin_plans_bp.route('/college-plans', methods=['POST'])
@jwt_required()
@role_required('super_admin')
def create_college_plan():
    data = request.get_json()
    required = ['plan_name', 'price', 'billing_period', 'max_courses', 'max_students', 'features']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400
    plan_data = {
        'plan_name': data['plan_name'],
        'price': data['price'],
        'billing_period': data['billing_period'],
        'max_courses': data['max_courses'],
        'max_students': data['max_students'],
        'features': data['features'],
        'is_active': data.get('is_active', True)
    }
    try:
        plan_id = CollegePlan.create(plan_data)
        return jsonify({'message': 'College plan created', 'plan_id': str(plan_id)}), 201
    except Exception as e:
        logger.error(f"College plan creation failed: {e}")
        return jsonify({'error': 'Failed to create plan'}), 500

@superadmin_plans_bp.route('/college-plans/<plan_id>', methods=['PUT'])
@jwt_required()
@role_required('super_admin')
def update_college_plan(plan_id):
    data = request.get_json()
    allowed = ['plan_name', 'price', 'billing_period', 'max_courses', 'max_students', 'features', 'is_active']
    updates = {k: v for k, v in data.items() if k in allowed}
    
    # Debug: check if plan exists
    from app.models.college_plan import CollegePlan
    plan = CollegePlan.find_by_id(plan_id)
    if not plan:
        logger.error(f"Plan not found with id: {plan_id}")
        return jsonify({'error': 'Plan not found'}), 404
    
    updated = CollegePlan.update(plan_id, updates)
    if updated:
        return jsonify({'message': 'College plan updated'}), 200
    else:
        logger.error(f"Update failed for plan {plan_id} with updates {updates}")
        return jsonify({'error': 'Update failed (no changes?)'}), 400


@superadmin_plans_bp.route('/college-plans/<plan_id>', methods=['DELETE'])
@jwt_required()
@role_required('super_admin')
def delete_college_plan(plan_id):
    # Optional: soft delete by setting is_active=False
    deleted = CollegePlan.delete(plan_id)
    if deleted:
        return jsonify({'message': 'College plan deleted'}), 200
    return jsonify({'error': 'Plan not found'}), 404

# ========== Student Plan (Credit Packs) CRUD ==========
@superadmin_plans_bp.route('/student-plans', methods=['GET'])
@jwt_required()
@role_required('super_admin')
def get_student_plans():
    plans = StudentPlan.get_all(include_inactive=True)
    for p in plans:
        p['_id'] = str(p['_id'])
    return jsonify(plans), 200

@superadmin_plans_bp.route('/student-plans', methods=['POST'])
@jwt_required()
@role_required('super_admin')
def create_student_plan():
    data = request.get_json()
    required = ['plan_name', 'price', 'credits', 'description']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400
    plan_data = {
        'plan_name': data['plan_name'],
        'price': data['price'],
        'credits': data['credits'],
        'description': data.get('description', ''),
        'features': data.get('features', []),
        'is_active': data.get('is_active', True)
    }
    try:
        plan_id = StudentPlan.create(plan_data)
        return jsonify({'message': 'Student plan created', 'plan_id': str(plan_id)}), 201
    except Exception as e:
        logger.error(f"Student plan creation failed: {e}")
        return jsonify({'error': 'Failed to create plan'}), 500

@superadmin_plans_bp.route('/student-plans/<plan_id>', methods=['PUT'])
@jwt_required()
@role_required('super_admin')
def update_student_plan(plan_id):
    data = request.get_json()
    allowed = ['plan_name', 'price', 'credits', 'description', 'features', 'is_active']
    updates = {k: v for k, v in data.items() if k in allowed}
    updated = StudentPlan.update(plan_id, updates)
    if updated:
        return jsonify({'message': 'Student plan updated'}), 200
    return jsonify({'error': 'Plan not found or update failed'}), 404

@superadmin_plans_bp.route('/student-plans/<plan_id>', methods=['DELETE'])
@jwt_required()
@role_required('super_admin')
def delete_student_plan(plan_id):
    deleted = StudentPlan.delete(plan_id)
    if deleted:
        return jsonify({'message': 'Student plan deleted'}), 200
    return jsonify({'error': 'Plan not found'}), 404

