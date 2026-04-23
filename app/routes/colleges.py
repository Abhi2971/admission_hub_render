# backend/app/routes/colleges.py
"""
Public college listing and details.
"""
import logging
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from app.models.college import College
from app.models.course import Course
from app.database import get_db

colleges_bp = Blueprint('colleges', __name__)
logger = logging.getLogger(__name__)

@colleges_bp.route('/', methods=['GET'])
def get_colleges():
    """Get paginated list of colleges."""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    city = request.args.get('city')
    state = request.args.get('state')
    search = request.args.get('search')
    university_id = request.args.get('university_id')

    query = {'$or': [{'is_active': {'$exists': False}}, {'is_active': True}]}
    if city:
        query['city'] = city
    if state:
        query['state'] = state
    if university_id:
        query['university_id'] = ObjectId(university_id)
    if search:
        query['$and'] = query.get('$and', []) + [
            {'$or': [
                {'name': {'$regex': search, '$options': 'i'}},
                {'code': {'$regex': search, '$options': 'i'}}
            ]}
        ]

    db = get_db()
    total = db.colleges.count_documents(query)
    colleges = College.get_all(query, page, per_page)
    
    for c in colleges:
        c['_id'] = str(c['_id'])
        if 'university_id' in c and c['university_id']:
            c['university_id'] = str(c['university_id'])
            uni = db.universities.find_one({'_id': ObjectId(c['university_id'])})
            if uni:
                c['university_name'] = uni.get('name', '')
                c['university_code'] = uni.get('code', '')
        c['course_count'] = db.courses.count_documents({'college_id': c['_id']})

    return jsonify({
        'colleges': colleges,
        'page': page,
        'per_page': per_page,
        'total': total
    }), 200

@colleges_bp.route('/<college_id>', methods=['GET'])
def get_college(college_id):
    """Get college details by ID."""
    try:
        college = College.find_by_id(college_id)
    except:
        return jsonify({'error': 'Invalid college ID'}), 400

    if not college:
        return jsonify({'error': 'College not found'}), 404

    college['_id'] = str(college['_id'])
    if 'university_id' in college and college['university_id']:
        college['university_id'] = str(college['university_id'])
        db = get_db()
        uni = db.universities.find_one({'_id': ObjectId(college['university_id'])})
        if uni:
            college['university_name'] = uni.get('name', '')
            college['university_code'] = uni.get('code', '')
    
    return jsonify(college), 200

@colleges_bp.route('/<college_id>/courses', methods=['GET'])
def get_college_courses(college_id):
    """Get all courses for a specific college."""
    try:
        courses = Course.find_by_college(college_id)
    except:
        return jsonify({'error': 'Invalid college ID'}), 400

    for c in courses:
        c['_id'] = str(c['_id'])
        c['college_id'] = str(c['college_id'])

    return jsonify(courses), 200