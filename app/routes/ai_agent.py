import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from groq import Groq
from app.database import get_db
from app.models.student import Student
from app.models.college import College
from app.models.course import Course
from app.models.application import Application
from app.models.student_credit import StudentCredit
from app.models.ai_profile import AIProfile
from app.models.ai_usage_log import AIUsageLog
from flask import current_app
import re

ai_agent_bp = Blueprint('ai_agent', __name__)
logger = logging.getLogger(__name__)

def get_groq_client():
    api_key = current_app.config.get('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in configuration")
    return Groq(api_key=api_key)

def get_student_context(student_id):
    """Get comprehensive context about a student including profile, applications, and recommendations."""
    student = Student.find_by_id(student_id)
    if not student:
        return None, None, None
    
    db = get_db()
    
    student_profile = {
        'name': student.get('name'),
        'email': student.get('email'),
        'mobile': student.get('mobile'),
        'college_name': student.get('college_name'),
        'preferred_course': student.get('preferred_course'),
        'year': student.get('year'),
        'location': student.get('location'),
        'interests': [],
        'skills': []
    }
    
    ai_profile = AIProfile.find_by_student(student_id)
    if ai_profile:
        student_profile['interests'] = ai_profile.get('interests', [])
        student_profile['skills'] = ai_profile.get('skills', [])
        student_profile['career_goals'] = ai_profile.get('career_goals', '')
    
    existing_applications = Application.find_by_student(student_id)
    applied_course_ids = [str(app.get('course_id')) for app in existing_applications]
    applied_college_ids = [str(app.get('college_id')) for app in existing_applications]
    
    all_courses = list(db.courses.find())
    all_colleges = list(db.colleges.find())
    
    courses_context = []
    for course in all_courses:
        college = next((c for c in all_colleges if str(c['_id']) == str(course.get('college_id'))), None)
        courses_context.append({
            'course_id': str(course['_id']),
            'course_name': course.get('course_name'),
            'domain': course.get('domain'),
            'duration': course.get('duration'),
            'fees': course.get('fees'),
            'available_seats': course.get('available_seats'),
            'eligibility': course.get('eligibility'),
            'college_id': str(course.get('college_id')),
            'college_name': college.get('name') if college else 'Unknown',
            'college_city': college.get('city') if college else 'Unknown',
            'is_applied': str(course['_id']) in applied_course_ids
        })
    
    colleges_context = []
    for college in all_colleges:
        college_courses = [c for c in courses_context if c['college_id'] == str(college['_id'])]
        colleges_context.append({
            'college_id': str(college['_id']),
            'name': college.get('name'),
            'code': college.get('code'),
            'city': college.get('city'),
            'state': college.get('state'),
            'contact_email': college.get('contact_email'),
            'courses_count': len(college_courses),
            'is_applied': str(college['_id']) in applied_college_ids
        })
    
    credit = StudentCredit.find_by_student(student_id)
    credits_balance = credit['balance'] if credit else 0
    
    return student_profile, courses_context, colleges_context, credits_balance

def parse_command(user_message):
    """Parse user message to detect intent/command."""
    message_lower = user_message.lower().strip()
    
    commands = {
        'update_profile': [
            r'update\s*(my)?\s*profile',
            r'edit\s*(my)?\s*profile',
            r'change\s*(my)?\s*profile',
            r'modify\s*(my)?\s*profile',
            r'i\s*want\s*to\s*update',
            r'change\s*my\s*(name|email|mobile|location)',
            r'edit\s*my\s*(name|email|mobile|location)'
        ],
        'apply_college': [
            r'apply\s*(for|to)',
            r'want\s*(to)?\s*apply',
            r'submit\s*application',
            r'register\s*for',
            r'enroll\s*(in|for)'
        ],
        'recommend': [
            r'recommend\s*(me)?',
            r'suggest\s*(me)?',
            r'what\s*(should|would)\s*(i|you)\s*(choose|pick|take)',
            r'best\s*(courses?|colleges?)',
            r'which\s*(courses?|colleges?)\s*(is|are)\s*(best|suitable)',
            r'help\s*(me)?\s*(choose|pick|find)',
            r'find\s*(me)?\s*(suitable|matching)'
        ],
        'my_applications': [
            r'my\s*applications',
            r'my\s*status',
            r'application\s*status',
            r'where\s*(is|are)\s*my\s*applications',
            r'check\s*(my)?\s*applications'
        ],
        'my_profile': [
            r'my\s*profile',
            r'show\s*(me)?\s*profile',
            r'what\s*(is)?\s*(my)?\s*profile',
            r'profile\s*info'
        ],
        'browse_courses': [
            r'browse\s*courses',
            r'show\s*(me)?\s*all\s*courses',
            r'list\s*courses',
            r'what\s*courses',
            r'show\s*available\s*courses'
        ],
        'browse_colleges': [
            r'browse\s*colleges',
            r'show\s*(me)?\s*all\s*colleges',
            r'list\s*colleges',
            r'what\s*colleges',
            r'show\s*available\s*colleges'
        ],
        'chat': [
            r'how\s*are\s*you',
            r'hi|hello|hey',
            r'what\s*can\s*(i|you)\s*do',
            r'help',
            r'thanks?|thank\s*you'
        ]
    }
    
    for intent, patterns in commands.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                return intent
    
    return 'general'

def build_system_prompt(student_profile, courses_context, colleges_context, credits_balance):
    """Build system prompt with student context and available data."""
    
    courses_str = ""
    if courses_context:
        for c in courses_context[:20]:
            status = "ALREADY APPLIED" if c['is_applied'] else "AVAILABLE"
            courses_str += f"- [{status}] {c['course_name']} at {c['college_name']} ({c['college_city']}) - {c['domain']}, Duration: {c['duration']}, Fees: ₹{c['fees']}, Seats: {c['available_seats']}\n"
    
    colleges_str = ""
    if colleges_context:
        for col in colleges_context[:15]:
            status = "ALREADY APPLIED" if col['is_applied'] else "AVAILABLE"
            colleges_str += f"- [{status}] {col['name']} ({col['code']}) - {col['city']}, {col['state']} - {col['courses_count']} courses\n"
    
    profile_str = f"Student Name: {student_profile['name']}\n"
    profile_str += f"Email: {student_profile['email']}\n"
    profile_str += f"Mobile: {student_profile['mobile']}\n"
    profile_str += f"Current College: {student_profile['college_name'] or 'N/A'}\n"
    profile_str += f"Preferred Course: {student_profile['preferred_course'] or 'N/A'}\n"
    profile_str += f"Year: {student_profile['year'] or 'N/A'}\n"
    profile_str += f"Location: {student_profile['location'] or 'N/A'}\n"
    profile_str += f"Interests: {', '.join(student_profile['interests']) if student_profile['interests'] else 'Not specified'}\n"
    profile_str += f"Skills: {', '.join(student_profile['skills']) if student_profile['skills'] else 'Not specified'}\n"
    profile_str += f"AI Credits Balance: {credits_balance}\n"
    
    system_prompt = f"""You are an AI Admission Copilot Assistant for students. You help students with:
1. Finding suitable courses and colleges
2. Applying to colleges
3. Updating their profile
4. Understanding their application status
5. Career guidance

STUDENT PROFILE:
{profile_str}

AVAILABLE COURSES IN DATABASE:
{courses_str if courses_str else "No courses available currently."}

AVAILABLE COLLEGES IN DATABASE:
{colleges_str if colleges_str else "No colleges available currently."}

IMPORTANT RULES:
1. ALWAYS reference specific course names and college names from the available data above
2. For recommendations, match student interests/skills/preferred_course with course domains
3. For applying to courses, tell the student to use the apply button on the course detail page
4. For profile updates, guide them to their profile settings
5. Keep responses conversational but informative
6. If a course/college is already applied, mention that
7. If credits are low (<5), suggest purchasing more credits
8. Provide specific suggestions based on student's profile data

AVAILABLE COMMANDS the student can ask:
- "recommend courses for me" or "suggest best courses based on my interests"
- "apply for [course name] at [college name]" or "I want to apply for [course]"
- "update my profile" or "change my [field]"
- "show my applications" or "what's my application status"
- "show available courses" or "list all courses"
- "show available colleges" or "list all colleges"

Respond in a helpful, conversational manner. Format recommendations as a bulleted list when appropriate."""
    
    return system_prompt

@ai_agent_bp.route('/agent', methods=['POST'])
@jwt_required()
def agent_chat():
    """Unified AI agent endpoint with full student context."""
    student_id = get_jwt_identity()
    data = request.get_json()
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    student_profile, courses_context, colleges_context, credits_balance = get_student_context(student_id)
    if not student_profile:
        return jsonify({'error': 'Student not found'}), 404
    
    if credits_balance < 1:
        return jsonify({
            'error': 'Insufficient credits',
            'credits_balance': credits_balance,
            'suggestion': 'Please purchase more credits to continue using AI features.'
        }), 402
    
    intent = parse_command(message)
    action_needed = None
    
    if intent == 'recommend':
        recommended_courses = []
        for course in courses_context:
            if not course['is_applied']:
                score = 0
                course_domain = course['domain'].lower() if course['domain'] else ''
                preferred = (student_profile.get('preferred_course') or '').lower()
                
                if student_profile.get('interests'):
                    for interest in student_profile['interests']:
                        if interest.lower() in course_domain:
                            score += 2
                
                if preferred in course_domain or course_domain in preferred:
                    score += 3
                
                if course['available_seats'] > 0:
                    score += 1
                
                recommended_courses.append({**course, 'match_score': score})
        
        recommended_courses.sort(key=lambda x: x['match_score'], reverse=True)
        top_recommendations = recommended_courses[:5]
        
        action_needed = {
            'type': 'recommendation',
            'courses': [{
                'course_id': c['course_id'],
                'course_name': c['course_name'],
                'college_name': c['college_name'],
                'domain': c['domain'],
                'fees': c['fees'],
                'match_score': c['match_score']
            } for c in top_recommendations]
        }
    
    try:
        client = get_groq_client()
        
        system_prompt = build_system_prompt(student_profile, courses_context, colleges_context, credits_balance)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        reply = response.choices[0].message.content
        
        StudentCredit.deduct_credits(student_id, 1)
        AIUsageLog.log(student_id, 'agent_chat', 1)
        
        result = {
            'reply': reply,
            'intent': intent,
            'credits_remaining': credits_balance - 1
        }
        
        if action_needed:
            result['action'] = action_needed
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"AI Agent error: {e}")
        return jsonify({'error': 'Failed to process request'}), 500

@ai_agent_bp.route('/recommendations/detailed', methods=['POST'])
@jwt_required()
def detailed_recommendations():
    """Get detailed course recommendations with full context."""
    student_id = get_jwt_identity()
    data = request.get_json()
    
    interests = data.get('interests', [])
    skills = data.get('skills', [])
    career_goals = data.get('career_goals', '')
    
    student_profile, courses_context, colleges_context, credits_balance = get_student_context(student_id)
    if not student_profile:
        return jsonify({'error': 'Student not found'}), 404
    
    if credits_balance < 1:
        return jsonify({
            'error': 'Insufficient credits',
            'credits_balance': credits_balance
        }), 402
    
    scored_courses = []
    for course in courses_context:
        if course['is_applied']:
            continue
        
        score = 0
        reasons = []
        
        course_domain = course['domain'].lower() if course['domain'] else ''
        course_name = course['course_name'].lower() if course['course_name'] else ''
        
        for interest in interests:
            if interest.lower() in course_domain or interest.lower() in course_name:
                score += 3
                reasons.append(f"Matches your interest in {interest}")
        
        for skill in skills:
            if skill.lower() in course_domain or skill.lower() in course_name:
                score += 2
                reasons.append(f"Uses your skill: {skill}")
        
        if career_goals:
            if any(word in course_name for word in career_goals.lower().split()[:3]):
                score += 2
                reasons.append("Aligns with your career goals")
        
        if course['available_seats'] > 10:
            score += 1
            reasons.append("Good availability of seats")
        
        if course['fees'] < 500000:
            score += 1
            reasons.append("Affordable fees")
        
        scored_courses.append({
            **course,
            'match_score': score,
            'reasons': reasons[:3]
        })
    
    scored_courses.sort(key=lambda x: x['match_score'], reverse=True)
    
    AIProfile.update(student_id, {
        'interests': interests,
        'skills': skills,
        'career_goals': career_goals
    })
    
    StudentCredit.deduct_credits(student_id, 1)
    AIUsageLog.log(student_id, 'detailed_recommendation', 1)
    
    return jsonify({
        'recommendations': scored_courses[:10],
        'student_profile': {
            'interests': interests,
            'skills': skills,
            'career_goals': career_goals
        },
        'total_courses_matched': len(scored_courses),
        'credits_remaining': credits_balance - 1
    }), 200

@ai_agent_bp.route('/quick-actions', methods=['GET'])
@jwt_required()
def get_quick_actions():
    """Get available quick actions for the student."""
    student_id = get_jwt_identity()
    student_profile, courses_context, colleges_context, credits_balance = get_student_context(student_id)
    
    if not student_profile:
        return jsonify({'error': 'Student not found'}), 404
    
    applied_courses = [c for c in courses_context if c['is_applied']]
    available_courses = [c for c in courses_context if not c['is_applied']]
    
    suggestions = []
    
    if not student_profile.get('interests') or not student_profile.get('skills'):
        suggestions.append({
            'action': 'complete_profile',
            'title': 'Complete Your Profile',
            'description': 'Add your interests and skills for better recommendations',
            'priority': 'high'
        })
    
    if applied_courses:
        suggestions.append({
            'action': 'check_applications',
            'title': 'Check Application Status',
            'description': f'You have {len(applied_courses)} active applications',
            'priority': 'medium'
        })
    
    if available_courses:
        suggestions.append({
            'action': 'get_recommendations',
            'title': 'Get Personalized Recommendations',
            'description': 'Based on your profile and available courses',
            'priority': 'high'
        })
    
    if credits_balance < 5:
        suggestions.append({
            'action': 'buy_credits',
            'title': 'Low on AI Credits',
            'description': f'Only {credits_balance} credits left',
            'priority': 'high'
        })
    
    return jsonify({
        'quick_actions': suggestions,
        'stats': {
            'credits_balance': credits_balance,
            'applied_courses': len(applied_courses),
            'available_courses': len(available_courses),
            'profile_completion': calculate_profile_completion(student_profile)
        }
    }), 200

def calculate_profile_completion(profile):
    required_fields = ['name', 'email', 'mobile', 'preferred_course', 'location']
    completed = sum(1 for field in required_fields if profile.get(field))
    return int((completed / len(required_fields)) * 100)


@ai_agent_bp.route('/history', methods=['GET'])
@jwt_required()
def get_chat_history():
    """Get student's chat history."""
    student_id = get_jwt_identity()
    from app.models.chat_history import ChatHistory
    history = ChatHistory.get_history(student_id)
    return jsonify({'history': history}), 200


@ai_agent_bp.route('/history', methods=['POST'])
@jwt_required()
def save_chat_message():
    """Save a chat message to history."""
    student_id = get_jwt_identity()
    data = request.get_json()
    
    role = data.get('role')
    content = data.get('content')
    intent = data.get('intent')
    
    if not role or not content:
        return jsonify({'error': 'Role and content are required'}), 400
    
    if role not in ['user', 'bot']:
        return jsonify({'error': 'Invalid role'}), 400
    
    from app.models.chat_history import ChatHistory
    message = ChatHistory.save_message(student_id, role, content, intent)
    
    return jsonify({'saved': True, 'message': message}), 201


@ai_agent_bp.route('/history/clear', methods=['DELETE'])
@jwt_required()
def clear_chat_history():
    """Clear student's chat history."""
    student_id = get_jwt_identity()
    from app.models.chat_history import ChatHistory
    ChatHistory.clear_history(student_id)
    return jsonify({'cleared': True}), 200


@ai_agent_bp.route('/chat', methods=['POST'])
@jwt_required()
def student_chat():
    """Enhanced chat endpoint with history, database lookup, and focused college admission responses."""
    student_id = get_jwt_identity()
    data = request.get_json()
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    student_profile, courses_context, colleges_context, credits_balance = get_student_context(student_id)
    if not student_profile:
        return jsonify({'error': 'Student not found'}), 404
    
    if credits_balance < 1:
        return jsonify({
            'error': 'Insufficient credits',
            'credits_balance': credits_balance,
            'suggestion': 'Please purchase more credits to continue using AI features.'
        }), 402
    
    message_lower = message.lower().strip()
    
    off_topic_patterns = [
        'weather', 'news', 'sports', 'movies', 'music', 'politics', 'stock market',
        'bitcoin', 'crypto', 'gaming', 'joke', 'recipe', 'news', 'code', 'programming',
        'python', 'javascript', 'html', 'css', 'game', 'playstation', 'xbox'
    ]
    
    for pattern in off_topic_patterns:
        if len(message_lower) < 20 and pattern in message_lower:
            return jsonify({
                'reply': f"I'm your College Admission AI Advisor! 🎓 I can help you with:\n\n✅ Finding suitable courses and colleges\n✅ Getting admission guidance\n✅ Understanding eligibility criteria\n✅ Checking application status\n✅ Course recommendations based on your profile\n\nPlease ask me about college admissions, courses, or career guidance!",
                'intent': 'off_topic',
                'credits_remaining': credits_balance,
                'redirect': False
            }), 200
    
    try:
        client = get_groq_client()
        
        from app.models.chat_history import ChatHistory
        history = ChatHistory.get_history(student_id, limit=10)
        
        chat_history_formatted = ""
        for msg in history[-6:]:
            role = "Assistant" if msg['role'] == 'bot' else "Student"
            chat_history_formatted += f"{role}: {msg['content']}\n"
        
        search_terms = message_lower.split()
        matching_courses = []
        matching_colleges = []
        
        for course in courses_context:
            course_name_lower = course['course_name'].lower() if course['course_name'] else ''
            college_name_lower = course['college_name'].lower() if course['college_name'] else ''
            domain_lower = course['domain'].lower() if course['domain'] else ''
            
            for term in search_terms:
                if len(term) > 2:
                    if term in course_name_lower or term in college_name_lower or term in domain_lower:
                        matching_courses.append(course)
                        break
        
        for college in colleges_context:
            college_name_lower = college['name'].lower() if college['name'] else ''
            for term in search_terms:
                if len(term) > 2 and term in college_name_lower:
                    matching_colleges.append(college)
                    break
        
        db_info = ""
        if matching_courses:
            db_info += f"\n\nAVAILABLE COURSES:\n"
            for c in matching_courses[:5]:
                db_info += f"- {c['course_name']} at {c['college_name']} ({c['college_city']}) - ₹{c['fees']}, Seats: {c['available_seats']}\n"
        
        if matching_colleges:
            db_info += f"\n\nAVAILABLE COLLEGES:\n"
            for col in matching_colleges[:5]:
                db_info += f"- {col['name']} ({col['code']}) - {col['city']}, {col['state']} - {col['courses_count']} courses\n"
        
        system_prompt = f"""You are an AI Admission Advisor for an Indian college admission system.

Your job is to recommend the best courses, colleges, and universities based on student profile.

STUDENT PROFILE:
- Name: {student_profile['name']}
- Preferred Course: {student_profile['preferred_course'] or 'Not specified'}
- Location/State: {student_profile['location'] or 'Not specified'}
- Current College: {student_profile['college_name'] or 'N/A'}

{db_info if db_info else '\nNo matching courses or colleges found. Provide general guidance.'}

RULES:
1. Recommend only ELIGIBLE courses based on student's qualification
2. Prefer colleges in the student's state/region
3. Suggest 3-5 best options only
4. If percentage is high (>80%), suggest top colleges
5. If percentage is low (<50%), suggest safe/affordable options
6. Keep answer short and structured

Output format (use this structure):
**Recommended Courses:**
1. Course name - College - Fees - Why recommended

**Recommended Colleges:**
1. College name - Location - Why recommended

**Eligibility & Reason:**
- Your eligibility status
- Why these are good choices for you

**Next Steps:**
- What to do next

Be helpful, encouraging, and specific. If no data available, give general guidance.

Recent conversation:
{chat_history_formatted}

Student's question: {message}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        reply = response.choices[0].message.content
        
        StudentCredit.deduct_credits(student_id, 1)
        AIUsageLog.log(student_id, 'student_chat', 1)
        ChatHistory.save_message(student_id, 'user', message)
        ChatHistory.save_message(student_id, 'bot', reply)
        
        return jsonify({
            'reply': reply,
            'credits_remaining': credits_balance - 1,
            'saved': True,
            'matching_data': {
                'courses': matching_courses[:5],
                'colleges': matching_colleges[:5]
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Student chat error: {e}")
        return jsonify({'error': 'Failed to process request'}), 500
