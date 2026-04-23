# backend/app/routes/superadmin.py
"""
Super admin routes for platform management.
Only SuperAdmin can access these routes.

Responsibilities:
- Create/Manage Universities
- Create University Admins
- View all universities, colleges, and students
- Platform-wide analytics
"""
from datetime import datetime
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from app.models.university import University
from app.models.college import College
from app.models.admin import Admin
from app.models.activity_log import ActivityLog
from app.utils.validators import validate_object_id, validate_email
from app.middlewares.auth_middleware import role_required
from app.services.analytics_service import get_platform_analytics


superadmin_bp = Blueprint('superadmin', __name__)
logger = logging.getLogger(__name__)

def convert_objectid(obj):
    """Recursively convert ObjectId and datetime to JSON serializable types."""
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
# UNIVERSITY MANAGEMENT (SuperAdmin creates Universities)
# ============================================================

@superadmin_bp.route('/universities', methods=['POST'])
@jwt_required()
@role_required('super_admin')
def create_university():
    """Create a new university."""
    data = request.get_json()
    required = ['name', 'code', 'address', 'city', 'state', 'contact_email', 'contact_phone']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400

    existing = University.find_by_code(data['code'])
    if existing:
        return jsonify({'error': 'University code already exists'}), 409

    university_data = {
        'name': data['name'],
        'code': data['code'],
        'address': data['address'],
        'city': data['city'],
        'state': data['state'],
        'contact_email': data['contact_email'],
        'contact_phone': data['contact_phone'],
        'website': data.get('website', ''),
        'description': data.get('description', '')
    }
    try:
        university_id = University.create(university_data)
        admin_id = get_jwt_identity()
        ActivityLog.log(admin_id, 'super_admin', 'create_university', 'university', {'university_id': str(university_id)})
        return jsonify({'message': 'University created', 'university_id': str(university_id)}), 201
    except Exception as e:
        logger.error(f"University creation failed: {e}")
        return jsonify({'error': 'Failed to create university'}), 500

@superadmin_bp.route('/universities', methods=['GET'])
@jwt_required()
@role_required('super_admin')
def get_all_universities():
    """Get all universities."""
    try:
        universities = University.get_all_as_dict()
        for u in universities:
            u['_id'] = str(u['_id'])
        return jsonify({'universities': universities}), 200
    except Exception as e:
        logger.error(f"Error fetching universities: {e}")
        return jsonify({'error': 'Failed to fetch universities'}), 500

@superadmin_bp.route('/universities/<university_id>', methods=['GET'])
@jwt_required()
@role_required('super_admin')
def get_university(university_id):
    """Get single university details."""
    if not validate_object_id(university_id):
        return jsonify({'error': 'Invalid university ID'}), 400
    
    university = University.find_by_id(university_id)
    if not university:
        return jsonify({'error': 'University not found'}), 404
    
    university['_id'] = str(university['_id'])
    return jsonify({'university': university}), 200

@superadmin_bp.route('/universities/<university_id>', methods=['PUT'])
@jwt_required()
@role_required('super_admin')
def update_university(university_id):
    """Update university details."""
    if not validate_object_id(university_id):
        return jsonify({'error': 'Invalid university ID'}), 400

    university = University.find_by_id(university_id)
    if not university:
        return jsonify({'error': 'University not found'}), 404

    data = request.get_json()
    allowed = ['name', 'code', 'address', 'city', 'state', 'contact_email', 'contact_phone', 'website', 'description']
    updates = {k: v for k, v in data.items() if k in allowed}

    if 'code' in updates and updates['code'] != university.get('code'):
        existing = University.find_by_code(updates['code'])
        if existing and str(existing['_id']) != university_id:
            return jsonify({'error': 'University code already in use'}), 409

    updated = University.update(university_id, updates)
    if updated:
        admin_id = get_jwt_identity()
        ActivityLog.log(admin_id, 'super_admin', 'update_university', 'university', {'university_id': university_id})
        return jsonify({'message': 'University updated'}), 200
    return jsonify({'error': 'Update failed'}), 500

@superadmin_bp.route('/universities/<university_id>', methods=['DELETE'])
@jwt_required()
@role_required('super_admin')
def delete_university(university_id):
    """Delete (deactivate) university."""
    if not validate_object_id(university_id):
        return jsonify({'error': 'Invalid university ID'}), 400
    
    deleted = University.delete(university_id)
    if deleted:
        admin_id = get_jwt_identity()
        ActivityLog.log(admin_id, 'super_admin', 'delete_university', 'university', {'university_id': university_id})
        return jsonify({'message': 'University deleted'}), 200
    return jsonify({'error': 'Failed to delete university'}), 500

# ============================================================
# UNIVERSITY ADMIN MANAGEMENT
# ============================================================

@superadmin_bp.route('/university-admins', methods=['POST'])
@jwt_required()
@role_required('super_admin')
def create_university_admin():
    """Create a new university admin."""
    data = request.get_json()
    required = ['name', 'email', 'password', 'university_id']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400

    if not validate_email(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400

    existing = Admin.find_by_email(data['email'])
    if existing:
        return jsonify({'error': 'Email already in use'}), 409

    university = University.find_by_id(data['university_id'])
    if not university:
        return jsonify({'error': 'University not found'}), 404

    admin_data = {
        'name': data['name'],
        'email': data['email'],
        'password': data['password'],
        'role': 'university_admin',
        'university_id': ObjectId(data['university_id']),
        'mobile': data.get('mobile', '')
    }
    try:
        admin_id = Admin.create(admin_data)
        super_admin_id = get_jwt_identity()
        ActivityLog.log(super_admin_id, 'super_admin', 'create_university_admin', 'admin', {
            'admin_id': str(admin_id),
            'university_id': data['university_id']
        })
        return jsonify({'message': 'University admin created', 'admin_id': str(admin_id)}), 201
    except Exception as e:
        logger.error(f"University admin creation failed: {e}")
        return jsonify({'error': 'Failed to create university admin'}), 500

@superadmin_bp.route('/university-admins', methods=['GET'])
@jwt_required()
@role_required('super_admin')
def get_all_university_admins():
    """Get all university admins."""
    try:
        db = get_db()
        admins = list(db.admins.find({'role': 'university_admin'}))
        for admin in admins:
            admin['_id'] = str(admin['_id'])
            if admin.get('university_id'):
                admin['university_id'] = str(admin['university_id'])
            admin.pop('password_hash', None)
        return jsonify(admins), 200
    except Exception as e:
        logger.error(f"Error fetching university admins: {e}")
        return jsonify({'error': 'Failed to fetch university admins'}), 500

# ============================================================
# VIEW ALL DATA (Universities → Colleges → Students)
# ============================================================

@superadmin_bp.route('/colleges', methods=['GET'])
@jwt_required()
@role_required('super_admin')
def get_all_colleges():
    """Get all colleges across all universities."""
    try:
        db = get_db()
        colleges = list(db.colleges.find())
        for college in colleges:
            college['_id'] = str(college['_id'])
            if college.get('university_id'):
                college['university_id'] = str(college['university_id'])
        return jsonify({'colleges': colleges}), 200
    except Exception as e:
        logger.error(f"Error fetching colleges: {e}")
        return jsonify({'error': 'Failed to fetch colleges'}), 500

@superadmin_bp.route('/students', methods=['GET'])
@jwt_required()
@role_required('super_admin')
def get_all_students():
    """Get all students."""
    try:
        from app.models.student import Student
        db = get_db()
        students = list(db.students.find({}, {'password_hash': 0}))
        for student in students:
            student['_id'] = str(student['_id'])
        return jsonify({'students': students}), 200
    except Exception as e:
        logger.error(f"Error fetching students: {e}")
        return jsonify({'error': 'Failed to fetch students'}), 500

@superadmin_bp.route('/all-admins', methods=['GET'])
@jwt_required()
@role_required('super_admin')
def get_all_admins():
    """Get all admins (all roles)."""
    try:
        db = get_db()
        admins = list(db.admins.find({}, {'password_hash': 0}))
        for admin in admins:
            admin['_id'] = str(admin['_id'])
            if admin.get('college_id'):
                admin['college_id'] = str(admin['college_id'])
            if admin.get('university_id'):
                admin['university_id'] = str(admin['university_id'])
        return jsonify(admins), 200
    except Exception as e:
        logger.error(f"Error fetching admins: {e}")
        return jsonify({'error': 'Failed to fetch admins'}), 500

# ============================================================
# ANALYTICS
# ============================================================

@superadmin_bp.route('/analytics', methods=['GET'])
@jwt_required()
@role_required('super_admin')
def get_analytics():
    """Get platform-wide analytics."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    try:
        if start_date:
            start_date = datetime.fromisoformat(start_date)
        if end_date:
            end_date = datetime.fromisoformat(end_date)
        analytics = get_platform_analytics(start_date, end_date)
        analytics = convert_objectid(analytics)
        return jsonify(analytics), 200
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return jsonify({'error': 'Failed to fetch analytics'}), 500

from app.database import get_db
