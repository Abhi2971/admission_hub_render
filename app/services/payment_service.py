"""
Payment processing with Razorpay.
"""
import razorpay
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def get_razorpay_client():
    """Get Razorpay client instance."""
    return razorpay.Client(auth=(
        current_app.config['RAZORPAY_KEY_ID'],
        current_app.config['RAZORPAY_KEY_SECRET']
    ))

def create_order(amount, currency='INR', receipt=None):
    """Create a Razorpay order."""
    client = get_razorpay_client()
    data = {
        'amount': int(amount),
        'currency': currency,
        'receipt': receipt,
        'payment_capture': 1
    }
    order = client.order.create(data=data)
    return order

def create_credit_order(student_id, amount, credits):
    """Create a Razorpay order for credit purchase."""
    # amount is in rupees, convert to paise
    receipt = f"credits_{student_id}_{credits}"
    return create_order(amount * 100, receipt=receipt)

def create_plan_order(plan_id, college_id):
    from app.models.college_plan import CollegePlan
    plan = CollegePlan.find_by_id(plan_id)
    if not plan:
        return None
    # Shorten receipt: use last 6 chars of each ID
    short_plan = str(plan_id)[-6:]
    short_college = str(college_id)[-6:]
    receipt = f"plan_{short_plan}_clg_{short_college}"
    return create_order(plan['price'] * 100, receipt=receipt)

def verify_payment(order_id, payment_id, signature):
    """Verify payment signature."""
    client = get_razorpay_client()
    params_dict = {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature
    }
    return client.utility.verify_payment_signature(params_dict)