import logging
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.student_credit import StudentCredit
from app.services.payment_service import create_credit_order
from app.models.activity_log import ActivityLog

credits_bp = Blueprint('credits', __name__)
logger = logging.getLogger(__name__)

@credits_bp.route('/balance', methods=['GET'])
@jwt_required()
def get_balance():
    student_id = get_jwt_identity()
    credit = StudentCredit.find_by_student(student_id)
    balance = credit['balance'] if credit else 0
    return jsonify({'balance': balance}), 200

@credits_bp.route('/purchase', methods=['POST'])
@jwt_required()
def purchase_credits():
    student_id = get_jwt_identity()
    data = request.get_json()
    amount = data.get('amount')  # in rupees
    credits = data.get('credits')
    if not amount or not credits:
        return jsonify({'error': 'amount and credits required'}), 400
    try:
        order = create_credit_order(student_id, amount, credits)
        return jsonify({
            'order_id': order['id'],
            'razorpay_key': current_app.config['RAZORPAY_KEY_ID'],
            'amount': amount * 100,
            'currency': 'INR'
        }), 201
    except Exception as e:
        logger.error(f"Credit purchase error: {e}")
        return jsonify({'error': 'Failed to initiate payment'}), 500

# Webhook for credit purchase (to be implemented similarly to payment webhooks)
@credits_bp.route('/webhook', methods=['POST'])
def payment_webhook():
    # Verify and add credits
    # Similar to previous webhook implementation
    pass