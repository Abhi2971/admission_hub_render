from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from app.models.college_subscription import CollegeSubscription
from app.database import get_db
from bson.objectid import ObjectId
from datetime import datetime


def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()

            if claims.get('role') not in roles:
                return jsonify({'error': 'Forbidden'}), 403

            return fn(*args, **kwargs)
        return decorator
    return wrapper


def subscription_required(feature=None):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()

            role = claims.get('role')
            if role not in ['college_admin', 'course_admin']:
                return jsonify({'error': 'Forbidden'}), 403

            college_id = claims.get('college_id')
            if not college_id:
                return jsonify({'error': 'No college associated'}), 403

            # Safe ObjectId conversion
            try:
                college_obj_id = ObjectId(college_id)
            except Exception:
                return jsonify({'error': 'Invalid college ID'}), 400

            # Course admins don't need subscription for basic course management
            if role == 'course_admin':
                return fn(*args, **kwargs)

            sub = CollegeSubscription.find_active_by_college(college_id)
            if not sub:
                return jsonify({'error': 'Active subscription required'}), 403

            # Optional expiry check
            if sub.get('end_date') and sub['end_date'] < datetime.utcnow():
                return jsonify({'error': 'Subscription expired'}), 403

            plan = sub.get('plan', {})
            db = get_db()

            # Feature checks
            if feature == 'courses' and plan.get('max_courses'):
                count = db.courses.count_documents({'college_id': college_obj_id})
                if count >= plan['max_courses']:
                    return jsonify({'error': 'Course limit reached for your plan'}), 403

            if feature == 'students' and plan.get('max_students'):
                count = db.students.count_documents({
                    'college_id': college_obj_id,
                    'created_by': 'admin'
                })
                if count >= plan['max_students']:
                    return jsonify({'error': 'Student limit reached for your plan'}), 403

            return fn(*args, **kwargs)

        return decorator
    return wrapper