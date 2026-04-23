# backend/app/routes/university_admin.py
"""
University admin routes.
UniversityAdmin can create Colleges and College Admins under their university.

Hierarchy:
UniversityAdmin → Creates Colleges → Creates College Admins
"""
from datetime import datetime
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson.objectid import ObjectId
from app.models.university import University
from app.models.college import College
from app.models.admin import Admin
from app.models.activity_log import ActivityLog
from app.utils.validators import validate_object_id, validate_email
from app.middlewares.auth_middleware import role_required


university_admin_bp = Blueprint('university_admin', __name__)
logger = logging.getLogger(__name__)

def get_university_id_from_token():
    """Get university_id from JWT token."""
    claims = get_jwt()
    return claims.get('university_id')

def convert_objectid(obj):
    if isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    if isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

# ============================================================
# MY UNIVERSITY INFO
# ============================================================

@university_admin_bp.route('/my-university', methods=['GET'])
@jwt_required()
@role_required('university_admin')
def get_my_university():
    """Get the university this admin belongs to."""
    university_id = get_university_id_from_token()
    if not university_id:
        return jsonify({'error': 'University ID not found in token'}), 400
    
    university = University.find_by_id(university_id)
    if not university:
        return jsonify({'error': 'University not found'}), 404
    
    university['_id'] = str(university['_id'])
    return jsonify({'university': university}), 200

# ============================================================
# COLLEGE MANAGEMENT (UniversityAdmin creates Colleges)
# ============================================================

@university_admin_bp.route('/colleges', methods=['POST'])
@jwt_required()
@role_required('university_admin')
def create_college():
    """Create a new college under this university."""
    university_id = get_university_id_from_token()
    if not university_id:
        return jsonify({'error': 'University ID not found'}), 400

    data = request.get_json()
    required = ['name', 'code', 'address', 'city', 'state', 'contact_email', 'contact_phone']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400

    existing = College.find_by_code(data['code'])
    if existing:
        return jsonify({'error': 'College code already exists'}), 409

    college_data = {
        'name': data['name'],
        'code': data['code'],
        'address': data['address'],
        'city': data['city'],
        'state': data['state'],
        'contact_email': data['contact_email'],
        'contact_phone': data['contact_phone'],
        'website': data.get('website', ''),
        'description': data.get('description', ''),
        'university_id': ObjectId(university_id),
        'created_by': 'university_admin'
    }
    try:
        college_id = College.create(college_data)
        admin_id = get_jwt_identity()
        ActivityLog.log(admin_id, 'university_admin', 'create_college', 'college', {
            'college_id': str(college_id),
            'university_id': university_id
        })
        return jsonify({'message': 'College created', 'college_id': str(college_id)}), 201
    except Exception as e:
        logger.error(f"College creation failed: {e}")
        return jsonify({'error': 'Failed to create college'}), 500

@university_admin_bp.route('/colleges', methods=['GET'])
@jwt_required()
@role_required('university_admin')
def get_my_colleges():
    """Get all colleges under this university."""
    university_id = get_university_id_from_token()
    if not university_id:
        return jsonify({'error': 'University ID not found'}), 400
    
    try:
        db = get_db()
        colleges = list(db.colleges.find({'university_id': ObjectId(university_id)}))
        for college in colleges:
            college['_id'] = str(college['_id'])
            if college.get('university_id'):
                college['university_id'] = str(college['university_id'])
        return jsonify({'colleges': colleges}), 200
    except Exception as e:
        logger.error(f"Error fetching colleges: {e}")
        return jsonify({'error': 'Failed to fetch colleges'}), 500

@university_admin_bp.route('/colleges/<college_id>', methods=['PUT'])
@jwt_required()
@role_required('university_admin')
def update_college(college_id):
    """Update college details."""
    university_id = get_university_id_from_token()
    if not validate_object_id(college_id):
        return jsonify({'error': 'Invalid college ID'}), 400

    college = College.find_by_id(college_id)
    if not college:
        return jsonify({'error': 'College not found'}), 404

    # Verify college belongs to this university
    if str(college.get('university_id')) != university_id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    allowed = ['name', 'address', 'city', 'state', 'contact_email', 'contact_phone', 'website', 'description']
    updates = {k: v for k, v in data.items() if k in allowed}

    if 'code' in updates and updates['code'] != college.get('code'):
        existing = College.find_by_code(updates['code'])
        if existing and str(existing['_id']) != college_id:
            return jsonify({'error': 'College code already in use'}), 409

    updated = College.update(college_id, updates)
    if updated:
        admin_id = get_jwt_identity()
        ActivityLog.log(admin_id, 'university_admin', 'update_college', 'college', {'college_id': college_id})
        return jsonify({'message': 'College updated'}), 200
    return jsonify({'error': 'Update failed'}), 500

@university_admin_bp.route('/colleges/<college_id>', methods=['GET'])
@jwt_required()
@role_required('university_admin')
def get_college(college_id):
    """Get single college details."""
    university_id = get_university_id_from_token()
    if not validate_object_id(college_id):
        return jsonify({'error': 'Invalid college ID'}), 400

    college = College.find_by_id(college_id)
    if not college:
        return jsonify({'error': 'College not found'}), 404

    if str(college.get('university_id')) != university_id:
        return jsonify({'error': 'Unauthorized'}), 403

    college['_id'] = str(college['_id'])
    return jsonify({'college': college}), 200

# ============================================================
# COLLEGE ADMIN MANAGEMENT
# ============================================================

@university_admin_bp.route('/college-admins', methods=['POST'])
@jwt_required()
@role_required('university_admin')
def create_college_admin():
    """Create a new college admin for a college in this university."""
    university_id = get_university_id_from_token()
    data = request.get_json()
    
    required = ['name', 'email', 'password', 'college_id']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400

    if not validate_email(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400

    existing = Admin.find_by_email(data['email'])
    if existing:
        return jsonify({'error': 'Email already in use'}), 409

    # Verify college belongs to this university
    college = College.find_by_id(data['college_id'])
    if not college:
        return jsonify({'error': 'College not found'}), 404
    if str(college.get('university_id')) != university_id:
        return jsonify({'error': 'Unauthorized to create admin for this college'}), 403

    admin_data = {
        'name': data['name'],
        'email': data['email'],
        'password': data['password'],
        'role': 'college_admin',
        'college_id': ObjectId(data['college_id']),
        'university_id': ObjectId(university_id),
        'mobile': data.get('mobile', '')
    }
    try:
        admin_id = Admin.create(admin_data)
        ua_id = get_jwt_identity()
        ActivityLog.log(ua_id, 'university_admin', 'create_college_admin', 'admin', {
            'admin_id': str(admin_id),
            'college_id': data['college_id']
        })
        return jsonify({'message': 'College admin created', 'admin_id': str(admin_id)}), 201
    except Exception as e:
        logger.error(f"College admin creation failed: {e}")
        return jsonify({'error': 'Failed to create college admin'}), 500

@university_admin_bp.route('/college-admins', methods=['GET'])
@jwt_required()
@role_required('university_admin')
def get_college_admins():
    """Get all college admins under this university."""
    university_id = get_university_id_from_token()
    if not university_id:
        return jsonify({'error': 'University ID not found'}), 400
    
    try:
        db = get_db()
        # Get all college_ids under this university
        colleges = list(db.colleges.find({'university_id': ObjectId(university_id)}, {'_id': 1}))
        college_ids = [c['_id'] for c in colleges]
        
        # Get admins for those colleges
        admins = list(db.admins.find({
            'role': 'college_admin',
            'college_id': {'$in': college_ids}
        }))
        for admin in admins:
            admin['_id'] = str(admin['_id'])
            if admin.get('college_id'):
                admin['college_id'] = str(admin['college_id'])
            admin.pop('password_hash', None)
        return jsonify(admins), 200
    except Exception as e:
        logger.error(f"Error fetching college admins: {e}")
        return jsonify({'error': 'Failed to fetch college admins'}), 500

# ============================================================
# ANALYTICS
# ============================================================

@university_admin_bp.route('/analytics', methods=['GET'])
@jwt_required()
@role_required('university_admin')
def get_analytics():
    """Get analytics for this university (for charts)."""
    university_id = get_university_id_from_token()
    if not university_id:
        return jsonify({'error': 'University ID not found'}), 400
    
    try:
        db = get_db()
        
        # Get all colleges under this university
        colleges = list(db.colleges.find({'university_id': ObjectId(university_id)}, {'_id': 1, 'name': 1}))
        college_ids = [c['_id'] for c in colleges]
        
        # Applications by status
        status_data = {}
        for status in ['applied', 'under_review', 'shortlisted', 'rejected', 'offered', 'confirmed']:
            status_data[status] = db.applications.count_documents({
                'college_id': {'$in': college_ids},
                'status': status
            })
        
        # Applications by college
        college_apps = db.applications.aggregate([
            {'$match': {'college_id': {'$in': college_ids}}},
            {'$group': {'_id': '$college_id', 'count': {'$sum': 1}}}
        ])
        college_data = {}
        for d in college_apps:
            college_name = next((c['name'] for c in colleges if c['_id'] == d['_id']), 'Unknown')
            college_data[college_name] = d['count']
        
        # Applications over time (last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        daily_apps = db.applications.aggregate([
            {'$match': {
                'college_id': {'$in': college_ids},
                'applied_at': {'$gte': thirty_days_ago}
            }},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$applied_at'}},
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}}
        ])
        timeline_data = [{'date': d['_id'], 'count': d['count']} for d in daily_apps]
        
        return jsonify({
            'status_distribution': status_data,
            'college_distribution': college_data,
            'timeline': timeline_data
        }), 200
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        return jsonify({'error': 'Failed to fetch analytics'}), 500

# ============================================================
# STATISTICS
# ============================================================

@university_admin_bp.route('/stats', methods=['GET'])
@jwt_required()
@role_required('university_admin')
def get_stats():
    """Get statistics for this university."""
    university_id = get_university_id_from_token()
    if not university_id:
        return jsonify({'error': 'University ID not found'}), 400
    
    try:
        db = get_db()
        
        # Count colleges
        college_count = db.colleges.count_documents({'university_id': ObjectId(university_id)})
        
        # Get college IDs
        colleges = list(db.colleges.find({'university_id': ObjectId(university_id)}, {'_id': 1}))
        college_ids = [c['_id'] for c in colleges]
        
        # Count college admins
        college_admin_count = db.admins.count_documents({
            'role': 'college_admin',
            'college_id': {'$in': college_ids}
        })
        
        # Count department admins (course_admin)
        dept_admin_count = db.admins.count_documents({
            'role': 'course_admin',
            'college_id': {'$in': college_ids}
        })
        
        # Count applications
        application_count = db.applications.count_documents({
            'college_id': {'$in': college_ids}
        })
        
        return jsonify({
            'college_count': college_count,
            'college_admin_count': college_admin_count,
            'department_admin_count': dept_admin_count,
            'application_count': application_count
        }), 200
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

# ============================================================
# UNIVERSITY SUPPORT MANAGEMENT
# ============================================================

@university_admin_bp.route('/support-users', methods=['POST'])
@jwt_required()
@role_required('university_admin')
def create_support_user():
    """Create a new University Support (local_support) user."""
    university_id = get_university_id_from_token()
    if not university_id:
        return jsonify({'error': 'University ID not found'}), 400

    data = request.get_json()
    required = ['name', 'email', 'password']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400

    if not validate_email(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400

    existing = Admin.find_by_email(data['email'])
    if existing:
        return jsonify({'error': 'Email already in use'}), 409

    admin_data = {
        'name': data['name'],
        'email': data['email'],
        'password': data['password'],
        'role': 'local_support',
        'university_id': ObjectId(university_id),
        'mobile': data.get('mobile', '')
    }
    try:
        admin_id = Admin.create(admin_data)
        ua_id = get_jwt_identity()
        ActivityLog.log(ua_id, 'university_admin', 'create_support_user', 'admin', {
            'admin_id': str(admin_id),
            'support_type': 'university_support'
        })
        return jsonify({'message': 'University support user created', 'admin_id': str(admin_id)}), 201
    except Exception as e:
        logger.error(f"Support user creation failed: {e}")
        return jsonify({'error': 'Failed to create support user'}), 500

@university_admin_bp.route('/support-users', methods=['GET'])
@jwt_required()
@role_required('university_admin')
def get_support_users():
    """Get all University Support users for this university."""
    university_id = get_university_id_from_token()
    if not university_id:
        return jsonify({'error': 'University ID not found'}), 400
    
    try:
        db = get_db()
        users = list(db.admins.find({
            'role': 'local_support',
            'university_id': ObjectId(university_id)
        }))
        for user in users:
            user['_id'] = str(user['_id'])
            if user.get('university_id'):
                user['university_id'] = str(user['university_id'])
            user.pop('password_hash', None)
        return jsonify(users), 200
    except Exception as e:
        logger.error(f"Error fetching support users: {e}")
        return jsonify({'error': 'Failed to fetch support users'}), 500

@university_admin_bp.route('/support-users/<user_id>', methods=['DELETE'])
@jwt_required()
@role_required('university_admin')
def delete_support_user(user_id):
    """Delete a University Support user."""
    university_id = get_university_id_from_token()
    if not validate_object_id(user_id):
        return jsonify({'error': 'Invalid user ID'}), 400

    admin = Admin.find_by_id(user_id)
    if not admin or admin.get('role') != 'local_support':
        return jsonify({'error': 'Support user not found'}), 404

    if str(admin.get('university_id')) != university_id:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        db = get_db()
        db.admins.delete_one({'_id': ObjectId(user_id)})
        ActivityLog.log(get_jwt_identity(), 'university_admin', 'delete_support_user', 'admin', {'user_id': user_id})
        return jsonify({'message': 'Support user deleted'}), 200
    except Exception as e:
        logger.error(f"Error deleting support user: {e}")
        return jsonify({'error': 'Failed to delete support user'}), 500

# ============================================================
# SUBSCRIPTION
# ============================================================

@university_admin_bp.route('/subscription', methods=['GET'])
@jwt_required()
@role_required('university_admin')
def get_subscription():
    """Get university subscription details."""
    university_id = get_university_id_from_token()
    if not university_id:
        return jsonify({'error': 'University ID not found'}), 400
    
    try:
        db = get_db()
        subscription = db.university_subscriptions.find_one({
            'university_id': ObjectId(university_id)
        })
        
        if not subscription:
            return jsonify({'subscription': None}), 200
        
        # Convert ObjectIds to strings
        subscription['_id'] = str(subscription['_id'])
        subscription['university_id'] = str(subscription['university_id'])
        subscription['plan_id'] = str(subscription['plan_id'])
        
        # Get plan details
        plan = db.college_plans.find_one({'_id': subscription['plan_id']})
        if plan:
            subscription['plan_name'] = plan.get('plan_name', 'Unknown Plan')
            subscription['plan_features'] = plan.get('features', {})
        
        return jsonify({'subscription': subscription}), 200
    except Exception as e:
        logger.error(f"Error fetching subscription: {e}")
        return jsonify({'error': 'Failed to fetch subscription'}), 500

from app.database import get_db
