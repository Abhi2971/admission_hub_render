# backend/app/routes/universities.py
"""
Public university listing for students.
"""
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from app.models.university import University
from app.models.plan import Subscription
from app.database import get_db

universities_bp = Blueprint('universities', __name__)

@universities_bp.route('/', methods=['GET'])
def get_universities():
    """Get paginated list of universities."""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search')
    state = request.args.get('state')

    query = {'is_active': True}
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'code': {'$regex': search, '$options': 'i'}}
        ]
    if state:
        query['state'] = state

    db = get_db()
    total = db.universities.count_documents(query)
    universities = University.get_all(query, page, per_page)
    
    for u in universities:
        u['_id'] = str(u['_id'])
        # Query colleges where is_active is True or not set (None)
        u['college_count'] = db.colleges.count_documents({
            'university_id': ObjectId(u['_id']),
            '$or': [{'is_active': {'$exists': False}}, {'is_active': True}]
        })
        sub = Subscription.find_active(u['_id'], 'university')
        u['has_active_plan'] = bool(sub)

    return jsonify({
        'universities': universities,
        'page': page,
        'per_page': per_page,
        'total': total
    }), 200

@universities_bp.route('/<university_id>', methods=['GET'])
def get_university(university_id):
    """Get university details by ID."""
    university = University.find_by_id(university_id)
    if not university:
        return jsonify({'error': 'University not found'}), 404

    university['_id'] = str(university['_id'])
    
    db = get_db()
    # Query colleges where is_active is True or not set (None)
    university['college_count'] = db.colleges.count_documents({
        'university_id': ObjectId(university['_id']),
        '$or': [{'is_active': {'$exists': False}}, {'is_active': True}]
    })
    university['colleges'] = list(db.colleges.find({
        'university_id': ObjectId(university['_id']),
        '$or': [{'is_active': {'$exists': False}}, {'is_active': True}]
    }))
    for c in university['colleges']:
        c['_id'] = str(c['_id'])
        if 'university_id' in c:
            c['university_id'] = str(c['university_id'])
        c['course_count'] = db.courses.count_documents({'college_id': c['_id']})

    sub = Subscription.find_active(university['_id'], 'university')
    university['has_active_plan'] = bool(sub)

    return jsonify(university), 200

@universities_bp.route('/<university_id>/colleges', methods=['GET'])
def get_university_colleges(university_id):
    """Get all colleges for a university."""
    db = get_db()
    colleges = list(db.colleges.find({
        'university_id': ObjectId(university_id),
        '$or': [{'is_active': {'$exists': False}}, {'is_active': True}]
    }))
    for c in colleges:
        c['_id'] = str(c['_id'])
        if 'university_id' in c:
            c['university_id'] = str(c['university_id'])
        c['course_count'] = db.courses.count_documents({'college_id': c['_id']})
    return jsonify({'colleges': colleges}), 200

@universities_bp.route('/states', methods=['GET'])
def get_states():
    """Get all states with universities."""
    db = get_db()
    states = db.universities.distinct('state', {'is_active': True})
    return jsonify({'states': sorted(states)}), 200
