# backend/app/routes/students.py
"""
Student profile and application management.
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from app.models.student import Student
from app.models.application import Application
from app.models.activity_log import ActivityLog
from app.utils.validators import validate_email, validate_mobile

students_bp = Blueprint('students', __name__)
logger = logging.getLogger(__name__)

@students_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current student's profile."""
    student_id = get_jwt_identity()
    student = Student.find_by_id(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    # Remove sensitive fields
    student.pop('password_hash', None)
    student['_id'] = str(student['_id'])
    return jsonify(student), 200

@students_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update student profile."""
    student_id = get_jwt_identity()
    data = request.get_json()

    # Allowed updates
    allowed_fields = [
        'name', 'college_name', 'preferred_course', 'year', 'location',
        'dob', 'date_of_birth', 'gender', 'father_name', 'mother_name', 'address',
        'city', 'state', 'pincode', 'year_of_passing', 'qualification', 'mobile'
    ]
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400

    # If updating email or mobile, validate and check uniqueness
    if 'email' in updates:
        if not validate_email(updates['email']):
            return jsonify({'error': 'Invalid email'}), 400
        existing = Student.find_by_email(updates['email'])
        if existing and str(existing['_id']) != student_id:
            return jsonify({'error': 'Email already in use'}), 409
    if 'mobile' in updates:
        if not validate_mobile(updates['mobile']):
            return jsonify({'error': 'Invalid mobile'}), 400
        existing = Student.find_by_mobile(updates['mobile'])
        if existing and str(existing['_id']) != student_id:
            return jsonify({'error': 'Mobile already in use'}), 409

    updated = Student.update(student_id, updates)
    if not updated:
        return jsonify({'error': 'Update failed'}), 500

    # Log activity
    ActivityLog.log(student_id, 'student', 'profile_update', 'student', {'fields': list(updates.keys())})

    return jsonify({'message': 'Profile updated successfully'}), 200

@students_bp.route('/applications', methods=['GET'])
@jwt_required()
def get_applications():
    """Get all applications for the current student."""
    student_id = get_jwt_identity()
    applications = Application.find_by_student(student_id)
    # Convert ObjectIds to strings and populate course/college names
    from app.models.course import Course
    from app.models.college import College
    result = []
    for app in applications:
        app['_id'] = str(app['_id'])
        app['student_id'] = str(app['student_id'])
        app['college_id'] = str(app['college_id'])
        app['course_id'] = str(app['course_id'])
        # Add course name and college name
        course = Course.find_by_id(app['course_id'])
        if course:
            app['course_name'] = course.get('course_name')
        college = College.find_by_id(app['college_id'])
        if college:
            app['college_name'] = college.get('name')
        result.append(app)
    return jsonify(result), 200

@students_bp.route('/claim-account', methods=['POST'])
def claim_account():
    """Allow a student manually added by admin to claim account via OTP."""
    data = request.get_json()
    mobile = data.get('mobile')
    email = data.get('email')
    if not mobile and not email:
        return jsonify({'error': 'Mobile or email required'}), 400

    # Find student by mobile or email
    student = None
    if mobile:
        student = Student.find_by_mobile(mobile)
    if not student and email:
        student = Student.find_by_email(email)

    if not student:
        return jsonify({'error': 'Student not found'}), 404

    # Check if already claimed (has password or google_id)
    if student.get('password_hash') or student.get('google_id'):
        return jsonify({'error': 'Account already claimed'}), 400

    # Send OTP to mobile/email
    from app.services.otp_service import OTPService
    from app.services.email_service import send_email
    identifier = email or mobile
    otp = OTPService.generate_otp(identifier)
    if email:
        send_email(email, 'Claim Your Account', f'OTP to claim your account: {otp}')
    else:
        # For mobile, integrate SMS service (placeholder)
        logger.info(f"OTP for {mobile}: {otp}")
        # In production, use SMS gateway

    return jsonify({'message': 'OTP sent', 'identifier': identifier}), 200

@students_bp.route('/claim-account/verify', methods=['POST'])
def claim_account_verify():
    """Verify OTP and set password to claim account."""
    data = request.get_json()
    identifier = data.get('identifier')  # email or mobile
    otp = data.get('otp')
    password = data.get('password')
    if not all([identifier, otp, password]):
        return jsonify({'error': 'Identifier, OTP, and password required'}), 400

    from app.services.otp_service import OTPService
    if not OTPService.verify_otp(identifier, otp):
        return jsonify({'error': 'Invalid or expired OTP'}), 400

    # Find student
    student = None
    if '@' in identifier:
        student = Student.find_by_email(identifier)
    else:
        student = Student.find_by_mobile(identifier)

    if not student:
        return jsonify({'error': 'Student not found'}), 404

    if student.get('password_hash'):
        return jsonify({'error': 'Account already claimed'}), 400

    # Set password
    Student.update(student['_id'], {'password': password})

    # Log
    ActivityLog.log(student['_id'], 'student', 'claim_account', 'student', {})

    return jsonify({'message': 'Account claimed successfully'}), 200


@students_bp.route('/qualification', methods=['PUT'])
@jwt_required()
def update_qualification():
    """Update student's qualification and stream."""
    student_id = get_jwt_identity()
    data = request.get_json()
    
    qualification = data.get('qualification')
    stream = data.get('stream')
    
    if qualification and qualification not in Student.QUALIFICATIONS:
        return jsonify({'error': 'Invalid qualification'}), 400
    
    if stream and stream not in Student.STREAMS:
        return jsonify({'error': 'Invalid stream'}), 400
    
    updates = {}
    if qualification:
        updates['qualification'] = qualification
    if stream:
        updates['stream'] = stream
    
    if not updates:
        return jsonify({'error': 'No fields to update'}), 400
    
    Student.update(student_id, updates)
    
    return jsonify({'message': 'Qualification updated successfully'}), 200


@students_bp.route('/eligible-courses', methods=['GET'])
@jwt_required()
def get_eligible_courses():
    """Get courses eligible for the student's qualification."""
    student_id = get_jwt_identity()
    student = Student.find_by_id(student_id)
    
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    qualification = request.args.get('qualification', student.get('qualification', '12th'))
    stream = request.args.get('stream', student.get('stream', 'science'))
    
    from app.models.course import Course
    from app.models.college import College
    
    eligible_courses = Course.get_eligible_courses(qualification, stream)
    
    # Add college info
    result = []
    for course in eligible_courses:
        course['_id'] = str(course['_id'])
        course['college_id'] = str(course['college_id'])
        college = College.find_by_id(course['college_id'])
        if college:
            course['college_name'] = college.get('name')
            course['college_city'] = college.get('city')
        result.append(course)
    
    return jsonify({'courses': result}), 200