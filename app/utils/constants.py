# Application status constants
APPLICATION_STATUS = ['applied', 'shortlisted', 'rejected', 'offered', 'confirmed']

# Admin roles - complete RBAC hierarchy
ADMIN_ROLES = [
    'super_admin',       # Platform Owner - Full system control
    'university_admin',  # University level - Manages multiple colleges
    'college_admin',      # College level - Manages college operations
    'course_admin',      # Department level - Manages specific courses
    'global_support',     # Platform-wide support
    'local_support',      # College/University level support
]

# Role hierarchy for access control
ROLE_HIERARCHY = {
    'super_admin': 6,       # Highest
    'university_admin': 5,
    'college_admin': 4,
    'course_admin': 3,
    'local_support': 2,
    'global_support': 2,    # Same level as local_support
    'student': 1,
}

# Document types
DOCUMENT_TYPES = ['mark_sheet', 'id_proof', 'photo', 'signature', 'other']

# Payment status
PAYMENT_STATUS = ['created', 'success', 'failed']

# Subscription status
SUBSCRIPTION_STATUS = ['active', 'expired', 'cancelled', 'pending']