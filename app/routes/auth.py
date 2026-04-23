"""
Authentication routes: signup, login, OTP, Google OAuth, password reset.
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from app.models.student import Student
from app.models.admin import Admin
from app.services.auth_service import AuthService
from app.services.otp_service import OTPService
from app.services.email_service import send_email
from app.utils.validators import validate_email, validate_mobile, validate_password
from app.utils.decorators import rate_limit
from app.middlewares.auth_middleware import role_required

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth_bp.route('/student/signup', methods=['POST'])
@rate_limit(limit=5, per=60)
def student_signup():
    """Student registration with email/mobile and OTP."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    name = data.get('name')
    email = data.get('email')
    mobile = data.get('mobile')
    password = data.get('password')
    if not all([name, email, mobile, password]):
        return jsonify({'error': 'Missing required fields'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    if not validate_mobile(mobile):
        return jsonify({'error': 'Invalid mobile number'}), 400
    if not validate_password(password):
        return jsonify({'error': 'Password must be at least 8 characters, include uppercase, lowercase, number'}), 400

    existing = Student.find_by_email(email) or Student.find_by_mobile(mobile)
    if existing:
        return jsonify({'error': 'User already exists with this email or mobile'}), 409

    otp = OTPService.generate_otp(email)
    try:
        send_email(
            to=email,
            subject='Your Admission Platform OTP',
            body=f'Your OTP for registration is: {otp}. It expires in 10 minutes.'
        )
    except Exception as e:
        logger.error(f"Failed to send OTP email: {e}")
        return jsonify({'error': 'Failed to send OTP. Please try again.'}), 500

    from app.services.otp_service import temp_store
    temp_store[email] = {
        'name': name,
        'email': email,
        'mobile': mobile,
        'password': password
    }

    return jsonify({'message': 'OTP sent to email', 'email': email}), 200

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP and complete student registration."""
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    if not email or not otp:
        return jsonify({'error': 'Email and OTP required'}), 400

    if not OTPService.verify_otp(email, otp):
        return jsonify({'error': 'Invalid or expired OTP'}), 400

    from app.services.otp_service import temp_store
    user_data = temp_store.pop(email, None)
    if not user_data:
        return jsonify({'error': 'Signup data expired. Please restart signup.'}), 400

    try:
        student_id = Student.create(user_data)
        from app.models.activity_log import ActivityLog
        ActivityLog.log(student_id, 'student', 'signup', 'student', {'email': email})
        access_token = create_access_token(identity=str(student_id), additional_claims={'role': 'student'})
        refresh_token = create_refresh_token(identity=str(student_id))
        return jsonify({
            'message': 'Registration successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {'id': str(student_id), 'name': user_data['name'], 'email': email, 'role': 'student'}
        }), 201
    except Exception as e:
        logger.error(f"Error creating student: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/student/login', methods=['POST'])
def student_login():
    """Student login with email/mobile and password (legacy)."""
    data = request.get_json()
    print(f"Student login data received: {data}")
    email_or_mobile = data.get('email') or data.get('mobile')
    password = data.get('password')
    if not email_or_mobile or not password:
        return jsonify({'error': 'Email/mobile and password required'}), 400

    student = None
    if '@' in email_or_mobile:
        student = Student.find_by_email(email_or_mobile)
    else:
        student = Student.find_by_mobile(email_or_mobile)

    if not student or not Student.verify_password(student, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=str(student['_id']), additional_claims={'role': 'student'})
    refresh_token = create_refresh_token(identity=str(student['_id']))

    from app.models.activity_log import ActivityLog
    ActivityLog.log(student['_id'], 'student', 'login', 'student', {'method': 'password'})

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': str(student['_id']),
            'name': student['name'],
            'email': student.get('email'),
            'mobile': student.get('mobile'),
            'role': 'student'
        }
    }), 200

@auth_bp.route('/admin/login', methods=['POST'])
def admin_login():
    """Admin login (college_admin or super_admin) - legacy."""
    data = request.get_json()
    print(f"Admin login data received: {data}")
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    admin = Admin.find_by_email(email)
    if not admin or not Admin.verify_password(admin, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    role = admin.get('role')
    valid_roles = ['college_admin', 'course_admin', 'super_admin', 'university_admin', 'global_support', 'local_support']
    if role not in valid_roles:
        return jsonify({'error': 'Invalid admin role'}), 403

    claims = {
        'role': role, 
        'college_id': str(admin.get('college_id')) if admin.get('college_id') else None,
        'university_id': str(admin.get('university_id')) if admin.get('university_id') else None
    }
    access_token = create_access_token(identity=str(admin['_id']), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(admin['_id']))

    from app.models.activity_log import ActivityLog
    ActivityLog.log(admin['_id'], 'admin', 'login', 'admin', {'role': role})

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': str(admin['_id']),
            'name': admin['name'],
            'email': admin['email'],
            'role': role,
            'college_id': str(admin.get('college_id')) if admin.get('college_id') else None,
            'university_id': str(admin.get('university_id')) if admin.get('university_id') else None
        }
    }), 200

@auth_bp.route('/login', methods=['POST'])
def unified_login():
    """Unified login for students and admins."""
    data = request.get_json()
    print(f"Unified login data received: {data}")
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    # Check student
    student = Student.find_by_email(email)
    if student and Student.verify_password(student, password):
        access_token = create_access_token(identity=str(student['_id']), additional_claims={'role': 'student'})
        refresh_token = create_refresh_token(identity=str(student['_id']))
        from app.models.activity_log import ActivityLog
        ActivityLog.log(student['_id'], 'student', 'login', 'student', {'method': 'password'})
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': str(student['_id']),
                'name': student['name'],
                'email': student.get('email'),
                'mobile': student.get('mobile'),
                'role': 'student'
            }
        }), 200

    # Check admin (all roles)
    admin = Admin.find_by_email(email)
    if admin and Admin.verify_password(admin, password):
        role = admin.get('role')
        # All admin roles can login
        valid_roles = ['college_admin', 'course_admin', 'super_admin', 'university_admin', 'global_support', 'local_support']
        if role not in valid_roles:
            return jsonify({'error': 'Invalid admin role'}), 403
        
        claims = {
            'role': role, 
            'college_id': str(admin.get('college_id')) if admin.get('college_id') else None,
            'university_id': str(admin.get('university_id')) if admin.get('university_id') else None
        }
        access_token = create_access_token(identity=str(admin['_id']), additional_claims=claims)
        refresh_token = create_refresh_token(identity=str(admin['_id']))
        from app.models.activity_log import ActivityLog
        ActivityLog.log(admin['_id'], 'admin', 'login', 'admin', {'role': role})
        
        user_data = {
            'id': str(admin['_id']),
            'name': admin['name'],
            'email': admin['email'],
            'role': role,
            'college_id': str(admin.get('college_id')) if admin.get('college_id') else None,
            'university_id': str(admin.get('university_id')) if admin.get('university_id') else None
        }
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user_data
        }), 200

    return jsonify({'error': 'Invalid credentials'}), 401

@auth_bp.route('/google-login', methods=['POST'])
def google_login():
    """Google OAuth login for students."""
    data = request.get_json()
    google_id = data.get('google_id')
    email = data.get('email')
    name = data.get('name')
    if not google_id or not email:
        return jsonify({'error': 'Google ID and email required'}), 400

    student = Student.find_by_google_id(google_id) or Student.find_by_email(email)
    if student:
        if not student.get('google_id'):
            Student.update(student['_id'], {'google_id': google_id})
    else:
        student_data = {
            'name': name,
            'email': email,
            'google_id': google_id,
            'created_by': 'student'
        }
        student_id = Student.create(student_data)
        student = Student.find_by_id(student_id)

    access_token = create_access_token(identity=str(student['_id']), additional_claims={'role': 'student'})
    refresh_token = create_refresh_token(identity=str(student['_id']))

    from app.models.activity_log import ActivityLog
    ActivityLog.log(student['_id'], 'student', 'login', 'student', {'method': 'google'})

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': str(student['_id']),
            'name': student['name'],
            'email': student.get('email'),
            'role': 'student'
        }
    }), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password_request():
    """Request password reset OTP."""
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({'error': 'Email required'}), 400

    student = Student.find_by_email(email)
    if not student:
        return jsonify({'message': 'If the email exists, an OTP will be sent'}), 200

    otp = OTPService.generate_otp(email)
    try:
        send_email(
            to=email,
            subject='Password Reset OTP',
            body=f'Your OTP to reset password is: {otp}. It expires in 10 minutes.'
        )
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        return jsonify({'error': 'Failed to send email'}), 500

    return jsonify({'message': 'OTP sent to email'}), 200

@auth_bp.route('/reset-password/confirm', methods=['POST'])
def reset_password_confirm():
    """Confirm OTP and set new password."""
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    new_password = data.get('new_password')
    if not all([email, otp, new_password]):
        return jsonify({'error': 'Email, OTP, and new password required'}), 400

    if not OTPService.verify_otp(email, otp):
        return jsonify({'error': 'Invalid or expired OTP'}), 400

    student = Student.find_by_email(email)
    if not student:
        return jsonify({'error': 'User not found'}), 404

    if not validate_password(new_password):
        return jsonify({'error': 'Password must be at least 8 characters, include uppercase, lowercase, number'}), 400

    Student.update(student['_id'], {'password': new_password})

    from app.models.activity_log import ActivityLog
    ActivityLog.log(student['_id'], 'student', 'password_reset', 'student', {})

    return jsonify({'message': 'Password updated successfully'}), 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token."""
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({'access_token': access_token}), 200