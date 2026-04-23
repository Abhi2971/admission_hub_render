# backend/seed.py
"""
Seed script to populate initial data with complete RBAC hierarchy.

ROLE HIERARCHY:
SuperAdmin -> University Admin -> College Admin -> Course Admin -> Student

SUBSCRIPTION SYSTEM:
- Plans created by SuperAdmin for: University, College, Student
- AI access based on subscription plan features
- Sidebar AI option only visible if user has AI access
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.database import get_db
from app.models.student import Student
from app.models.university import University
from app.models.college import College
from app.models.course import Course
from app.models.admin import Admin
from app.models.student_credit import StudentCredit
from app.models.ai_profile import AIProfile
from app.models.application import Application
from app.models.plan import Plan, Subscription
from app.models.college_subscription import CollegeSubscription
from bson.objectid import ObjectId
from datetime import datetime, timedelta, timezone
import random

app = create_app()
with app.app_context():
    db = get_db()

    # Clear existing data
    print("Clearing existing collections...")
    db.students.delete_many({})
    db.universities.delete_many({})
    db.colleges.delete_many({})
    db.courses.delete_many({})
    db.admins.delete_many({})
    db.plans.delete_many({})
    db.subscriptions.delete_many({})
    db.college_subscriptions.delete_many({})
    db.student_credits.delete_many({})
    db.ai_profiles.delete_many({})
    db.applications.delete_many({})
    db.support_tickets.delete_many({})

    # ============================================================
    # SUPER ADMIN (Platform Owner)
    # ============================================================
    super_admin_data = {
        'name': 'Super Admin',
        'email': 'superadmin@example.com',
        'password': 'Admin@123',
        'role': 'super_admin',
        'mobile': '9999999999'
    }
    super_admin_id = Admin.create(super_admin_data)
    print("[OK] Super admin created")

    # Global Support
    global_support_data = {
        'name': 'Global Support',
        'email': 'support@platform.com',
        'password': 'Support@123',
        'role': 'global_support',
        'mobile': '9999999998'
    }
    global_support_id = Admin.create(global_support_data)
    print("[OK] Global support created")

    # ============================================================
    # PLANS (Created by SuperAdmin)
    # ============================================================
    print("\n--- Creating Plans ---")

    # University Plans
    university_plans = [
        {
            'plan_name': 'University Starter',
            'plan_type': 'university',
            'price': 9999,
            'billing_period': 'monthly',
            'description': 'Basic plan for universities',
            'features': {
                'ai_enabled': True,
                'ai_credits': 100,
                'max_colleges': 3,
                'analytics': ['basic'],
                'support_level': 'email',
                'custom_branding': False,
                'api_access': False
            }
        },
        {
            'plan_name': 'University Growth',
            'plan_type': 'university',
            'price': 24999,
            'billing_period': 'monthly',
            'description': 'Growth plan for expanding universities',
            'features': {
                'ai_enabled': True,
                'ai_credits': 500,
                'max_colleges': 10,
                'analytics': ['basic', 'advanced'],
                'support_level': 'priority',
                'custom_branding': True,
                'api_access': False
            }
        },
        {
            'plan_name': 'University Enterprise',
            'plan_type': 'university',
            'price': 49999,
            'billing_period': 'monthly',
            'description': 'Enterprise plan for large universities',
            'features': {
                'ai_enabled': True,
                'ai_credits': -1,  # Unlimited
                'max_colleges': -1,  # Unlimited
                'analytics': ['basic', 'advanced', 'realtime'],
                'support_level': 'dedicated',
                'custom_branding': True,
                'api_access': True
            }
        }
    ]
    for plan in university_plans:
        db.plans.update_one(
            {'plan_name': plan['plan_name'], 'plan_type': 'university'},
            {'$set': plan},
            upsert=True
        )
    print(f"[OK] {len(university_plans)} University plans created")

    # College Plans
    college_plans = [
        {
            'plan_name': 'College Starter',
            'plan_type': 'college',
            'price': 1999,
            'billing_period': 'monthly',
            'description': 'Basic plan for colleges',
            'features': {
                'ai_enabled': True,
                'ai_credits': 50,
                'max_courses': 5,
                'analytics': ['basic'],
                'support_level': 'email'
            }
        },
        {
            'plan_name': 'College Growth',
            'plan_type': 'college',
            'price': 4999,
            'billing_period': 'monthly',
            'description': 'Growth plan for colleges',
            'features': {
                'ai_enabled': True,
                'ai_credits': 200,
                'max_courses': 20,
                'analytics': ['basic', 'advanced'],
                'support_level': 'priority'
            }
        },
        {
            'plan_name': 'College Enterprise',
            'plan_type': 'college',
            'price': 9999,
            'billing_period': 'monthly',
            'description': 'Enterprise plan for large colleges',
            'features': {
                'ai_enabled': True,
                'ai_credits': -1,
                'max_courses': -1,
                'analytics': ['basic', 'advanced', 'realtime'],
                'support_level': 'dedicated'
            }
        }
    ]
    for plan in college_plans:
        db.plans.update_one(
            {'plan_name': plan['plan_name'], 'plan_type': 'college'},
            {'$set': plan},
            upsert=True
        )
    print(f"[OK] {len(college_plans)} College plans created")

    # Student Plans (Credit Packs)
    student_plans = [
        {
            'plan_name': 'Starter Pack',
            'plan_type': 'student',
            'price': 499,
            'billing_period': 'one-time',
            'description': '10 AI credits',
            'features': {
                'ai_enabled': True,
                'ai_credits': 10
            }
        },
        {
            'plan_name': 'Pro Pack',
            'plan_type': 'student',
            'price': 999,
            'billing_period': 'one-time',
            'description': '25 AI credits',
            'features': {
                'ai_enabled': True,
                'ai_credits': 25
            }
        },
        {
            'plan_name': 'Unlimited Month',
            'plan_type': 'student',
            'price': 1999,
            'billing_period': 'monthly',
            'description': 'Unlimited AI for 1 month',
            'features': {
                'ai_enabled': True,
                'ai_credits': -1
            }
        }
    ]
    for plan in student_plans:
        db.plans.update_one(
            {'plan_name': plan['plan_name'], 'plan_type': 'student'},
            {'$set': plan},
            upsert=True
        )
    print(f"[OK] {len(student_plans)} Student plans created")

    # ============================================================
    # UNIVERSITIES
    # ============================================================
    print("\n--- Creating Universities ---")

    university1_data = {
        'name': 'Indian Institutes of Technology',
        'code': 'IIT_SYSTEM',
        'description': 'Premier engineering institutes of India, known for excellence in technical education and research. IIT system comprises 23 premier institutions across India.',
        'contact_email': 'iit-board@gov.in',
        'contact_phone': '011-26581000',
        'address': 'IIT Delhi, Hauz Khas',
        'city': 'New Delhi',
        'state': 'Delhi',
        'website': 'https://www.iitd.ac.in',
        'features': {'ai_enabled': True, 'max_colleges': 23, 'support_level': 'dedicated'}
    }
    university1_id = University.create(university1_data)
    print(f"[OK] University 1 (IIT System) created")

    university2_data = {
        'name': 'National Institutes of Technology',
        'code': 'NIT_SYSTEM',
        'description': 'Premier technical universities of India. NITs are autonomous public engineering colleges established by the Government of India.',
        'contact_email': 'nit-board@nic.in',
        'contact_phone': '0124-1234567',
        'address': 'NIT Campus',
        'city': 'New Delhi',
        'state': 'Delhi',
        'website': 'https://www.nit.ac.in',
        'features': {'ai_enabled': True, 'max_colleges': 31, 'support_level': 'priority'}
    }
    university2_id = University.create(university2_data)
    print(f"[OK] University 2 (NIT System) created")

    university3_data = {
        'name': 'Savitribai Phule Pune University',
        'code': 'SPPU',
        'description': 'One of the largest universities in India with a vast network of affiliated colleges. Located in Pune, Maharashtra, known for quality education across disciplines.',
        'contact_email': 'info@unipune.ac.in',
        'contact_phone': '020-25601222',
        'address': 'Ganeshkhind Road',
        'city': 'Pune',
        'state': 'Maharashtra',
        'website': 'https://www.unipune.ac.in',
        'features': {'ai_enabled': True, 'max_colleges': 100, 'support_level': 'standard'}
    }
    university3_id = University.create(university3_data)
    print(f"[OK] University 3 (SPPU) created")

    university4_data = {
        'name': 'University of Mumbai',
        'code': 'UOM',
        'description': 'One of the oldest and largest universities in India, located in Mumbai. Known for diverse range of undergraduate and postgraduate programs.',
        'contact_email': 'info@mu.ac.in',
        'contact_phone': '022-26543000',
        'address': 'Kalina Campus, Santacruz',
        'city': 'Mumbai',
        'state': 'Maharashtra',
        'website': 'https://www.mu.ac.in',
        'features': {'ai_enabled': True, 'max_colleges': 150, 'support_level': 'standard'}
    }
    university4_id = University.create(university4_data)
    print(f"[OK] University 4 (UOM) created")

    # New Universities
    university5_data = {
        'name': 'Anna University',
        'code': 'AU',
        'description': 'Premier technical university in Tamil Nadu, known for engineering education. Located in Chennai, one of the top ranked universities in India.',
        'contact_email': 'info@annauniv.edu',
        'contact_phone': '044-22358316',
        'address': 'Sardar Patel Road',
        'city': 'Chennai',
        'state': 'Tamil Nadu',
        'website': 'https://www.annauniv.edu',
        'features': {'ai_enabled': True, 'max_colleges': 200, 'support_level': 'standard'}
    }
    university5_id = University.create(university5_data)
    print(f"[OK] University 5 (Anna University) created")

    university6_data = {
        'name': 'Jadavpur University',
        'code': 'JU',
        'description': 'Premier research university in Kolkata, West Bengal. Known for excellence in engineering, arts, and science education.',
        'contact_email': 'info@jadavpuruniversity.in',
        'contact_phone': '033-24146666',
        'address': 'Jadavpur',
        'city': 'Kolkata',
        'state': 'West Bengal',
        'website': 'https://www.jadavpuruniversity.in',
        'features': {'ai_enabled': True, 'max_colleges': 50, 'support_level': 'standard'}
    }
    university6_id = University.create(university6_data)
    print(f"[OK] University 6 (Jadavpur University) created")

    # ============================================================
    # UNIVERSITY ADMIN
    # ============================================================
    print("\n--- Creating University Admins ---")

    iit_admin_data = {
        'name': 'IIT System Admin',
        'email': 'university@iit-system.edu',
        'password': 'Admin@123',
        'role': 'university_admin',
        'university_id': university1_id,
        'mobile': '9999999997'
    }
    iit_admin_id = Admin.create(iit_admin_data)
    print(f"[OK] IIT University Admin created")

    nit_admin_data = {
        'name': 'NIT System Admin',
        'email': 'university@nit-system.edu',
        'password': 'Admin@123',
        'role': 'university_admin',
        'university_id': university2_id,
        'mobile': '9999999996'
    }
    nit_admin_id = Admin.create(nit_admin_data)
    print(f"[OK] NIT University Admin created")

    # Local Support
    local_support_data = {
        'name': 'University Support',
        'email': 'university-support@iit-system.edu',
        'password': 'Support@123',
        'role': 'local_support',
        'university_id': university1_id,
        'mobile': '9999999995'
    }
    local_support_id = Admin.create(local_support_data)
    print(f"[OK] Local support created")

    # More University Support Users
    local_support_2 = {
        'name': 'SPPU Support',
        'email': 'support@sppu.edu',
        'password': 'Support@123',
        'role': 'local_support',
        'university_id': university3_id,
        'mobile': '9999999994'
    }
    Admin.create(local_support_2)
    print("[OK] SPPU Support user created")

    local_support_3 = {
        'name': 'UOM Support',
        'email': 'support@uom.edu',
        'password': 'Support@123',
        'role': 'local_support',
        'university_id': university4_id,
        'mobile': '9999999993'
    }
    Admin.create(local_support_3)
    print("[OK] UOM Support user created")

    # Give IIT University a subscription (Enterprise Plan)
    iit_uni_plan = db.plans.find_one({'plan_name': 'University Enterprise', 'plan_type': 'university'})
    if iit_uni_plan:
        Subscription.create(
            entity_id=str(university1_id),
            plan_id=str(iit_uni_plan['_id']),
            entity_type='university'
        )
        print("[OK] IIT University subscribed to Enterprise plan")

    # Give NIT University a subscription (Growth Plan)
    nit_uni_plan = db.plans.find_one({'plan_name': 'University Growth', 'plan_type': 'university'})
    if nit_uni_plan:
        Subscription.create(
            entity_id=str(university2_id),
            plan_id=str(nit_uni_plan['_id']),
            entity_type='university'
        )
        print("[OK] NIT University subscribed to Growth plan")

    # Give SPPU a subscription (Enterprise Plan)
    if iit_uni_plan:
        Subscription.create(
            entity_id=str(university3_id),
            plan_id=str(iit_uni_plan['_id']),
            entity_type='university'
        )
        print("[OK] SPPU subscribed to Enterprise plan")

    # Give UOM a subscription (Growth Plan)
    if nit_uni_plan:
        Subscription.create(
            entity_id=str(university4_id),
            plan_id=str(nit_uni_plan['_id']),
            entity_type='university'
        )
        print("[OK] UOM subscribed to Growth plan")

    # ============================================================
    # COLLEGES
    # ============================================================
    print("\n--- Creating Colleges ---")

    college1_data = {
        'name': 'Indian Institute of Technology, Bombay',
        'code': 'IITB',
        'address': 'Powai',
        'city': 'Mumbai',
        'state': 'Maharashtra',
        'contact_email': 'info@iitb.ac.in',
        'contact_phone': '022-25722545',
        'website': 'https://www.iitb.ac.in',
        'description': 'Premier engineering institute',
        'university_id': university1_id,
        'created_by': 'university_admin'
    }
    college1_id = College.create(college1_data)
    print(f"[OK] College 1 (IITB) created")

    college2_data = {
        'name': 'Indian Institute of Technology, Delhi',
        'code': 'IITD',
        'address': 'Hauz Khas',
        'city': 'New Delhi',
        'state': 'Delhi',
        'contact_email': 'info@iitd.ac.in',
        'contact_phone': '011-26581000',
        'website': 'https://www.iitd.ac.in',
        'description': 'Top engineering institute',
        'university_id': university1_id,
        'created_by': 'university_admin'
    }
    college2_id = College.create(college2_data)
    print(f"[OK] College 2 (IITD) created")

    # SPPU Colleges
    college3_data = {
        'name': 'College of Engineering, Pune',
        'code': 'COEP',
        'address': 'Wellesley Road',
        'city': 'Pune',
        'state': 'Maharashtra',
        'contact_email': 'info@coep.org.in',
        'contact_phone': '020-25507000',
        'website': 'https://www.coep.org.in',
        'description': 'One of the oldest engineering colleges in Asia',
        'university_id': university3_id,
        'created_by': 'university_admin'
    }
    college3_id = College.create(college3_data)
    print(f"[OK] College 3 (COEP) created")

    college4_data = {
        'name': 'Vishwakarma Institute of Technology',
        'code': 'VIT',
        'address': 'VIT College Road',
        'city': 'Pune',
        'state': 'Maharashtra',
        'contact_email': 'info@vit.edu',
        'contact_phone': '020-24202200',
        'website': 'https://www.vit.edu',
        'description': 'Premier engineering institute in Pune',
        'university_id': university3_id,
        'created_by': 'university_admin'
    }
    college4_id = College.create(college4_data)
    print(f"[OK] College 4 (VIT Pune) created")

    college5_data = {
        'name': 'Pune Institute of Computer Technology',
        'code': 'PICT',
        'address': 'Dhankawadi',
        'city': 'Pune',
        'state': 'Maharashtra',
        'contact_email': 'info@pict.edu',
        'contact_phone': '020-24378090',
        'website': 'https://www.pict.edu',
        'description': 'Top engineering college for Computer Science',
        'university_id': university3_id,
        'created_by': 'university_admin'
    }
    college5_id = College.create(college5_data)
    print(f"[OK] College 5 (PICT) created")

    # UOM Colleges
    college6_data = {
        'name': 'Institute of Chemical Technology',
        'code': 'ICT',
        'address': 'Matunga',
        'city': 'Mumbai',
        'state': 'Maharashtra',
        'contact_email': 'info@ict.edu.in',
        'contact_phone': '022-33612000',
        'website': 'https://www.ict.edu.in',
        'description': 'Premier institute for chemical technology',
        'university_id': university4_id,
        'created_by': 'university_admin'
    }
    college6_id = College.create(college6_data)
    print(f"[OK] College 6 (ICT Mumbai) created")

    college7_data = {
        'name': 'Veermata Jijabai Technological Institute',
        'code': 'VJTI',
        'address': 'Matunga',
        'city': 'Mumbai',
        'state': 'Maharashtra',
        'contact_email': 'info@vjti.ac.in',
        'contact_phone': '022-24198102',
        'website': 'https://www.vjti.ac.in',
        'description': 'One of the oldest engineering colleges in India',
        'university_id': university4_id,
        'created_by': 'university_admin'
    }
    college7_id = College.create(college7_data)
    print(f"[OK] College 7 (VJTI) created")

    college8_data = {
        'name': 'Dwarkadas J. Sanghvi College of Engineering',
        'code': 'DJSCE',
        'address': 'Vile Parle',
        'city': 'Mumbai',
        'state': 'Maharashtra',
        'contact_email': 'info@djscoe.org',
        'contact_phone': '022-42301000',
        'website': 'https://www.djscoe.org',
        'description': 'Top engineering college in Mumbai',
        'university_id': university4_id,
        'created_by': 'university_admin'
    }
    college8_id = College.create(college8_data)
    print(f"[OK] College 8 (DJSCE) created")

    # Give IITB a college subscription (using CollegeSubscription)
    iitb_college_plan = db.plans.find_one({'plan_name': 'College Growth', 'plan_type': 'college'})
    if iitb_college_plan:
        CollegeSubscription.create(
            college_id=college1_id,
            plan_id=iitb_college_plan['_id']
        )
        print("[OK] IITB subscribed to Growth plan")

    # Give COEP a college subscription (using CollegeSubscription)
    if iitb_college_plan:
        CollegeSubscription.create(
            college_id=college3_id,
            plan_id=iitb_college_plan['_id']
        )
        print("[OK] COEP subscribed to Growth plan")

    # Give PICT a college subscription (Starter)
    pict_college_plan = db.plans.find_one({'plan_name': 'College Starter', 'plan_type': 'college'})
    if pict_college_plan:
        CollegeSubscription.create(
            college_id=college5_id,
            plan_id=pict_college_plan['_id']
        )
        print("[OK] PICT subscribed to Starter plan")

    # Give VJTI a college subscription (using CollegeSubscription)
    if iitb_college_plan:
        CollegeSubscription.create(
            college_id=college8_id,
            plan_id=iitb_college_plan['_id']
        )
        print("[OK] VJTI subscribed to Growth plan")

    # ============================================================
    # MORE COLLEGES (Anna University)
    # ============================================================
    print("\n--- Creating Anna University Colleges ---")

    college9_data = {
        'name': 'College of Engineering, Guindy',
        'code': 'CEG',
        'address': 'Guindy',
        'city': 'Chennai',
        'state': 'Tamil Nadu',
        'contact_email': 'info@ceg.res.in',
        'contact_phone': '044-22358316',
        'website': 'https://www.annauniv.edu/ceg',
        'description': 'One of the oldest and most prestigious engineering colleges in India',
        'university_id': university5_id,
        'created_by': 'university_admin'
    }
    college9_id = College.create(college9_data)
    print(f"[OK] College 9 (CEG Chennai) created")

    college10_data = {
        'name': 'PSG College of Technology',
        'code': 'PSGCT',
        'address': 'Peelamedu',
        'city': 'Coimbatore',
        'state': 'Tamil Nadu',
        'contact_email': 'info@psgct.ac.in',
        'contact_phone': '0422-2572177',
        'website': 'https://www.psgct.ac.in',
        'description': 'Premier engineering college in Coimbatore, known for excellent placements',
        'university_id': university5_id,
        'created_by': 'university_admin'
    }
    college10_id = College.create(college10_data)
    print(f"[OK] College 10 (PSGCT Coimbatore) created")

    # Jadavpur University Colleges
    college11_data = {
        'name': 'Jadavpur University - Engineering Faculty',
        'code': 'JU_ENGG',
        'address': 'Jadavpur',
        'city': 'Kolkata',
        'state': 'West Bengal',
        'contact_email': 'info@jadavpuruniversity.in',
        'contact_phone': '033-24146666',
        'website': 'https://www.jadavpuruniversity.in',
        'description': 'Top engineering college in Eastern India',
        'university_id': university6_id,
        'created_by': 'university_admin'
    }
    college11_id = College.create(college11_data)
    print(f"[OK] College 11 (Jadavpur Engineering) created")

    # Give CEG Chennai a college subscription (Growth)
    if iitb_college_plan:
        CollegeSubscription.create(
            college_id=college9_id,
            plan_id=iitb_college_plan['_id']
        )
        print("[OK] CEG Chennai subscribed to Growth plan")

    # Give PSGCT Coimbatore a college subscription (Growth)
    if iitb_college_plan:
        CollegeSubscription.create(
            college_id=college10_id,
            plan_id=iitb_college_plan['_id']
        )
        print("[OK] PSGCT Coimbatore subscribed to Growth plan")

    # Give Jadavpur Engineering a college subscription (Growth)
    if iitb_college_plan:
        CollegeSubscription.create(
            college_id=college11_id,
            plan_id=iitb_college_plan['_id']
        )
        print("[OK] Jadavpur Engineering subscribed to Growth plan")

    # More SPPU Colleges
    college12_data = {
        'name': 'Symbiosis Institute of Technology',
        'code': 'SIT',
        'address': 'Lavale',
        'city': 'Pune',
        'state': 'Maharashtra',
        'contact_email': 'info@sit.edu.in',
        'contact_phone': '020-39116200',
        'website': 'https://www.sit.edu.in',
        'description': 'Part of Symbiosis International University, known for tech education',
        'university_id': university3_id,
        'created_by': 'university_admin'
    }
    college12_id = College.create(college12_data)
    print(f"[OK] College 12 (SIT Pune) created")

    college13_data = {
        'name': 'MIT World Peace University',
        'code': 'MITWPU',
        'address': 'Kothrud',
        'city': 'Pune',
        'state': 'Maharashtra',
        'contact_email': 'info@mitwpu.edu.in',
        'contact_phone': '020-7117710',
        'website': 'https://www.mitwpu.edu.in',
        'description': 'Multi-disciplinary university with excellent engineering programs',
        'university_id': university3_id,
        'created_by': 'university_admin'
    }
    college13_id = College.create(college13_data)
    print(f"[OK] College 13 (MITWPU Pune) created")

    # More UOM Colleges
    college14_data = {
        'name': 'Thadomal Shahani Engineering College',
        'code': 'TSEC',
        'address': 'Bandra West',
        'city': 'Mumbai',
        'state': 'Maharashtra',
        'contact_email': 'info@tsec.edu.in',
        'contact_phone': '022-26495380',
        'website': 'https://www.tsec.edu.in',
        'description': 'One of the best engineering colleges in Mumbai suburbs',
        'university_id': university4_id,
        'created_by': 'university_admin'
    }
    college14_id = College.create(college14_data)
    print(f"[OK] College 14 (TSEC Mumbai) created")

    college15_data = {
        'name': 'Fr. Conceicao Rodrigues College of Engineering',
        'code': 'CRCE',
        'address': 'Bandra West',
        'city': 'Mumbai',
        'state': 'Maharashtra',
        'contact_email': 'info@crce.edu.in',
        'contact_phone': '022-26402265',
        'website': 'https://www.crce.edu.in',
        'description': 'Reputed engineering college in Mumbai',
        'university_id': university4_id,
        'created_by': 'university_admin'
    }
    college15_id = College.create(college15_data)
    print(f"[OK] College 15 (CRCE Mumbai) created")

    # ============================================================
    # COLLEGE ADMIN
    # ============================================================
    print("\n--- Creating College Admins ---")

    admin1_data = {
        'name': 'IIT Bombay Admin',
        'email': 'admin@iitb.ac.in',
        'password': 'Admin@123',
        'role': 'college_admin',
        'college_id': ObjectId(college1_id),
        'mobile': '9876543210'
    }
    admin1_id = Admin.create(admin1_data)
    print(f"[OK] IIT Bombay College Admin created")

    admin2_data = {
        'name': 'IIT Delhi Admin',
        'email': 'admin@iitd.ac.in',
        'password': 'Admin@123',
        'role': 'college_admin',
        'college_id': ObjectId(college2_id),
        'mobile': '9876543211'
    }
    admin2_id = Admin.create(admin2_data)
    print(f"[OK] IIT Delhi College Admin created")

    # ============================================================
    # COURSES
    # ============================================================
    print("\n--- Creating Courses ---")

    courses_iitb = [
        {'course_name': 'B.Tech Computer Science', 'domain': 'Computer Science', 'department': 'Computer Science', 'description': '4-year undergraduate program in CS', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 120, 'available_seats': 120, 'fees': 200000},
        {'course_name': 'B.Tech Electrical Engineering', 'domain': 'Electrical Engineering', 'department': 'Electrical Engineering', 'description': '4-year program in Electrical', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 100, 'available_seats': 100, 'fees': 200000},
        {'course_name': 'B.Tech Mechanical Engineering', 'domain': 'Mechanical Engineering', 'department': 'Mechanical Engineering', 'description': '4-year program in Mechanical', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 120, 'available_seats': 120, 'fees': 200000}
    ]
    for c in courses_iitb:
        c['college_id'] = ObjectId(college1_id)
        Course.create(c)
    print(f"[OK] {len(courses_iitb)} courses created for IITB")

    courses_iitd = [
        {'course_name': 'B.Tech Computer Science', 'domain': 'Computer Science', 'department': 'Computer Science', 'description': '4-year undergraduate program in CS', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 100, 'available_seats': 100, 'fees': 200000},
        {'course_name': 'B.Tech Civil Engineering', 'domain': 'Civil Engineering', 'department': 'Civil Engineering', 'description': '4-year program in Civil', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 80, 'available_seats': 80, 'fees': 200000}
    ]
    for c in courses_iitd:
        c['college_id'] = ObjectId(college2_id)
        Course.create(c)
    print(f"[OK] {len(courses_iitd)} courses created for IITD")

    # COEP Courses
    courses_coep = [
        {'course_name': 'B.Tech Computer Science', 'domain': 'Computer Science', 'department': 'Computer Science', 'description': '4-year undergraduate program in CS', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 180, 'available_seats': 180, 'fees': 175000},
        {'course_name': 'B.Tech Information Technology', 'domain': 'Information Technology', 'department': 'IT', 'description': '4-year program in IT', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 70%', 'seats': 120, 'available_seats': 120, 'fees': 175000},
        {'course_name': 'B.Tech Electronics & Telecommunication', 'domain': 'Electronics', 'department': 'Electronics', 'description': '4-year program in E&TC', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 70%', 'seats': 120, 'available_seats': 120, 'fees': 150000},
        {'course_name': 'B.Tech Mechanical Engineering', 'domain': 'Mechanical Engineering', 'department': 'Mechanical', 'description': '4-year program in Mechanical', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 70%', 'seats': 180, 'available_seats': 180, 'fees': 150000}
    ]
    for c in courses_coep:
        c['college_id'] = ObjectId(college3_id)
        Course.create(c)
    print(f"[OK] {len(courses_coep)} courses created for COEP")

    # VIT Pune Courses
    courses_vit = [
        {'course_name': 'B.Tech Computer Science', 'domain': 'Computer Science', 'department': 'Computer Science', 'description': '4-year undergraduate program in CS', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 70%', 'seats': 240, 'available_seats': 240, 'fees': 185000},
        {'course_name': 'B.Tech Electronics Engineering', 'domain': 'Electronics', 'department': 'Electronics', 'description': '4-year program in Electronics', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 65%', 'seats': 180, 'available_seats': 180, 'fees': 165000},
        {'course_name': 'B.Tech Mechanical Engineering', 'domain': 'Mechanical Engineering', 'department': 'Mechanical', 'description': '4-year program in Mechanical', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 65%', 'seats': 180, 'available_seats': 180, 'fees': 165000}
    ]
    for c in courses_vit:
        c['college_id'] = ObjectId(college4_id)
        Course.create(c)
    print(f"[OK] {len(courses_vit)} courses created for VIT Pune")

    # PICT Courses
    courses_pict = [
        {'course_name': 'B.E. Computer Engineering', 'domain': 'Computer Science', 'department': 'Computer', 'description': '4-year undergraduate program in Computer Engineering', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 70%', 'seats': 240, 'available_seats': 240, 'fees': 175000},
        {'course_name': 'B.E. Information Technology', 'domain': 'Information Technology', 'department': 'IT', 'description': '4-year program in IT', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 65%', 'seats': 120, 'available_seats': 120, 'fees': 165000},
        {'course_name': 'B.E. Electronics & Telecommunication', 'domain': 'Electronics', 'department': 'E&TC', 'description': '4-year program in E&TC', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 60%', 'seats': 120, 'available_seats': 120, 'fees': 140000}
    ]
    for c in courses_pict:
        c['college_id'] = ObjectId(college5_id)
        Course.create(c)
    print(f"[OK] {len(courses_pict)} courses created for PICT")

    # ICT Mumbai Courses
    courses_ict = [
        {'course_name': 'B.Tech Chemical Engineering', 'domain': 'Chemical Engineering', 'department': 'Chemical', 'description': '4-year program in Chemical Engineering', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 60, 'available_seats': 60, 'fees': 120000},
        {'course_name': 'B.Tech Food Engineering', 'domain': 'Food Technology', 'department': 'Food Tech', 'description': '4-year program in Food Technology', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 70%', 'seats': 60, 'available_seats': 60, 'fees': 120000},
        {'course_name': 'B.Tech Pharmaceutical Technology', 'domain': 'Pharmacy', 'department': 'Pharmacy', 'description': '4-year program in Pharmaceutical Technology', 'duration': '4 years', 'eligibility': '10+2 with PCB/PCM minimum 70%', 'seats': 60, 'available_seats': 60, 'fees': 130000}
    ]
    for c in courses_ict:
        c['college_id'] = ObjectId(college6_id)
        Course.create(c)
    print(f"[OK] {len(courses_ict)} courses created for ICT Mumbai")

    # VJTI Courses
    courses_vjti = [
        {'course_name': 'B.Tech Computer Engineering', 'domain': 'Computer Science', 'department': 'Computer', 'description': '4-year undergraduate program in Computer Engineering', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 70%', 'seats': 120, 'available_seats': 120, 'fees': 140000},
        {'course_name': 'B.Tech Electrical Engineering', 'domain': 'Electrical Engineering', 'department': 'Electrical', 'description': '4-year program in Electrical Engineering', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 65%', 'seats': 120, 'available_seats': 120, 'fees': 135000},
        {'course_name': 'B.Tech Mechanical Engineering', 'domain': 'Mechanical Engineering', 'department': 'Mechanical', 'description': '4-year program in Mechanical Engineering', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 65%', 'seats': 120, 'available_seats': 120, 'fees': 135000}
    ]
    for c in courses_vjti:
        c['college_id'] = ObjectId(college7_id)
        Course.create(c)
    print(f"[OK] {len(courses_vjti)} courses created for VJTI")

    # DJSCE Courses
    courses_djsce = [
        {'course_name': 'B.E. Computer Engineering', 'domain': 'Computer Science', 'department': 'Computer', 'description': '4-year undergraduate program in Computer Engineering', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 70%', 'seats': 180, 'available_seats': 180, 'fees': 160000},
        {'course_name': 'B.E. Electronics & Telecommunication', 'domain': 'Electronics', 'department': 'E&TC', 'description': '4-year program in E&TC', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 65%', 'seats': 120, 'available_seats': 120, 'fees': 145000},
        {'course_name': 'B.E. Production Engineering', 'domain': 'Production', 'department': 'Production', 'description': '4-year program in Production Engineering', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 60%', 'seats': 60, 'available_seats': 60, 'fees': 120000}
    ]
    for c in courses_djsce:
        c['college_id'] = ObjectId(college8_id)
        Course.create(c)
    print(f"[OK] {len(courses_djsce)} courses created for DJSCE")

    # CEG Chennai Courses
    courses_ceg = [
        {'course_name': 'B.E. Computer Science and Engineering', 'domain': 'Computer Science', 'department': 'CSE', 'description': '4-year program in Computer Science', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 80%', 'seats': 120, 'available_seats': 120, 'fees': 50000},
        {'course_name': 'B.E. Civil Engineering', 'domain': 'Civil Engineering', 'department': 'Civil', 'description': '4-year program in Civil Engineering', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 120, 'available_seats': 120, 'fees': 50000},
        {'course_name': 'B.E. Mechanical Engineering', 'domain': 'Mechanical Engineering', 'department': 'Mechanical', 'description': '4-year program in Mechanical', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 120, 'available_seats': 120, 'fees': 50000},
        {'course_name': 'B.E. Electronics and Communication', 'domain': 'Electronics', 'department': 'ECE', 'description': '4-year program in Electronics', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 120, 'available_seats': 120, 'fees': 50000}
    ]
    for c in courses_ceg:
        c['college_id'] = ObjectId(college9_id)
        Course.create(c)
    print(f"[OK] {len(courses_ceg)} courses created for CEG Chennai")

    # PSGCT Coimbatore Courses
    courses_psgct = [
        {'course_name': 'B.E. Computer Science and Engineering', 'domain': 'Computer Science', 'department': 'CSE', 'description': '4-year program in Computer Science', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 180, 'available_seats': 180, 'fees': 150000},
        {'course_name': 'B.E. Mechanical Engineering', 'domain': 'Mechanical Engineering', 'department': 'Mechanical', 'description': '4-year program in Mechanical', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 70%', 'seats': 180, 'available_seats': 180, 'fees': 140000},
        {'course_name': 'B.E. Electronics and Communication', 'domain': 'Electronics', 'department': 'ECE', 'description': '4-year program in Electronics', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 70%', 'seats': 120, 'available_seats': 120, 'fees': 140000},
        {'course_name': 'B.E. Information Technology', 'domain': 'Information Technology', 'department': 'IT', 'description': '4-year program in IT', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 70%', 'seats': 120, 'available_seats': 120, 'fees': 140000}
    ]
    for c in courses_psgct:
        c['college_id'] = ObjectId(college10_id)
        Course.create(c)
    print(f"[OK] {len(courses_psgct)} courses created for PSGCT Coimbatore")

    # Jadavpur Engineering Courses
    courses_ju = [
        {'course_name': 'B.E. Computer Science and Engineering', 'domain': 'Computer Science', 'department': 'CSE', 'description': '4-year program in Computer Science', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 80%', 'seats': 90, 'available_seats': 90, 'fees': 10000},
        {'course_name': 'B.E. Electrical Engineering', 'domain': 'Electrical Engineering', 'department': 'EE', 'description': '4-year program in Electrical', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 90, 'available_seats': 90, 'fees': 10000},
        {'course_name': 'B.E. Mechanical Engineering', 'domain': 'Mechanical Engineering', 'department': 'Mechanical', 'description': '4-year program in Mechanical', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 75%', 'seats': 120, 'available_seats': 120, 'fees': 10000},
        {'course_name': 'B.Pharm', 'domain': 'Pharmacy', 'department': 'Pharmacy', 'description': '4-year program in Pharmacy', 'duration': '4 years', 'eligibility': '10+2 with PCB/PCM minimum 60%', 'seats': 60, 'available_seats': 60, 'fees': 10000}
    ]
    for c in courses_ju:
        c['college_id'] = ObjectId(college11_id)
        Course.create(c)
    print(f"[OK] {len(courses_ju)} courses created for Jadavpur")

    # SIT Pune Courses
    courses_sit = [
        {'course_name': 'B.Tech Computer Science', 'domain': 'Computer Science', 'department': 'CS', 'description': '4-year program in CS with AI/ML', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 70%', 'seats': 180, 'available_seats': 180, 'fees': 180000},
        {'course_name': 'B.Tech Electronics and Telecommunication', 'domain': 'Electronics', 'department': 'E&TC', 'description': '4-year program in E&TC', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 65%', 'seats': 120, 'available_seats': 120, 'fees': 160000},
        {'course_name': 'B.Tech Mechanical Engineering', 'domain': 'Mechanical Engineering', 'department': 'Mechanical', 'description': '4-year program in Mechanical', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 65%', 'seats': 120, 'available_seats': 120, 'fees': 160000}
    ]
    for c in courses_sit:
        c['college_id'] = ObjectId(college12_id)
        Course.create(c)
    print(f"[OK] {len(courses_sit)} courses created for SIT Pune")

    # MITWPU Pune Courses
    courses_mitwpu = [
        {'course_name': 'B.Tech Computer Science', 'domain': 'Computer Science', 'department': 'CS', 'description': '4-year program in Computer Science', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 60%', 'seats': 240, 'available_seats': 240, 'fees': 195000},
        {'course_name': 'B.Tech Civil Engineering', 'domain': 'Civil Engineering', 'department': 'Civil', 'description': '4-year program in Civil', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 60%', 'seats': 120, 'available_seats': 120, 'fees': 175000},
        {'course_name': 'B.Tech Electrical Engineering', 'domain': 'Electrical Engineering', 'department': 'Electrical', 'description': '4-year program in Electrical', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 60%', 'seats': 120, 'available_seats': 120, 'fees': 175000},
        {'course_name': 'BBA', 'domain': 'Business Administration', 'department': 'Management', 'description': '3-year undergraduate management program', 'duration': '3 years', 'eligibility': '10+2 minimum 50%', 'seats': 180, 'available_seats': 180, 'fees': 150000},
        {'course_name': 'MBA', 'domain': 'Business Administration', 'department': 'Management', 'description': '2-year postgraduate management program', 'duration': '2 years', 'eligibility': 'Graduation minimum 50%', 'seats': 180, 'available_seats': 180, 'fees': 250000}
    ]
    for c in courses_mitwpu:
        c['college_id'] = ObjectId(college13_id)
        Course.create(c)
    print(f"[OK] {len(courses_mitwpu)} courses created for MITWPU Pune")

    # TSEC Mumbai Courses
    courses_tsec = [
        {'course_name': 'B.E. Computer Engineering', 'domain': 'Computer Science', 'department': 'CE', 'description': '4-year program in Computer Engineering', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 65%', 'seats': 120, 'available_seats': 120, 'fees': 130000},
        {'course_name': 'B.E. Electronics and Telecommunication', 'domain': 'Electronics', 'department': 'E&TC', 'description': '4-year program in E&TC', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 60%', 'seats': 120, 'available_seats': 120, 'fees': 120000},
        {'course_name': 'B.E. Information Technology', 'domain': 'Information Technology', 'department': 'IT', 'description': '4-year program in IT', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 60%', 'seats': 120, 'available_seats': 120, 'fees': 120000}
    ]
    for c in courses_tsec:
        c['college_id'] = ObjectId(college14_id)
        Course.create(c)
    print(f"[OK] {len(courses_tsec)} courses created for TSEC Mumbai")

    # CRCE Mumbai Courses
    courses_crce = [
        {'course_name': 'B.E. Computer Engineering', 'domain': 'Computer Science', 'department': 'CE', 'description': '4-year program in Computer Engineering', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 65%', 'seats': 60, 'available_seats': 60, 'fees': 125000},
        {'course_name': 'B.E. Electronics and Telecommunication', 'domain': 'Electronics', 'department': 'E&TC', 'description': '4-year program in E&TC', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 60%', 'seats': 60, 'available_seats': 60, 'fees': 115000},
        {'course_name': 'B.E. Mechanical Engineering', 'domain': 'Mechanical Engineering', 'department': 'Mechanical', 'description': '4-year program in Mechanical', 'duration': '4 years', 'eligibility': '10+2 with PCM minimum 60%', 'seats': 60, 'available_seats': 60, 'fees': 115000}
    ]
    for c in courses_crce:
        c['college_id'] = ObjectId(college15_id)
        Course.create(c)
    print(f"[OK] {len(courses_crce)} courses created for CRCE Mumbai")

    # ============================================================
    # SEAT ALLOCATION RULES
    # ============================================================
    print("\n--- Creating Seat Allocation Rules ---")
    
    db.seat_allocations.delete_many({})
    
    for course in db.courses.find():
        total_seats = course.get('seats', 60)
        allocation = {
            'general': int(total_seats * 0.40),
            'obc': int(total_seats * 0.27),
            'sc': int(total_seats * 0.15),
            'st': int(total_seats * 0.075),
            'ews': int(total_seats * 0.10),
            'pwd': int(total_seats * 0.05),
            'nri': int(total_seats * 0.03),
            'management': int(total_seats * 0.05)
        }
        db.seat_allocations.insert_one({
            'course_id': course['_id'],
            'college_id': course['college_id'],
            'allocations': allocation,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        })
    
    print("[OK] Seat allocation rules created for all courses")

    # ============================================================
    # DEPARTMENT ADMIN
    # ============================================================
    print("\n--- Creating Department Admins ---")

    dept_admins = [
        {'name': 'IITB CS Department Admin', 'email': 'csadmin@iitb.ac.in', 'password': 'Admin@123', 'role': 'course_admin', 'college_id': ObjectId(college1_id), 'department': 'Computer Science', 'mobile': '9876543220'},
        {'name': 'IITB EE Department Admin', 'email': 'eeadmin@iitb.ac.in', 'password': 'Admin@123', 'role': 'course_admin', 'college_id': ObjectId(college1_id), 'department': 'Electrical Engineering', 'mobile': '9876543221'},
        {'name': 'IITB ME Department Admin', 'email': 'meadmin@iitb.ac.in', 'password': 'Admin@123', 'role': 'course_admin', 'college_id': ObjectId(college1_id), 'department': 'Mechanical Engineering', 'mobile': '9876543222'},
        {'name': 'IITD CS Department Admin', 'email': 'csadmin@iitd.ac.in', 'password': 'Admin@123', 'role': 'course_admin', 'college_id': ObjectId(college2_id), 'department': 'Computer Science', 'mobile': '9876543223'}
    ]
    for dept_admin in dept_admins:
        Admin.create(dept_admin)
        print(f"[OK] {dept_admin['name']} created")

    # ============================================================
    # STUDENTS
    # ============================================================
    print("\n--- Creating Students ---")

    students = [
        {'name': 'Rahul Sharma', 'email': 'rahul@example.com', 'mobile': '9876500001', 'password': 'Student@123', 'college_name': 'Delhi Public School', 'preferred_course': 'B.Tech Computer Science', 'year': '2024', 'location': 'Pune'},
        {'name': 'Priya Singh', 'email': 'priya@example.com', 'mobile': '9876500002', 'password': 'Student@123', 'college_name': 'Kendriya Vidyalaya', 'preferred_course': 'BCA Computer Applications', 'year': '2024', 'location': 'Pune'},
        {'name': 'Amit Kumar', 'email': 'amit@example.com', 'mobile': '9876500003', 'password': 'Student@123', 'college_name': "St. Xavier's School", 'preferred_course': 'B.Tech Mechanical Engineering', 'year': '2024', 'location': 'Mumbai'},
        {'name': 'Neha Gupta', 'email': 'neha@example.com', 'mobile': '9876500004', 'password': 'Student@123', 'college_name': 'Modern School', 'preferred_course': 'B.Sc Data Science', 'year': '2024', 'location': 'Chennai'},
        {'name': 'Vikram Patel', 'email': 'vikram@example.com', 'mobile': '9876500005', 'password': 'Student@123', 'college_name': 'KV School', 'preferred_course': 'MBA Business Administration', 'year': '2024', 'location': 'Pune'},
        {'name': 'Sneha Reddy', 'email': 'sneha@example.com', 'mobile': '9876500006', 'password': 'Student@123', 'college_name': 'Narayana College', 'preferred_course': 'MBBS Medical', 'year': '2024', 'location': 'Hyderabad'}
    ]
    student_ids = []
    for s in students:
        student_id = Student.create(s)
        student_ids.append(student_id)
        print(f"[OK] Student: {s['name']} ({s['email']})")

    # Give Rahul AI credits
    rahul = Student.find_by_email('rahul@example.com')
    if rahul:
        StudentCredit.create(rahul['_id'], 1000)
        AIProfile.update(rahul['_id'], {
            'interests': ['programming', 'AI', 'robotics'],
            'skills': ['Python', 'JavaScript'],
            'career_goals': 'Become a software engineer'
        })
        print("[OK] AI credits created for Rahul")

    # Give Priya AI credits
    priya = Student.find_by_email('priya@example.com')
    if priya:
        StudentCredit.create(priya['_id'], 1000)
        AIProfile.update(priya['_id'], {
            'interests': ['software development', 'web technologies'],
            'skills': ['C++', 'Java'],
            'career_goals': 'Become a software developer'
        })
        print("[OK] AI credits created for Priya")

    # Give Amit AI credits
    amit = Student.find_by_email('amit@example.com')
    if amit:
        StudentCredit.create(amit['_id'], 500)
        print("[OK] AI credits created for Amit")

    # Give Neha AI credits
    neha = Student.find_by_email('neha@example.com')
    if neha:
        StudentCredit.create(neha['_id'], 500)
        print("[OK] AI credits created for Neha")

    # Give Vikram AI credits
    vikram = Student.find_by_email('vikram@example.com')
    if vikram:
        StudentCredit.create(vikram['_id'], 500)
        print("[OK] AI credits created for Vikram")

    # Give Sneha AI credits
    sneha = Student.find_by_email('sneha@example.com')
    if sneha:
        StudentCredit.create(sneha['_id'], 500)
        print("[OK] AI credits created for Sneha")

    # ============================================================
    # APPLICATIONS
    # ============================================================
    print("\n--- Creating Applications ---")

    courses = list(db.courses.find({'college_id': ObjectId(college1_id)}))
    if student_ids and courses:
        app1_data = {
            'student_id': ObjectId(student_ids[0]),
            'college_id': ObjectId(college1_id),
            'course_id': courses[0]['_id'],
            'department': 'Computer Science',
            'status': 'applied',
            'applied_at': datetime.now(timezone.utc) - timedelta(days=random.randint(1, 10)),
            'updated_at': datetime.now(timezone.utc)
        }
        Application.create(app1_data)
        print("[OK] Application created: Rahul -> IITB CS")

        app2_data = {
            'student_id': ObjectId(student_ids[1]),
            'college_id': ObjectId(college1_id),
            'course_id': courses[0]['_id'],
            'department': 'Computer Science',
            'status': 'shortlisted',
            'applied_at': datetime.now(timezone.utc) - timedelta(days=random.randint(1, 10)),
            'updated_at': datetime.now(timezone.utc)
        }
        Application.create(app2_data)
        print("[OK] Application created: Priya -> IITB CS (shortlisted)")

    # ============================================================
    # SUPPORT TICKETS
    # ============================================================
    print("\n--- Creating Support Tickets ---")

    if student_ids and college1_id and university1_id:
        ticket1_data = {
            'user_id': ObjectId(student_ids[0]),
            'user_type': 'student',
            'user_role': 'student',
            'subject': 'Application Status Query',
            'description': 'I applied for B.Tech CS at IIT Bombay 5 days ago but have not heard back.',
            'category': 'application',
            'priority': 'medium',
            'status': 'open',
            'college_id': ObjectId(college1_id),
            'university_id': ObjectId(university1_id)
        }
        db.support_tickets.insert_one(ticket1_data)
        print("[OK] Support ticket: Rahul - Application Status")

        ticket2_data = {
            'user_id': ObjectId(student_ids[1]),
            'user_type': 'student',
            'user_role': 'student',
            'subject': 'Document Upload Issue',
            'description': "Unable to upload my 12th mark sheet. Upload keeps failing.",
            'category': 'technical',
            'priority': 'high',
            'status': 'in_progress',
            'college_id': ObjectId(college1_id),
            'university_id': ObjectId(university1_id)
        }
        db.support_tickets.insert_one(ticket2_data)
        print("[OK] Support ticket: Priya - Document Upload Issue")

    print("\n" + "="*60)
    print("SEEDING COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("\nLOGIN CREDENTIALS:")
    print("-"*60)
    print("SuperAdmin:       superadmin@example.com / Admin@123")
    print("IIT University:   university@iit-system.edu / Admin@123")
    print("NIT University:   university@nit-system.edu / Admin@123")
    print("IITB Admin:       admin@iitb.ac.in / Admin@123")
    print("IITD Admin:       admin@iitd.ac.in / Admin@123")
    print("IITB CS Dept:     csadmin@iitb.ac.in / Admin@123")
    print("Global Support:   support@platform.com / Support@123")
    print("Students:")
    print("  rahul@example.com / Student@123 (1000 credits)")
    print("  priya@example.com / Student@123 (1000 credits)")
    print("  amit@example.com / Student@123 (500 credits)")
    print("  neha@example.com / Student@123 (500 credits)")
    print("  vikram@example.com / Student@123 (500 credits)")
    print("  sneha@example.com / Student@123 (500 credits)")
    print("-"*60)
    print("\nDATABASE SUMMARY:")
    print("-"*60)
    print("Universities: 6 (IIT, NIT, SPPU, UOM, Anna Univ, Jadavpur)")
    print("Colleges: 15+ across Maharashtra, Delhi, Tamil Nadu, West Bengal")
    print("Courses: 50+ including B.Tech, B.E., B.Sc, MBA, BBA")
    print("States: Maharashtra, Delhi, Tamil Nadu, West Bengal")
    print("-"*60)
