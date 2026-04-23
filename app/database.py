# backend/app/database.py
"""
MongoDB connection setup.
"""
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
import logging

# Global variable for database
db = None

def init_db(app):
    """Initialize MongoDB connection."""
    global db
    try:
        client = MongoClient(app.config['MONGO_URI'])
        # Check connection
        client.admin.command('ping')
        db = client[app.config['MONGO_DB_NAME']]
        app.logger.info("MongoDB connected successfully")
        create_indexes(db)
    except ConnectionFailure as e:
        app.logger.error(f"Could not connect to MongoDB: {e}")
        raise

def get_db():
    """Return database instance."""
    if db is None:
        raise Exception("Database not initialized. Call init_db first.")
    return db

def create_indexes(db):
    """Create necessary indexes for performance and uniqueness."""
    # Students
    db.students.create_index('email', unique=True, sparse=True)
    db.students.create_index('mobile')
    db.students.create_index('google_id', unique=True, sparse=True)

    # Colleges
    db.colleges.create_index('code', unique=True)

    # Courses
    db.courses.create_index([('college_id', ASCENDING), ('course_name', ASCENDING)], unique=True)

    # Applications
    db.applications.create_index([('student_id', ASCENDING), ('college_id', ASCENDING), ('course_id', ASCENDING)], unique=True)

    # Admins
    db.admins.create_index('email', unique=True)
    db.admins.create_index([('college_id', ASCENDING), ('role', ASCENDING)])

    # Documents
    db.documents.create_index([('student_id', ASCENDING), ('application_id', ASCENDING)])

    # Payments
    db.payments.create_index('razorpay_order_id', unique=True)
    db.payments.create_index([('student_id', ASCENDING), ('application_id', ASCENDING)])

    # Notifications
    db.notifications.create_index([('user_id', ASCENDING), ('created_at', DESCENDING)])

    # Activity logs
    db.activity_logs.create_index([('user_id', ASCENDING), ('timestamp', DESCENDING)])
    db.activity_logs.create_index([('resource', ASCENDING), ('action', ASCENDING)])

    # Membership plans
    db.membership_plans.create_index('plan_name', unique=True)

    # Subscriptions
    db.subscriptions.create_index([('college_id', ASCENDING), ('status', ASCENDING)])

    # AI profiles
    db.ai_profiles.create_index('student_id', unique=True)