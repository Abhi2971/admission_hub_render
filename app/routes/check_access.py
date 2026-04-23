# backend/app/routes/check_access.py
"""
AI Access check routes for all roles.
Checks if user has AI access based on their subscription.
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.plan import Subscription
from app.models.college_subscription import CollegeSubscription
from app.models.student_credit import StudentCredit

check_access_bp = Blueprint('check_access', __name__)


@check_access_bp.route('/api/check-access', methods=['GET'])
@jwt_required()
def check_my_access():
    """Check current user's access based on their role and subscription."""
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get('role')
    
    result = {
        'has_ai_access': False,
        'ai_credits': 0,
        'subscription': None,
        'role': role
    }
    
    try:
        if role == 'super_admin':
            # SuperAdmin always has full access
            result['has_ai_access'] = True
            result['ai_credits'] = -1  # Unlimited
            return jsonify(result), 200
        
        elif role == 'university_admin':
            university_id = claims.get('university_id')
            if university_id:
                sub = Subscription.find_active(university_id, 'university')
                if sub and sub.get('plan'):
                    result['subscription'] = {
                        'plan_name': sub['plan'].get('plan_name'),
                        'has_ai': sub['plan'].get('features', {}).get('ai_enabled', False),
                        'ai_credits': sub['plan'].get('features', {}).get('ai_credits', 0)
                    }
                    result['has_ai_access'] = sub['plan'].get('features', {}).get('ai_enabled', False)
                    result['ai_credits'] = sub['plan'].get('features', {}).get('ai_credits', 0)
            return jsonify(result), 200
        
        elif role == 'college_admin':
            college_id = claims.get('college_id')
            university_id = claims.get('university_id')
            
            # First check college subscription from CollegeSubscription model
            if college_id:
                from bson.objectid import ObjectId
                try:
                    college_sub = CollegeSubscription.find_active_by_college(ObjectId(college_id))
                    if college_sub and college_sub.get('plan'):
                        features = college_sub['plan'].get('features', {})
                        result['subscription'] = {
                            'plan_name': college_sub['plan'].get('plan_name'),
                            'has_ai': features.get('ai_enabled', False),
                            'ai_credits': features.get('ai_credits', 0)
                        }
                        result['has_ai_access'] = features.get('ai_enabled', False)
                        result['ai_credits'] = features.get('ai_credits', 0)
                        return jsonify(result), 200
                except Exception as e:
                    print(f"Error checking college subscription: {e}")
            
            # Also check unified Subscription model
            if college_id:
                sub = Subscription.find_active(college_id, 'college')
                if sub and sub.get('plan') and sub['plan'].get('features', {}).get('ai_enabled'):
                    result['subscription'] = {
                        'plan_name': sub['plan'].get('plan_name'),
                        'has_ai': True,
                        'ai_credits': sub['plan'].get('features', {}).get('ai_credits', 0)
                    }
                    result['has_ai_access'] = True
                    result['ai_credits'] = sub['plan'].get('features', {}).get('ai_credits', 0)
                    return jsonify(result), 200
            
            # Fallback to university subscription
            if university_id:
                sub = Subscription.find_active(university_id, 'university')
                if sub and sub.get('plan'):
                    result['subscription'] = {
                        'plan_name': sub['plan'].get('plan_name'),
                        'source': 'university',
                        'has_ai': sub['plan'].get('features', {}).get('ai_enabled', False),
                        'ai_credits': sub['plan'].get('features', {}).get('ai_credits', 0)
                    }
                    result['has_ai_access'] = sub['plan'].get('features', {}).get('ai_enabled', False)
                    result['ai_credits'] = sub['plan'].get('features', {}).get('ai_credits', 0)
            return jsonify(result), 200
        
        elif role == 'course_admin':
            college_id = claims.get('college_id')
            university_id = claims.get('university_id')
            
            # Check college subscription from CollegeSubscription model first
            if college_id:
                from bson.objectid import ObjectId
                try:
                    college_sub = CollegeSubscription.find_active_by_college(ObjectId(college_id))
                    if college_sub and college_sub.get('plan'):
                        features = college_sub['plan'].get('features', {})
                        result['subscription'] = {
                            'plan_name': college_sub['plan'].get('plan_name'),
                            'has_ai': features.get('ai_enabled', False),
                            'ai_credits': features.get('ai_credits', 0)
                        }
                        result['has_ai_access'] = features.get('ai_enabled', False)
                        result['ai_credits'] = features.get('ai_credits', 0)
                        return jsonify(result), 200
                except Exception as e:
                    print(f"Error checking college subscription: {e}")
            
            # Fallback to unified Subscription
            if college_id:
                sub = Subscription.find_active(college_id, 'college')
                if sub and sub.get('plan') and sub['plan'].get('features', {}).get('ai_enabled'):
                    result['subscription'] = {
                        'plan_name': sub['plan'].get('plan_name'),
                        'has_ai': True,
                        'ai_credits': sub['plan'].get('features', {}).get('ai_credits', 0)
                    }
                    result['has_ai_access'] = True
                    result['ai_credits'] = sub['plan'].get('features', {}).get('ai_credits', 0)
                    return jsonify(result), 200
            
            # Fallback to university
            if university_id:
                sub = Subscription.find_active(university_id, 'university')
                if sub and sub.get('plan'):
                    result['subscription'] = {
                        'plan_name': sub['plan'].get('plan_name'),
                        'source': 'university',
                        'has_ai': sub['plan'].get('features', {}).get('ai_enabled', False),
                        'ai_credits': sub['plan'].get('features', {}).get('ai_credits', 0)
                    }
                    result['has_ai_access'] = sub['plan'].get('features', {}).get('ai_enabled', False)
                    result['ai_credits'] = sub['plan'].get('features', {}).get('ai_credits', 0)
            return jsonify(result), 200
        
        elif role == 'student':
            # Check student's AI credits (minimum 50 required)
            credits = StudentCredit.get_balance(user_id)
            result['ai_credits'] = credits
            result['has_ai_access'] = credits >= 50
            result['min_required'] = 50
            return jsonify(result), 200
        
        elif role in ['global_support', 'local_support']:
            # Support staff always have access
            result['has_ai_access'] = True
            result['ai_credits'] = -1
            return jsonify(result), 200
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'has_ai_access': False}), 500
