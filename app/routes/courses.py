import logging
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from app.models.course import Course
from app.models.college import College

courses_bp = Blueprint('courses', __name__)
logger = logging.getLogger(__name__)

@courses_bp.route('/', methods=['GET'])
def get_courses():
    """Get paginated list of courses with optional filters."""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    college_id = request.args.get('college_id')
    domain = request.args.get('domain')
    search = request.args.get('search')

    query = {}
    if college_id:
        try:
            query['college_id'] = ObjectId(college_id)
        except:
            return jsonify({'error': 'Invalid college_id'}), 400
    if domain:
        query['domain'] = domain
    if search:
        query['$or'] = [
            {'course_name': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}}
        ]

    courses = Course.get_all(query, page, per_page)
    from app.database import get_db
    db = get_db()
    total = db.courses.count_documents(query)
    result = []
    for c in courses:
        c['_id'] = str(c['_id'])
        c['college_id'] = str(c['college_id'])
        college = College.find_by_id(c['college_id'])
        if college:
            c['college_name'] = college.get('name')
            c['college_city'] = college.get('city')
        # Ensure required_documents is present
        c['required_documents'] = c.get('required_documents', [])
        result.append(c)

    return jsonify({
        'courses': result,
        'page': page,
        'per_page': per_page,
        'total': total
    }), 200

@courses_bp.route('/<course_id>', methods=['GET'])
def get_course(course_id):
    """Get course details by ID."""
    try:
        course = Course.find_by_id(course_id)
    except:
        return jsonify({'error': 'Invalid course ID'}), 400

    if not course:
        return jsonify({'error': 'Course not found'}), 404

    course['_id'] = str(course['_id'])
    course['college_id'] = str(course['college_id'])
    college = College.find_by_id(course['college_id'])
    if college:
        course['college_name'] = college.get('name')
        course['college_details'] = {
            'address': college.get('address'),
            'city': college.get('city'),
            'state': college.get('state'),
            'contact_email': college.get('contact_email')
        }
    course['required_documents'] = course.get('required_documents', [])
    return jsonify(course), 200

@courses_bp.route('/recommended', methods=['GET'])
def get_recommended_courses():
    """Simple recommendation based on query parameters (e.g., interest)."""
    interest = request.args.get('interest', '')
    if not interest:
        return jsonify({'courses': []}), 200

    from app.database import get_db
    db = get_db()
    courses = list(db.courses.find({
        '$or': [
            {'domain': {'$regex': interest, '$options': 'i'}},
            {'course_name': {'$regex': interest, '$options': 'i'}},
            {'description': {'$regex': interest, '$options': 'i'}}
        ]
    }).limit(10))

    for c in courses:
        c['_id'] = str(c['_id'])
        c['college_id'] = str(c['college_id'])
        college = College.find_by_id(c['college_id'])
        if college:
            c['college_name'] = college.get('name')
        c['required_documents'] = c.get('required_documents', [])
    return jsonify({'courses': courses}), 200


@courses_bp.route('/eligible', methods=['GET'])
def get_eligible_courses():
    """Get courses eligible for a student's qualification."""
    qualification = request.args.get('qualification', '12th')
    stream = request.args.get('stream', 'science')
    
    courses = Course.get_eligible_courses(qualification, stream)
    
    result = []
    for c in courses:
        c['_id'] = str(c['_id'])
        c['college_id'] = str(c['college_id'])
        college = College.find_by_id(c['college_id'])
        if college:
            c['college_name'] = college.get('name')
            c['college_city'] = college.get('city')
        c['required_documents'] = c.get('required_documents', [])
        result.append(c)
    
    return jsonify({'courses': result}), 200