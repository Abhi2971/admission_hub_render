"""
Register all blueprints.
"""
from flask import Blueprint
from .auth import auth_bp
from .students import students_bp
from .courses import courses_bp
from .colleges import colleges_bp
from .applications import applications_bp
from .documents import documents_bp
from .payments import payments_bp
from .admin import admin_bp
from .superadmin import superadmin_bp
from .university_admin import university_admin_bp
from .course_admin import course_admin_bp
from .membership import membership_bp
from .ai import ai_bp
from .ai_agent import ai_agent_bp
from .notifications import notifications_bp
from .student_credits import credits_bp
from .college_subscription import subscription_bp
from .superadmin_plans import superadmin_plans_bp
from .support import support_bp
from .plan import plan_bp
from .check_access import check_access_bp
from .universities import universities_bp



def register_blueprints(app):
    """Register all blueprints with the app."""
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(students_bp, url_prefix='/api/students')
    app.register_blueprint(courses_bp, url_prefix='/api/courses')
    app.register_blueprint(colleges_bp, url_prefix='/api/colleges')
    app.register_blueprint(universities_bp, url_prefix='/api/universities')
    app.register_blueprint(applications_bp, url_prefix='/api/applications')
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(superadmin_bp, url_prefix='/api/superadmin')
    app.register_blueprint(university_admin_bp, url_prefix='/api/university-admin')
    app.register_blueprint(course_admin_bp, url_prefix='/api/course-admin')
    app.register_blueprint(membership_bp, url_prefix='/api/membership')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(ai_agent_bp, url_prefix='/api/ai-agent')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(credits_bp, url_prefix='/api/credits')
    app.register_blueprint(subscription_bp, url_prefix='/api/subscription')
    app.register_blueprint(superadmin_plans_bp, url_prefix='/api/superadmin/plans')
    app.register_blueprint(support_bp, url_prefix='/api/support')
    app.register_blueprint(plan_bp, url_prefix='/api/plans')
    app.register_blueprint(check_access_bp)