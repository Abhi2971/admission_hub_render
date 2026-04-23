import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.ai_service import recommend_courses, chat_response
from app.models.ai_profile import AIProfile
from app.models.student_credit import StudentCredit
from app.models.activity_log import ActivityLog

ai_bp = Blueprint('ai', __name__)
logger = logging.getLogger(__name__)

# ... rest of the file (unchanged)

@ai_bp.route('/recommend-courses', methods=['POST'])
@jwt_required()
def recommend():
    student_id = get_jwt_identity()
    data = request.get_json()
    interests = data.get('interests', [])
    skills = data.get('skills', [])
    career_goals = data.get('career_goals', '')

    # Check credits
    credit = StudentCredit.find_by_student(student_id)
    if not credit or credit['balance'] < 1:
        return jsonify({'error': 'Insufficient credits. Please purchase more.'}), 402

    # Update AI profile
    AIProfile.update(student_id, {
        'interests': interests,
        'skills': skills,
        'career_goals': career_goals
    })

    # Get recommendations
    try:
        recommendations = recommend_courses(interests, skills, career_goals, student_id)
        ActivityLog.log(student_id, 'student', 'ai_recommendation', 'ai', {})
        return jsonify({'recommendations': recommendations}), 200
    except Exception as e:
        logger.error(f"AI recommendation error: {e}")
        return jsonify({'error': str(e)}), 500

@ai_bp.route('/career-chat', methods=['POST'])
@jwt_required()
def career_chat():
    student_id = get_jwt_identity()
    data = request.get_json()
    message = data.get('message')
    if not message:
        return jsonify({'error': 'Message required'}), 400

    # Check credits
    credit = StudentCredit.find_by_student(student_id)
    if not credit or credit['balance'] < 1:
        return jsonify({'error': 'Insufficient credits. Please purchase more.'}), 402

    try:
        reply = chat_response(message, student_id)
        return jsonify({'reply': reply}), 200
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        return jsonify({'error': str(e)}), 500