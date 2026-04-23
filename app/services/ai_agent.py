import json
from flask import current_app
from groq import Groq
from app.database import get_db
from bson.objectid import ObjectId

def get_groq_client():
    api_key = current_app.config.get('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")
    return Groq(api_key=api_key)

def search_courses(query):
    """Search courses in database based on keywords."""
    db = get_db()
    # Simple text search (can be improved)
    pipeline = [
        {'$match': {
            '$or': [
                {'course_name': {'$regex': query, '$options': 'i'}},
                {'domain': {'$regex': query, '$options': 'i'}},
                {'description': {'$regex': query, '$options': 'i'}}
            ]
        }},
        {'$limit': 5},
        {'$lookup': {'from': 'colleges', 'localField': 'college_id', 'foreignField': '_id', 'as': 'college'}}
    ]
    courses = list(db.courses.aggregate(pipeline))
    for c in courses:
        c['_id'] = str(c['_id'])
        c['college_id'] = str(c['college_id'])
        if c.get('college'):
            c['college_name'] = c['college'][0].get('name')
        c.pop('college', None)
    return courses

def process_agent_message(user_message, student_id):
    """Main AI agent logic."""
    client = get_groq_client()
    db = get_db()

    # Fetch student profile (optional)
    student = db.students.find_one({'_id': ObjectId(student_id)})
    student_info = f"Student: {student.get('name')}, Interests: {student.get('preferred_course', 'N/A')}"

    # First, decide if we need to search the database
    # For simplicity, we'll always search for keywords
    # Better to use function calling, but we'll keep it simple
    search_keywords = user_message  # crude, but we can refine
    courses = search_courses(search_keywords)

    # Build context
    context = f"Student info: {student_info}\n\n"
    if courses:
        context += "Relevant courses from our database:\n"
        for c in courses:
            context += f"- {c['course_name']} at {c.get('college_name', 'Unknown')} (Domain: {c.get('domain')}, Duration: {c.get('duration')}, Fees: ₹{c.get('fees')})\n"
    else:
        context += "No exact matches found in database."

    # System prompt
    system_prompt = """You are a helpful career guidance assistant for students. 
    You have access to the student's profile and a list of courses from our database.
    Answer the student's query conversationally, using the provided course list to suggest specific options.
    If no courses match, suggest related fields or ask for more details."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context:\n{context}\n\nStudent query: {user_message}"}
    ]

    try:
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=messages,
            max_tokens=800,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        current_app.logger.error(f"Groq error: {e}")
        return "I'm having trouble connecting to my brain right now. Please try again later."