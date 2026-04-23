# backend/app/routes/course_admin.py
"""
Course/Department admin routes.
DepartmentAdmin (course_admin) manages their specific department's admission flow.

Hierarchy:
DepartmentAdmin → Manages their department's courses and applications
"""
from datetime import datetime
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson.objectid import ObjectId
from app.models.course import Course
from app.models.admin import Admin
from app.models.application import Application
from app.models.activity_log import ActivityLog
from app.utils.validators import validate_object_id, validate_email
from app.middlewares.auth_middleware import role_required


course_admin_bp = Blueprint('course_admin', __name__)
logger = logging.getLogger(__name__)

def get_admin_data_from_token():
    claims = get_jwt()
    return {
        'college_id': claims.get('college_id'),
        'department': None  # Will fetch from admin record
    }

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

def get_department(admin_id):
    """Get the department this admin manages."""
    admin = Admin.find_by_id(admin_id)
    return admin.get('department') if admin else None

# ============================================================
# MY DEPARTMENT INFO
# ============================================================

@course_admin_bp.route('/my-department', methods=['GET'])
@jwt_required()
@role_required('course_admin')
def get_my_department():
    """Get department info for this admin."""
    admin_id = get_jwt_identity()
    admin = Admin.find_by_id(admin_id)
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    return jsonify({
        'department': admin.get('department'),
        'college_id': str(admin['college_id']) if admin.get('college_id') else None,
        'name': admin.get('name')
    }), 200

# ============================================================
# MY COURSES (Department's courses only)
# ============================================================

@course_admin_bp.route('/courses', methods=['GET'])
@jwt_required()
@role_required('course_admin')
def get_my_courses():
    """Get all courses in this department."""
    admin_id = get_jwt_identity()
    department = get_department(admin_id)
    if not department:
        return jsonify({'error': 'Department not assigned'}), 400
    
    try:
        db = get_db()
        admin = Admin.find_by_id(admin_id)
        college_id = admin.get('college_id')
        
        courses = list(db.courses.find({
            'college_id': college_id,
            'department': department
        }))
        for course in courses:
            course['_id'] = str(course['_id'])
            if course.get('college_id'):
                course['college_id'] = str(course['college_id'])
        return jsonify({'courses': courses}), 200
    except Exception as e:
        logger.error(f"Error fetching courses: {e}")
        return jsonify({'error': 'Failed to fetch courses'}), 500

@course_admin_bp.route('/courses', methods=['POST'])
@jwt_required()
@role_required('course_admin')
def create_course():
    """Create a new course in this department."""
    admin_id = get_jwt_identity()
    department = get_department(admin_id)
    if not department:
        return jsonify({'error': 'Department not assigned'}), 400

    data = request.get_json()
    required = ['course_name', 'domain', 'duration', 'eligibility', 'seats', 'fees']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400

    try:
        admin = Admin.find_by_id(admin_id)
        course_data = {
            'college_id': admin['college_id'],
            'course_name': data['course_name'],
            'domain': data['domain'],
            'department': department,
            'description': data.get('description', ''),
            'duration': data['duration'],
            'eligibility': data['eligibility'],
            'seats': int(data['seats']),
            'available_seats': int(data['seats']),
            'fees': float(data['fees']),
            'required_documents': data.get('required_documents', [])
        }
        course_id = Course.create(course_data)
        ActivityLog.log(admin_id, 'course_admin', 'create_course', 'course', {
            'course_id': str(course_id),
            'department': department
        })
        return jsonify({'message': 'Course created', 'course_id': str(course_id)}), 201
    except Exception as e:
        logger.error(f"Course creation failed: {e}")
        return jsonify({'error': 'Failed to create course'}), 500

@course_admin_bp.route('/courses/<course_id>', methods=['PUT'])
@jwt_required()
@role_required('course_admin')
def update_course(course_id):
    """Update course details."""
    admin_id = get_jwt_identity()
    department = get_department(admin_id)
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID'}), 400

    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    if course.get('department') != department:
        return jsonify({'error': 'Unauthorized - course not in your department'}), 403

    data = request.get_json()
    allowed = ['course_name', 'domain', 'description', 'duration', 'eligibility', 'seats', 'fees', 'required_documents']
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
        ActivityLog.log(admin_id, 'course_admin', 'update_course', 'course', {'course_id': course_id})
        return jsonify({'message': 'Course updated'}), 200
    return jsonify({'error': 'Update failed'}), 500

@course_admin_bp.route('/courses/<course_id>', methods=['DELETE'])
@jwt_required()
@role_required('course_admin')
def delete_course(course_id):
    """Delete a course."""
    admin_id = get_jwt_identity()
    department = get_department(admin_id)
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID'}), 400

    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    if course.get('department') != department:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        db = get_db()
        db.courses.delete_one({'_id': ObjectId(course_id)})
        ActivityLog.log(admin_id, 'course_admin', 'delete_course', 'course', {'course_id': course_id})
        return jsonify({'message': 'Course deleted'}), 200
    except Exception as e:
        logger.error(f"Error deleting course: {e}")
        return jsonify({'error': 'Failed to delete course'}), 500

# ============================================================
# APPLICATION MANAGEMENT (Department's applications)
# ============================================================

@course_admin_bp.route('/applications', methods=['GET'])
@jwt_required()
@role_required('course_admin')
def get_applications():
    """Get all applications for this department."""
    admin_id = get_jwt_identity()
    department = get_department(admin_id)
    if not department:
        return jsonify({'error': 'Department not assigned'}), 400
    
    try:
        db = get_db()
        applications = list(db.applications.find({'department': department}))
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

@course_admin_bp.route('/applications/<app_id>', methods=['GET'])
@jwt_required()
@role_required('course_admin')
def get_application(app_id):
    """Get single application details."""
    from bson.objectid import ObjectId
    admin_id = get_jwt_identity()
    department = get_department(admin_id)
    if not validate_object_id(app_id):
        return jsonify({'error': 'Invalid application ID'}), 400

    app = Application.find_by_id(app_id)
    if not app:
        return jsonify({'error': 'Application not found'}), 404

    if app.get('department') != department:
        return jsonify({'error': 'Unauthorized'}), 403

    app['_id'] = str(app['_id'])
    if app.get('student_id'):
        app['student_id'] = str(app['student_id'])
        db = get_db()
        student = db.students.find_one({'_id': ObjectId(app['student_id'])})
        if student:
            app['student_name'] = student.get('name', '')
            app['student_email'] = student.get('email', '')
            app['student_mobile'] = student.get('mobile', '')
    
    if app.get('college_id'):
        app['college_id'] = str(app['college_id'])
        db = get_db()
        college = db.colleges.find_one({'_id': ObjectId(app['college_id'])})
        if college:
            app['college_name'] = college.get('name', '')
    
    if app.get('course_id'):
        app['course_id'] = str(app['course_id'])
        db = get_db()
        course = db.courses.find_one({'_id': ObjectId(app['course_id'])})
        if course:
            app['course_name'] = course.get('course_name', '')
    
    if app.get('documents'):
        documents = list(db.documents.find({'application_id': ObjectId(app_id)}))
        app['documents'] = []
        for doc in documents:
            app['documents'].append({
                '_id': str(doc['_id']),
                'document_type': doc.get('document_type', ''),
                'file_url': doc.get('file_url', ''),
                'uploaded_at': doc.get('uploaded_at', '').isoformat() if doc.get('uploaded_at') else '',
                'verification_status': doc.get('verification_status', 'pending')
            })
    
    return jsonify({'application': app}), 200

@course_admin_bp.route('/applications/<app_id>/status', methods=['PUT'])
@jwt_required()
@role_required('course_admin')
def update_application_status(app_id):
    """Update application status."""
    admin_id = get_jwt_identity()
    department = get_department(admin_id)
    if not validate_object_id(app_id):
        return jsonify({'error': 'Invalid application ID'}), 400

    app = Application.find_by_id(app_id)
    if not app:
        return jsonify({'error': 'Application not found'}), 404

    if app.get('department') != department:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    status = data.get('status')
    remarks = data.get('remarks', '')
    valid_statuses = ['applied', 'under_review', 'shortlisted', 'rejected', 'offered', 'confirmed']
    if status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400

    updates = {
        'status': status,
        'updated_at': datetime.utcnow()
    }
    if remarks:
        updates['remarks'] = remarks

    updated = Application.update(app_id, updates)
    if updated:
        ActivityLog.log(admin_id, 'course_admin', 'update_application_status', 'application', {
            'application_id': app_id,
            'status': status
        })
        return jsonify({'message': 'Status updated'}), 200
    return jsonify({'error': 'Update failed'}), 500

# ============================================================
# STATISTICS (Department level)
# ============================================================

@course_admin_bp.route('/stats', methods=['GET'])
@jwt_required()
@role_required('course_admin')
def get_stats():
    """Get statistics for this department."""
    admin_id = get_jwt_identity()
    department = get_department(admin_id)
    if not department:
        return jsonify({'error': 'Department not assigned'}), 400
    
    try:
        db = get_db()
        
        # Count courses
        course_count = db.courses.count_documents({'department': department})
        
        # Count applications
        app_count = db.applications.count_documents({'department': department})
        
        # Count by status
        status_counts = {}
        for status in ['applied', 'under_review', 'shortlisted', 'rejected', 'offered', 'confirmed']:
            status_counts[status] = db.applications.count_documents({
                'department': department,
                'status': status
            })
        
        # Get course details
        courses = list(db.courses.find({'department': department}, {
            'course_name': 1,
            'seats': 1,
            'available_seats': 1
        }))
        
        total_seats = sum(c.get('seats', 0) for c in courses)
        filled_seats = sum(c.get('seats', 0) - c.get('available_seats', 0) for c in courses)
        
        return jsonify({
            'department': department,
            'course_count': course_count,
            'application_count': app_count,
            'total_seats': total_seats,
            'filled_seats': filled_seats,
            'available_seats': total_seats - filled_seats,
            'status_counts': status_counts
        }), 200
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

from app.database import get_db
