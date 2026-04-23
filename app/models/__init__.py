# backend/app/models/__init__.py
"""
Models package.
"""
from .student import Student
from .college import College
from .course import Course
from .application import Application
from .document import Document
from .payment import Payment
from .admin import Admin
from .notification import Notification
from .ai_profile import AIProfile
from .activity_log import ActivityLog
from .membership_plan import MembershipPlan
from .subscription import Subscription
from .student_credit import StudentCredit  # if added
from .college_plan import CollegePlan       # if added
from .college_subscription import CollegeSubscription
from .ai_usage_log import AIUsageLog

__all__ = [
    'Student', 'College', 'Course', 'Application', 'Document',
    'Payment', 'Admin', 'Notification', 'AIProfile', 'ActivityLog',
    'MembershipPlan', 'Subscription', 'StudentCredit', 'CollegePlan', 'CollegeSubscription', 'AIUsageLog'
]