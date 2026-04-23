import logging
from flask import current_app
from groq import Groq
from app.models.student_credit import StudentCredit
from app.models.ai_usage_log import AIUsageLog

logger = logging.getLogger(__name__)

def get_groq_client():
    """Get Groq client lazily using current_app context."""
    api_key = current_app.config.get('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in configuration")
    return Groq(api_key=api_key)

def recommend_courses(interests, skills, career_goals, student_id=None):
    """Use Groq to generate personalized course recommendations."""
    if student_id:
        credit = StudentCredit.find_by_student(student_id)
        if not credit or credit['balance'] < 1:
            raise Exception("Insufficient credits")
        StudentCredit.deduct_credits(student_id, 1)
        AIUsageLog.log(student_id, 'recommendation', 1)

    prompt = f"""
    Based on the following student profile, recommend suitable courses from our database.
    Interests: {interests}
    Skills: {skills}
    Career Goals: {career_goals}
    Provide a list of course names and a brief explanation.
    """
    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        current_app.logger.error(f"Groq error: {e}")
        return "Unable to generate recommendations at this time."

def chat_response(message, student_id=None):
    """AI chatbot with context and credit check."""
    if student_id:
        credit = StudentCredit.find_by_student(student_id)
        if not credit or credit['balance'] < 1:
            raise Exception("Insufficient credits")
        StudentCredit.deduct_credits(student_id, 1)
        AIUsageLog.log(student_id, 'chat', 1)

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful career guidance assistant for students."},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        current_app.logger.error(f"Groq error: {e}")
        return "I'm having trouble responding right now. Please try again later."