import logging
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.college_plan import CollegePlan
from app.models.college_subscription import CollegeSubscription
from app.models.admin import Admin
from app.services.payment_service import create_plan_order

subscription_bp = Blueprint('college_subscription', __name__)
logger = logging.getLogger(__name__)

@subscription_bp.route('/plans', methods=['GET'])
def list_plans():
    plans = CollegePlan.get_all()
    for p in plans:
        p['_id'] = str(p['_id'])
    return jsonify(plans), 200

@subscription_bp.route('/subscribe', methods=['POST'])
@jwt_required()
def subscribe():
    admin_id = get_jwt_identity()
    admin = Admin.find_by_id(admin_id)
    if not admin or admin.get('role') != 'college_admin':
        return jsonify({'error': 'Only college admins can subscribe'}), 403
    college_id = admin.get('college_id')
    # Check if already active subscription
    existing = CollegeSubscription.find_active_by_college(college_id)
    if existing:
        return jsonify({'error': 'College already has an active subscription'}), 400
    data = request.get_json()
    plan_id = data.get('plan_id')
    if not plan_id:
        return jsonify({'error': 'plan_id required'}), 400
    order = create_plan_order(plan_id, college_id)
    if not order:
        return jsonify({'error': 'Invalid plan'}), 400
    return jsonify({
        'order_id': order['id'],
        'razorpay_key': current_app.config['RAZORPAY_KEY_ID'],
        'amount': order['amount'],
        'currency': order['currency']
    }), 201

@subscription_bp.route('/webhook', methods=['POST'])
def subscription_webhook():
    # Handle payment success and activate subscription
    # This should be implemented similarly to previous webhooks
    return jsonify({'status': 'ignored'}), 200

@subscription_bp.route('/status', methods=['GET'])
@jwt_required()
def subscription_status():
    from bson.objectid import ObjectId
    admin_id = get_jwt_identity()
    try:
        admin = Admin.find_by_id(ObjectId(admin_id))
    except Exception:
        return jsonify({'error': 'Invalid admin ID'}), 400
    if not admin or admin.get('role') != 'college_admin':
        return jsonify({'error': 'Access denied'}), 403
    college_id = admin.get('college_id')
    sub = CollegeSubscription.find_active_by_college(college_id)
    if sub:
        sub['_id'] = str(sub['_id'])
        sub['college_id'] = str(sub['college_id'])
        sub['plan_id'] = str(sub['plan_id'])
        if 'plan' in sub:
            sub['plan']['_id'] = str(sub['plan']['_id'])
        return jsonify(sub), 200
    return jsonify({'status': 'no_active_subscription'}), 200

@subscription_bp.route('/history', methods=['GET'])
@jwt_required()
def subscription_history():
    """Get subscription history for the college."""
    from bson.objectid import ObjectId
    admin_id = get_jwt_identity()
    try:
        admin = Admin.find_by_id(ObjectId(admin_id))
    except Exception:
        return jsonify({'error': 'Invalid admin ID'}), 400
    if not admin or admin.get('role') != 'college_admin':
        return jsonify({'error': 'Access denied'}), 403
    college_id = admin.get('college_id')
    history = CollegeSubscription.find_history_by_college(college_id)
    return jsonify(history), 200