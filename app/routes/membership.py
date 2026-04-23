# backend/app/routes/membership.py
"""
Membership plan and subscription routes.
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
import razorpay
from app.database import get_db
from app.models.activity_log import ActivityLog
from app.models.membership_plan import MembershipPlan
from app.models.subscription import Subscription
from app.models.college import College
from app.models.admin import Admin
from app.models.activity_log import ActivityLog
from app.utils.validators import validate_object_id

membership_bp = Blueprint('membership', __name__)
logger = logging.getLogger(__name__)

def get_razorpay_client():
    return razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))

@membership_bp.route('/plans', methods=['GET'])
def get_plans():
    """Get all membership plans."""
    plans = MembershipPlan.get_all_active()
    for p in plans:
        p['_id'] = str(p['_id'])
    return jsonify(plans), 200

@membership_bp.route('/subscribe', methods=['POST'])
@jwt_required()
def subscribe():
    """College admin subscribes to a plan."""
    admin_id = get_jwt_identity()
    admin = Admin.find_by_id(admin_id)
    if not admin or admin.get('role') != 'college_admin':
        return jsonify({'error': 'Only college admins can subscribe'}), 403

    college_id = admin.get('college_id')
    if not college_id:
        return jsonify({'error': 'Admin not associated with a college'}), 400

    data = request.get_json()
    plan_id = data.get('plan_id')
    if not plan_id or not validate_object_id(plan_id):
        return jsonify({'error': 'Invalid plan_id'}), 400

    plan = MembershipPlan.find_by_id(plan_id)
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404

    # Check if college already has an active subscription
    existing = Subscription.find_active_by_college(college_id)
    if existing:
        return jsonify({'error': 'College already has an active subscription'}), 400

    # Create Razorpay order for subscription payment
    amount = plan['price'] * 100  # convert to paise
    try:
        client = get_razorpay_client()
        order_data = {
            'amount': int(amount),
            'currency': 'INR',
            'receipt': f'sub_{college_id}_{plan_id}',
            'payment_capture': 1
        }
        order = client.order.create(data=order_data)
        order_id = order['id']
    except Exception as e:
        logger.error(f"Razorpay order creation for subscription failed: {e}")
        return jsonify({'error': 'Payment order creation failed'}), 500

    # Save payment record? For simplicity, we'll handle webhook to activate subscription.
    # We'll store subscription in pending state.
    sub_data = {
        'college_id': ObjectId(college_id),
        'plan_id': ObjectId(plan_id),
        'duration_days': plan['duration_days'],
        'status': 'pending',
        'razorpay_order_id': order_id,
        'amount': amount,
        'currency': 'INR'
    }
    from app.database import get_db
    db = get_db()
    result = db.subscriptions.insert_one(sub_data)
    subscription_id = result.inserted_id

    return jsonify({
        'order_id': order_id,
        'razorpay_key': current_app.config['RAZORPAY_KEY_ID'],
        'amount': amount,
        'currency': 'INR',
        'subscription_id': str(subscription_id)
    }), 201

# Webhook for subscription payment
@membership_bp.route('/payment-webhook', methods=['POST'])
def subscription_payment_webhook():
    """Handle Razorpay webhook for subscription payment."""
    data = request.get_json()
    webhook_secret = current_app.config['RAZORPAY_WEBHOOK_SECRET']
    signature = request.headers.get('X-Razorpay-Signature')
    if not signature:
        return jsonify({'error': 'Missing signature'}), 400

    # Verify signature (same as before)
    import hmac, hashlib
    body = request.get_data(as_text=True)
    expected_signature = hmac.new(
        key=webhook_secret.encode('utf-8'),
        msg=body.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return jsonify({'error': 'Invalid signature'}), 400

    event = data.get('event')
    if event == 'payment.captured':
        payload = data.get('payload', {})
        payment = payload.get('payment', {})
        order_id = payment.get('order_id')
        payment_id = payment.get('id')

        # Find subscription with this order_id
        db = get_db()
        subscription = db.subscriptions.find_one({'razorpay_order_id': order_id})
        if subscription and subscription['status'] == 'pending':
            # Activate subscription
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=subscription['duration_days'])
            db.subscriptions.update_one(
                {'_id': subscription['_id']},
                {'$set': {
                    'status': 'active',
                    'start_date': start_date,
                    'end_date': end_date,
                    'razorpay_payment_id': payment_id,
                    'paid_at': datetime.utcnow()
                }}
            )
            # Log
            ActivityLog.log(subscription['college_id'], 'college', 'subscription_activated', 'subscription', {'subscription_id': str(subscription['_id'])})
        return jsonify({'status': 'success'}), 200

    return jsonify({'status': 'ignored'}), 200

@membership_bp.route('/subscription/status', methods=['GET'])
@jwt_required()
def subscription_status():
    """Get current subscription status for admin's college."""
    admin_id = get_jwt_identity()
    admin = Admin.find_by_id(admin_id)
    if not admin or admin.get('role') != 'college_admin':
        return jsonify({'error': 'Access denied'}), 403

    college_id = admin.get('college_id')
    if not college_id:
        return jsonify({'error': 'Admin not associated with a college'}), 400

    sub = Subscription.find_active_by_college(college_id)
    if sub:
        sub['_id'] = str(sub['_id'])
        sub['college_id'] = str(sub['college_id'])
        sub['plan_id'] = str(sub['plan_id'])
        # Add plan details
        plan = MembershipPlan.find_by_id(sub['plan_id'])
        if plan:
            sub['plan_name'] = plan.get('plan_name')
        return jsonify(sub), 200
    else:
        return jsonify({'status': 'no_active_subscription'}), 200