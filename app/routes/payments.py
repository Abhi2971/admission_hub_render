# backend/app/routes/payments.py
"""
Payment processing with Razorpay.
"""
import logging
import hmac
import hashlib
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
import razorpay
from app.models.payment import Payment
from app.models.application import Application
from app.models.course import Course
from app.models.activity_log import ActivityLog
from app.utils.validators import validate_object_id
from app.services.payment_service import create_order, verify_payment

payments_bp = Blueprint('payments', __name__)
logger = logging.getLogger(__name__)

# Initialize Razorpay client
def get_razorpay_client():
    return razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))

@payments_bp.route('/create', methods=['POST'])
@jwt_required()
def create_payment_order():
    """Create a Razorpay order for an application."""
    student_id = get_jwt_identity()
    data = request.get_json()
    application_id = data.get('application_id')
    amount = data.get('amount')  # in paise (INR)

    if not application_id or not amount:
        return jsonify({'error': 'application_id and amount required'}), 400
    if not validate_object_id(application_id):
        return jsonify({'error': 'Invalid application ID'}), 400

    # Verify application belongs to student and is in 'offered' status
    app = Application.find_by_id(application_id)
    if not app or str(app['student_id']) != student_id:
        return jsonify({'error': 'Invalid application'}), 403
    if app['status'] != 'offered':
        return jsonify({'error': 'Application not in offered state'}), 400

    # Create Razorpay order
    try:
        client = get_razorpay_client()
        order_data = {
            'amount': int(amount),
            'currency': 'INR',
            'receipt': f'app_{application_id}',
            'payment_capture': 1  # auto-capture
        }
        order = client.order.create(data=order_data)
        order_id = order['id']
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        return jsonify({'error': 'Payment order creation failed'}), 500

    # Save payment record
    payment_data = {
        'student_id': ObjectId(student_id),
        'application_id': ObjectId(application_id),
        'razorpay_order_id': order_id,
        'amount': amount,
        'currency': 'INR',
        'status': 'created'
    }
    try:
        payment_id = Payment.create(payment_data)
        ActivityLog.log(student_id, 'student', 'payment_order_created', 'payment', {'payment_id': str(payment_id), 'order_id': order_id})
        return jsonify({
            'order_id': order_id,
            'razorpay_key': current_app.config['RAZORPAY_KEY_ID'],
            'amount': amount,
            'currency': 'INR',
            'payment_id': str(payment_id)
        }), 201
    except Exception as e:
        logger.error(f"Payment record creation failed: {e}")
        return jsonify({'error': 'Failed to save payment record'}), 500

@payments_bp.route('/verify', methods=['POST'])
def verify_payment_webhook():
    """Verify payment via Razorpay webhook."""
    data = request.get_json()
    # Webhook signature verification
    webhook_secret = current_app.config['RAZORPAY_WEBHOOK_SECRET']
    signature = request.headers.get('X-Razorpay-Signature')
    if not signature:
        return jsonify({'error': 'Missing signature'}), 400

    # Verify signature
    body = request.get_data(as_text=True)
    expected_signature = hmac.new(
        key=webhook_secret.encode('utf-8'),
        msg=body.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return jsonify({'error': 'Invalid signature'}), 400

    # Process payment
    event = data.get('event')
    if event == 'payment.captured':
        payload = data.get('payload', {})
        payment = payload.get('payment', {})
        order_id = payment.get('order_id')
        payment_id = payment.get('id')
        # Update payment record
        updated = Payment.update_after_success(order_id, payment_id, 'success')
        if updated:
            # Find payment record to get application_id
            payment_record = Payment.find_by_order_id(order_id)
            if payment_record:
                application_id = payment_record.get('application_id')
                # Update application status to 'confirmed'
                Application.update_status(application_id, 'confirmed')
                # Decrement available seats
                app = Application.find_by_id(application_id)
                if app:
                    Course.decrement_available_seats(app['course_id'])
                # Log activity
                ActivityLog.log(payment_record['student_id'], 'student', 'payment_success', 'payment', {'payment_id': payment_id})
        return jsonify({'status': 'success'}), 200

    return jsonify({'status': 'ignored'}), 200

@payments_bp.route('/history', methods=['GET'])
@jwt_required()
def get_payment_history():
    """Get payment history for the current student."""
    student_id = get_jwt_identity()
    payments = Payment.find_by_student(student_id)
    for p in payments:
        p['_id'] = str(p['_id'])
        p['student_id'] = str(p['student_id'])
        p['application_id'] = str(p['application_id'])
        # Optionally add application details
        app = Application.find_by_id(p['application_id'])
        if app:
            p['college_id'] = str(app['college_id'])
            p['course_id'] = str(app['course_id'])
    return jsonify(payments), 200