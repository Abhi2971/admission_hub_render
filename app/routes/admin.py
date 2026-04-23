# backend/app/routes/admin.py
"""
College admin routes.
CollegeAdmin can create Department Admins and view all department data.

Hierarchy:
CollegeAdmin → Creates Department Admins → Manages Admission Flow
"""
from datetime import datetime
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson.objectid import ObjectId
from app.models.college import College
from app.models.course import Course
from app.models.admin import Admin
from app.models.application import Application
from app.models.activity_log import ActivityLog
from app.utils.validators import validate_object_id, validate_email
from app.middlewares.auth_middleware import role_required


admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

def get_college_id_from_token():
    claims = get_jwt()
    return claims.get('college_id')

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
# MY COLLEGE INFO
# ============================================================

@admin_bp.route('/my-college', methods=['GET'])
@jwt_required()
def get_my_college():
    """Get the college this admin belongs to."""
    from bson.objectid import ObjectId
    claims = get_jwt()
    role = claims.get('role')
    
    if role != 'college_admin':
        return jsonify({'error': 'Only college admins can access this'}), 403
    
    college_id = get_college_id_from_token()
    if not college_id:
        return jsonify({'error': 'College ID not found in token', 'claims': claims}), 400
    
    try:
        college = College.find_by_id(ObjectId(college_id))
    except Exception as e:
        return jsonify({'error': 'Invalid college ID', 'details': str(e)}), 400
    
    if not college:
        return jsonify({'error': 'College not found', 'college_id': college_id}), 404
    
    college['_id'] = str(college['_id'])
    if college.get('university_id'):
        college['university_id'] = str(college['university_id'])
    return jsonify({'college': college}), 200

# ============================================================
# DEPARTMENT ADMIN MANAGEMENT (CollegeAdmin creates them)
# ============================================================

@admin_bp.route('/department-admins', methods=['POST'])
@jwt_required()
@role_required('college_admin')
def create_department_admin():
    """Create a new department admin (course_admin)."""
    college_id = get_college_id_from_token()
    if not college_id:
        return jsonify({'error': 'College ID not found'}), 400

    data = request.get_json()
    required = ['name', 'email', 'password', 'department']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400

    if not validate_email(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400

    existing = Admin.find_by_email(data['email'])
    if existing:
        return jsonify({'error': 'Email already in use'}), 409

    claims = get_jwt()
    university_id = claims.get('university_id')

    admin_data = {
        'name': data['name'],
        'email': data['email'],
        'password': data['password'],
        'role': 'course_admin',
        'college_id': ObjectId(college_id),
        'university_id': ObjectId(university_id) if university_id else None,
        'department': data['department'],
        'mobile': data.get('mobile', '')
    }
    try:
        admin_id = Admin.create(admin_data)
        ActivityLog.log(get_jwt_identity(), 'college_admin', 'create_department_admin', 'admin', {
            'admin_id': str(admin_id),
            'department': data['department']
        })
        return jsonify({'message': 'Department admin created', 'admin_id': str(admin_id)}), 201
    except Exception as e:
        logger.error(f"Department admin creation failed: {e}")
        return jsonify({'error': 'Failed to create department admin'}), 500

@admin_bp.route('/department-admins', methods=['GET'])
@jwt_required()
@role_required('college_admin')
def get_department_admins():
    """Get all department admins for this college."""
    college_id = get_college_id_from_token()
    if not college_id:
        return jsonify({'error': 'College ID not found'}), 400
    
    try:
        db = get_db()
        admins = list(db.admins.find({
            'role': 'course_admin',
            'college_id': ObjectId(college_id)
        }))
        for admin in admins:
            admin['_id'] = str(admin['_id'])
            if admin.get('college_id'):
                admin['college_id'] = str(admin['college_id'])
            admin.pop('password_hash', None)
        return jsonify(admins), 200
    except Exception as e:
        logger.error(f"Error fetching department admins: {e}")
        return jsonify({'error': 'Failed to fetch department admins'}), 500

@admin_bp.route('/department-admins/<admin_id>', methods=['PUT'])
@jwt_required()
@role_required('college_admin')
def update_department_admin(admin_id):
    """Update department admin details."""
    college_id = get_college_id_from_token()
    if not validate_object_id(admin_id):
        return jsonify({'error': 'Invalid admin ID'}), 400

    admin = Admin.find_by_id(admin_id)
    if not admin or admin.get('role') != 'course_admin':
        return jsonify({'error': 'Department admin not found'}), 404

    if str(admin.get('college_id')) != college_id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    allowed = ['name', 'mobile', 'department']
    updates = {k: v for k, v in data.items() if k in allowed}

    if 'password' in data:
        updates['password'] = data['password']

    updated = Admin.update(admin_id, updates)
    if updated:
        ActivityLog.log(get_jwt_identity(), 'college_admin', 'update_department_admin', 'admin', {'admin_id': admin_id})
        return jsonify({'message': 'Department admin updated'}), 200
    return jsonify({'error': 'Update failed'}), 500

@admin_bp.route('/department-admins/<admin_id>', methods=['DELETE'])
@jwt_required()
@role_required('college_admin')
def delete_department_admin(admin_id):
    """Delete department admin."""
    college_id = get_college_id_from_token()
    if not validate_object_id(admin_id):
        return jsonify({'error': 'Invalid admin ID'}), 400

    admin = Admin.find_by_id(admin_id)
    if not admin or admin.get('role') != 'course_admin':
        return jsonify({'error': 'Department admin not found'}), 404

    if str(admin.get('college_id')) != college_id:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        db = get_db()
        db.admins.delete_one({'_id': ObjectId(admin_id)})
        ActivityLog.log(get_jwt_identity(), 'college_admin', 'delete_department_admin', 'admin', {'admin_id': admin_id})
        return jsonify({'message': 'Department admin deleted'}), 200
    except Exception as e:
        logger.error(f"Error deleting department admin: {e}")
        return jsonify({'error': 'Failed to delete department admin'}), 500

# ============================================================
# COURSE MANAGEMENT (Courses belong to Departments)
# ============================================================

@admin_bp.route('/courses', methods=['GET'])
@jwt_required()
@role_required('college_admin')
def get_courses():
    """Get all courses in this college."""
    college_id = get_college_id_from_token()
    if not college_id:
        return jsonify({'error': 'College ID not found'}), 400
    
    try:
        db = get_db()
        courses = list(db.courses.find({'college_id': ObjectId(college_id)}))
        for course in courses:
            course['_id'] = str(course['_id'])
            if course.get('college_id'):
                course['college_id'] = str(course['college_id'])
        return jsonify({'courses': courses}), 200
    except Exception as e:
        logger.error(f"Error fetching courses: {e}")
        return jsonify({'error': 'Failed to fetch courses'}), 500

@admin_bp.route('/courses', methods=['POST'])
@jwt_required()
@role_required('college_admin')
def create_course():
    """Create a new course (department course)."""
    college_id = get_college_id_from_token()
    if not college_id:
        return jsonify({'error': 'College ID not found'}), 400

    data = request.get_json()
    required = ['course_name', 'domain', 'department', 'duration', 'eligibility', 'seats', 'fees']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400

    course_data = {
        'college_id': ObjectId(college_id),
        'course_name': data['course_name'],
        'domain': data['domain'],
        'department': data['department'],
        'description': data.get('description', ''),
        'duration': data['duration'],
        'eligibility': data['eligibility'],
        'seats': int(data['seats']),
        'available_seats': int(data['seats']),
        'fees': float(data['fees']),
        'required_documents': data.get('required_documents', [])
    }
    try:
        course_id = Course.create(course_data)
        ActivityLog.log(get_jwt_identity(), 'college_admin', 'create_course', 'course', {
            'course_id': str(course_id),
            'course_name': data['course_name']
        })
        return jsonify({'message': 'Course created', 'course_id': str(course_id)}), 201
    except Exception as e:
        logger.error(f"Course creation failed: {e}")
        return jsonify({'error': 'Failed to create course'}), 500

@admin_bp.route('/courses/<course_id>', methods=['PUT'])
@jwt_required()
@role_required('college_admin')
def update_course(course_id):
    """Update course details."""
    college_id = get_college_id_from_token()
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID'}), 400

    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    if str(course.get('college_id')) != college_id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    allowed = ['course_name', 'domain', 'department', 'description', 'duration', 'eligibility', 'seats', 'fees', 'required_documents']
    updates = {k: v for k, v in data.items() if k in allowed}
    
    if 'seats' in updates:
        old_seats = course.get('seats', 0)
        new_seats = int(updates['seats'])
        current_filled = old_seats - course.get('available_seats', 0)
        if new_seats < current_filled:
            return jsonify({'error': 'Cannot reduce seats below filled count'}), 400
        updates['available_seats'] = new_seats - current_filled

    updated = Course.update(course_id, updates)
    if updated:
        ActivityLog.log(get_jwt_identity(), 'college_admin', 'update_course', 'course', {'course_id': course_id})
        return jsonify({'message': 'Course updated'}), 200
    return jsonify({'error': 'Update failed'}), 500

@admin_bp.route('/courses/<course_id>', methods=['DELETE'])
@jwt_required()
@role_required('college_admin')
def delete_course(course_id):
    """Delete a course."""
    college_id = get_college_id_from_token()
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID'}), 400

    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    if str(course.get('college_id')) != college_id:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        db = get_db()
        db.courses.delete_one({'_id': ObjectId(course_id)})
        ActivityLog.log(get_jwt_identity(), 'college_admin', 'delete_course', 'course', {'course_id': course_id})
        return jsonify({'message': 'Course deleted'}), 200
    except Exception as e:
        logger.error(f"Error deleting course: {e}")
        return jsonify({'error': 'Failed to delete course'}), 500

# ============================================================
# APPLICATION MANAGEMENT (View all across departments)
# ============================================================

@admin_bp.route('/applications', methods=['GET'])
@jwt_required()
@role_required('college_admin')
def get_applications():
    """Get all applications for this college (all departments)."""
    college_id = get_college_id_from_token()
    if not college_id:
        return jsonify({'error': 'College ID not found'}), 400
    
    try:
        db = get_db()
        applications = list(db.applications.find({'college_id': ObjectId(college_id)}))
        for app in applications:
            app['_id'] = str(app['_id'])
            if app.get('student_id'):
                app['student_id'] = str(app['student_id'])
            if app.get('college_id'):
                app['college_id'] = str(app['college_id'])
            if app.get('course_id'):
                app['course_id'] = str(app['course_id'])
        return jsonify({'applications': applications}), 200
    except Exception as e:
        logger.error(f"Error fetching applications: {e}")
        return jsonify({'error': 'Failed to fetch applications'}), 500

@admin_bp.route('/applications/<app_id>/status', methods=['PUT'])
@jwt_required()
@role_required('college_admin')
def update_application_status(app_id):
    """Update application status."""
    college_id = get_college_id_from_token()
    if not validate_object_id(app_id):
        return jsonify({'error': 'Invalid application ID'}), 400

    app = Application.find_by_id(app_id)
    if not app:
        return jsonify({'error': 'Application not found'}), 404

    if str(app.get('college_id')) != college_id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    status = data.get('status')
    valid_statuses = ['applied', 'under_review', 'shortlisted', 'rejected', 'offered', 'confirmed']
    if status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400

    updated = Application.update(app_id, {
        'status': status,
        'updated_at': datetime.utcnow()
    })
    if updated:
        ActivityLog.log(get_jwt_identity(), 'college_admin', 'update_application_status', 'application', {
            'application_id': app_id,
            'status': status
        })
        return jsonify({'message': 'Status updated'}), 200
    return jsonify({'error': 'Update failed'}), 500

# ============================================================
# STATISTICS
# ============================================================

@admin_bp.route('/analytics', methods=['GET'])
@jwt_required()
@role_required('college_admin')
def get_analytics():
    """Get analytics for this college (for charts)."""
    college_id = get_college_id_from_token()
    if not college_id:
        return jsonify({'error': 'College ID not found'}), 400
    
    try:
        db = get_db()
        
        # Applications by status
        status_data = {}
        for status in ['applied', 'under_review', 'shortlisted', 'rejected', 'offered', 'confirmed']:
            status_data[status] = db.applications.count_documents({
                'college_id': ObjectId(college_id),
                'status': status
            })
        
        # Applications by department
        dept_apps = db.applications.aggregate([
            {'$match': {'college_id': ObjectId(college_id)}},
            {'$group': {'_id': '$department', 'count': {'$sum': 1}}}
        ])
        dept_data = {d['_id']: d['count'] for d in dept_apps}
        
        # Applications over time (last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        daily_apps = db.applications.aggregate([
            {'$match': {
                'college_id': ObjectId(college_id),
                'applied_at': {'$gte': thirty_days_ago}
            }},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$applied_at'}},
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}}
        ])
        timeline_data = [{'date': d['_id'], 'count': d['count']} for d in daily_apps]
        
        # Top courses by applications
        top_courses = db.applications.aggregate([
            {'$match': {'college_id': ObjectId(college_id)}},
            {'$group': {'_id': '$course_id', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 5}
        ])
        course_ids = [d['_id'] for d in top_courses]
        courses = {str(c['_id']): c['course_name'] for c in db.courses.find({'_id': {'$in': course_ids}})} if course_ids else {}
        top_course_data = []
        for d in top_courses:
            top_course_data.append({
                'course_id': str(d['_id']),
                'course_name': courses.get(str(d['_id']), 'Unknown'),
                'count': d['count']
            })
        
        return jsonify({
            'status_distribution': status_data,
            'department_distribution': dept_data,
            'timeline': timeline_data,
            'top_courses': top_course_data
        }), 200
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        return jsonify({'error': 'Failed to fetch analytics'}), 500

@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
@role_required('college_admin')
def get_stats():
    """Get statistics for this college."""
    college_id = get_college_id_from_token()
    if not college_id:
        return jsonify({'error': 'College ID not found'}), 400
    
    try:
        db = get_db()
        
        # Count courses
        course_count = db.courses.count_documents({'college_id': ObjectId(college_id)})
        
        # Count department admins
        dept_admin_count = db.admins.count_documents({
            'role': 'course_admin',
            'college_id': ObjectId(college_id)
        })
        
        # Count applications
        app_count = db.applications.count_documents({'college_id': ObjectId(college_id)})
        
        # Count by status
        status_counts = {}
        for status in ['applied', 'under_review', 'shortlisted', 'rejected', 'offered', 'confirmed']:
            status_counts[status] = db.applications.count_documents({
                'college_id': ObjectId(college_id),
                'status': status
            })
        
        return jsonify({
            'course_count': course_count,
            'department_admin_count': dept_admin_count,
            'application_count': app_count,
            'status_counts': status_counts
        }), 200
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

# ============================================================
# SEAT ALLOCATION RULES
# ============================================================

@admin_bp.route('/seat-allocations', methods=['GET'])
@jwt_required()
@role_required('college_admin')
def get_seat_allocations():
    """Get all seat allocation rules for the college."""
    college_id = get_college_id_from_token()
    if not college_id:
        return jsonify({'error': 'College ID not found'}), 400
    
    try:
        db = get_db()
        courses = list(db.courses.find({'college_id': ObjectId(college_id)}))
        course_ids = [c['_id'] for c in courses]
        
        allocations = list(db.seat_allocations.find({'course_id': {'$in': course_ids}}))
        
        result = []
        for alloc in allocations:
            course = next((c for c in courses if c['_id'] == alloc['course_id']), None)
            result.append({
                '_id': str(alloc['_id']),
                'course_id': str(alloc['course_id']),
                'course_name': course['course_name'] if course else 'Unknown',
                'allocations': alloc.get('allocations', {}),
                'created_at': alloc.get('created_at'),
                'updated_at': alloc.get('updated_at')
            })
        
        return jsonify({'seat_allocations': result}), 200
    except Exception as e:
        logger.error(f"Error fetching seat allocations: {e}")
        return jsonify({'error': 'Failed to fetch seat allocations'}), 500

@admin_bp.route('/seat-allocations/<course_id>', methods=['POST'])
@jwt_required()
@role_required('college_admin')
def create_seat_allocation(course_id):
    """Create or update seat allocation for a course."""
    college_id = get_college_id_from_token()
    if not college_id:
        return jsonify({'error': 'College ID not found'}), 400
    
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID'}), 400
    
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if str(course.get('college_id')) != college_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    allocations = data.get('allocations', {})
    
    for category in allocations:
        if category not in ['general', 'obc', 'sc', 'st', 'ews', 'pwd', 'nri', 'management']:
            return jsonify({'error': f'Invalid category: {category}'}), 400
    
    try:
        db = get_db()
        db.seat_allocations.update_one(
            {'course_id': ObjectId(course_id)},
            {
                '$set': {
                    'college_id': ObjectId(college_id),
                    'course_id': ObjectId(course_id),
                    'allocations': allocations,
                    'updated_at': datetime.utcnow()
                }
            },
            upsert=True
        )
        
        ActivityLog.log(get_jwt_identity(), 'college_admin', 'create_seat_allocation', 'course', {
            'course_id': course_id,
            'allocations': allocations
        })
        
        return jsonify({'message': 'Seat allocation updated'}), 200
    except Exception as e:
        logger.error(f"Error creating seat allocation: {e}")
        return jsonify({'error': 'Failed to create seat allocation'}), 500

@admin_bp.route('/seat-allocations/<course_id>', methods=['GET'])
@jwt_required()
@role_required('college_admin')
def get_course_seat_allocation(course_id):
    """Get seat allocation for a specific course."""
    college_id = get_college_id_from_token()
    if not college_id:
        return jsonify({'error': 'College ID not found'}), 400
    
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID'}), 400
    
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if str(course.get('college_id')) != college_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        db = get_db()
        allocation = db.seat_allocations.find_one({'course_id': ObjectId(course_id)})
        
        if not allocation:
            return jsonify({
                'course_id': course_id,
                'course_name': course.get('course_name'),
                'total_seats': course.get('seats', 0),
                'allocations': {}
            }), 200
        
        allocation['_id'] = str(allocation['_id'])
        allocation['course_id'] = str(allocation['course_id'])
        allocation['course_name'] = course.get('course_name')
        allocation['total_seats'] = course.get('seats', 0)
        
        return jsonify(allocation), 200
    except Exception as e:
        logger.error(f"Error fetching seat allocation: {e}")
        return jsonify({'error': 'Failed to fetch seat allocation'}), 500

from app.database import get_db
