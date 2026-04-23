# backend/app/routes/applications.py
"""
Student application routes.
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from app.models.application import Application
from app.models.course import Course
from app.models.student import Student
from app.models.activity_log import ActivityLog
from app.utils.validators import validate_object_id

applications_bp = Blueprint('applications', __name__)
logger = logging.getLogger(__name__)

@applications_bp.route('/apply', methods=['POST'])
@jwt_required()
def apply():
    """Student applies to a course."""
    student_id = get_jwt_identity()
    data = request.get_json()
    course_id = data.get('course_id')
    college_id = data.get('college_id')

    if not course_id:
        return jsonify({'error': 'course_id is required'}), 400

    # Validate course_id
    if not validate_object_id(course_id):
        return jsonify({'error': 'Invalid course ID format'}), 400

    # Check if course exists and has available seats
    course = Course.find_by_id(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Get college_id from course if not provided
    if not college_id:
        college_id = course.get('college_id')
    
    if not college_id:
        return jsonify({'error': 'College ID not found for this course'}), 400

    # Validate college_id
    if not validate_object_id(college_id):
        return jsonify({'error': 'Invalid college ID format'}), 400

    if course.get('available_seats', 0) <= 0:
        return jsonify({'error': 'No seats available'}), 400

    # Check if already applied
    existing = Application.find_by_student(student_id)
    for app in existing:
        if str(app['college_id']) == college_id and str(app['course_id']) == course_id:
            return jsonify({'error': 'Already applied to this course'}), 409

    # Create application
    application_data = {
        'student_id': ObjectId(student_id),
        'college_id': ObjectId(college_id),
        'course_id': ObjectId(course_id)
    }
    try:
        app_id = Application.create(application_data)
        # Log activity
        ActivityLog.log(student_id, 'student', 'apply', 'application', {'application_id': str(app_id)})
        return jsonify({'message': 'Application submitted', 'application_id': str(app_id)}), 201
    except Exception as e:
        logger.error(f"Application creation failed: {e}")
        return jsonify({'error': 'Failed to submit application'}), 500

@applications_bp.route('/<application_id>', methods=['GET'])
@jwt_required()
def get_application(application_id):
    """Get details of a specific application."""
    student_id = get_jwt_identity()
    if not validate_object_id(application_id):
        return jsonify({'error': 'Invalid application ID'}), 400

    app = Application.find_by_id(application_id)
    if not app:
        return jsonify({'error': 'Application not found'}), 404

    # Check ownership
    if str(app['student_id']) != student_id:
        return jsonify({'error': 'Access denied'}), 403

    app['_id'] = str(app['_id'])
    app['student_id'] = str(app['student_id'])
    app['college_id'] = str(app['college_id'])
    app['course_id'] = str(app['course_id'])

    # Populate names
    course = Course.find_by_id(app['course_id'])
    if course:
        app['course_name'] = course.get('course_name')
    from app.models.college import College
    college = College.find_by_id(app['college_id'])
    if college:
        app['college_name'] = college.get('name')

    return jsonify(app), 200

@applications_bp.route('/<application_id>', methods=['DELETE'])
@jwt_required()
def withdraw_application(application_id):
    """Student withdraws an application."""
    student_id = get_jwt_identity()
    if not validate_object_id(application_id):
        return jsonify({'error': 'Invalid application ID'}), 400

    app = Application.find_by_id(application_id)
    if not app:
        return jsonify({'error': 'Application not found'}), 404

    if str(app['student_id']) != student_id:
        return jsonify({'error': 'Access denied'}), 403

    # Only allow withdrawal if status is 'applied' or 'shortlisted'
    if app['status'] not in ['applied', 'shortlisted']:
        return jsonify({'error': 'Cannot withdraw application at this stage'}), 400

    deleted = Application.delete(application_id)
    if deleted:
        ActivityLog.log(student_id, 'student', 'withdraw', 'application', {'application_id': application_id})
        return jsonify({'message': 'Application withdrawn'}), 200
    else:
        return jsonify({'error': 'Withdrawal failed'}), 500