from app.database import get_db
from bson.objectid import ObjectId
from datetime import datetime, timedelta

def get_platform_analytics(start_date=None, end_date=None):
    db = get_db()
    # If no dates provided, match all documents (no filter)
    match_stage = {}
    if start_date and end_date:
        match_stage = {'applied_at': {'$gte': start_date, '$lte': end_date}}

    # Conversion funnel (respects date filter if provided)
    pipeline = [
        {'$match': match_stage},
        {'$group': {
            '_id': None,
            'applied': {'$sum': 1},
            'shortlisted': {'$sum': {'$cond': [{'$in': ['$status', ['shortlisted', 'offered', 'confirmed']]}, 1, 0]}},
            'offered': {'$sum': {'$cond': [{'$in': ['$status', ['offered', 'confirmed']]}, 1, 0]}},
            'confirmed': {'$sum': {'$cond': [{'$eq': ['$status', 'confirmed']}, 1, 0]}}
        }}
    ]
    funnel = list(db.applications.aggregate(pipeline))
    funnel = funnel[0] if funnel else {}

    # Revenue over time (requires date range; defaults to last 30 days if not provided)
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    revenue_pipeline = [
        {'$match': {'paid_at': {'$gte': start_date, '$lte': end_date}, 'status': 'success'}},
        {'$group': {
            '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$paid_at'}},
            'daily': {'$sum': '$amount'}
        }},
        {'$sort': {'_id': 1}}
    ]
    revenue = list(db.payments.aggregate(revenue_pipeline))

    # Geographic distribution (respects date filter)
    geo_pipeline = [
        {'$match': match_stage},
        {'$lookup': {'from': 'students', 'localField': 'student_id', 'foreignField': '_id', 'as': 'student'}},
        {'$unwind': '$student'},
        {'$group': {'_id': '$student.location', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]
    geo = list(db.applications.aggregate(geo_pipeline))

    # Total applications (unfiltered)
    total_applications = db.applications.count_documents({})

    # Total revenue (all-time successful payments)
    total_revenue_pipeline = [
        {'$match': {'status': 'success'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    total_revenue_result = list(db.payments.aggregate(total_revenue_pipeline))
    total_revenue = total_revenue_result[0]['total'] if total_revenue_result else 0

    # Count admins
    total_admins = db.admins.count_documents({})

    return {
        'funnel': funnel,
        'revenue': revenue,
        'geo': geo,
        'total_students': db.students.count_documents({}),
        'total_colleges': db.colleges.count_documents({}),
        'total_courses': db.courses.count_documents({}),
        'total_applications': total_applications,
        'total_admins': total_admins,
        'total_revenue': total_revenue,          # <-- added
        'active_subscriptions': db.college_subscriptions.count_documents({'status': 'active'})
    }

def get_college_analytics(college_id):
    """Get analytics for a specific college."""
    from app.database import get_db
    from bson.objectid import ObjectId

    db = get_db()
    college_id_obj = ObjectId(college_id)

    total_courses = db.courses.count_documents({'college_id': college_id_obj})
    total_applications = db.applications.count_documents({'college_id': college_id_obj})

    status_counts = list(db.applications.aggregate([
        {'$match': {'college_id': college_id_obj}},
        {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
    ]))
    app_status = {item['_id']: item['count'] for item in status_counts}

    distinct_students = db.applications.distinct('student_id', {'college_id': college_id_obj})
    total_students = len(distinct_students)

    confirmed = db.applications.count_documents({'college_id': college_id_obj, 'status': 'confirmed'})

    course_popularity = list(db.applications.aggregate([
        {'$match': {'college_id': college_id_obj}},
        {'$group': {'_id': '$course_id', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 5},
        {'$lookup': {'from': 'courses', 'localField': '_id', 'foreignField': '_id', 'as': 'course'}}
    ]))
    for item in course_popularity:
        item['_id'] = str(item['_id'])
        if item['course']:
            item['course_name'] = item['course'][0].get('course_name')
        else:
            item['course_name'] = 'Unknown'

    return {
        'total_courses': total_courses,
        'total_applications': total_applications,
        'application_status': app_status,
        'total_students': total_students,
        'confirmed_admissions': confirmed,
        'course_popularity': course_popularity
    }