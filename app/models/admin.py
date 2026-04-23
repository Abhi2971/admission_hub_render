# backend/app/models/admin.py
"""
Admin model for college admins and super admins.
"""
from datetime import datetime
from app.database import get_db
import bcrypt

class Admin:
    """Represents an admin user."""

    collection_name = 'admins'

    ROLES = [
        'super_admin',       # Platform Owner - Full system control
        'university_admin',  # University level - Manages multiple colleges
        'college_admin',      # College level - Manages college operations
        'course_admin',      # Department level - Manages specific courses
        'global_support',     # Platform-wide support
        'local_support',      # College/University level support
    ]

    @classmethod
    def create(cls, data):
        """Create a new admin."""
        db = get_db()
        data['created_at'] = datetime.utcnow()
        if 'password' in data:
            data['password_hash'] = cls._hash_password(data.pop('password'))
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_id(cls, admin_id):
        """Find admin by _id."""
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'_id': ObjectId(admin_id)})

    @classmethod
    def find_by_email(cls, email):
        """Find admin by email."""
        db = get_db()
        return db[cls.collection_name].find_one({'email': email})

    @classmethod
    def find_by_college(cls, college_id):
        """Find all admins for a college."""
        from bson.objectid import ObjectId
        db = get_db()
        return list(db[cls.collection_name].find({'college_id': ObjectId(college_id)}))

    @classmethod
    def update(cls, admin_id, updates):
        """Update admin details."""
        from bson.objectid import ObjectId
        db = get_db()
        if 'password' in updates:
            updates['password_hash'] = cls._hash_password(updates.pop('password'))
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(admin_id)},
            {'$set': updates}
        )
        return result.modified_count > 0

    @classmethod
    def verify_password(cls, admin, password):
        """Verify password against hash."""
        if 'password_hash' not in admin:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), admin['password_hash'])

    @staticmethod
    def _hash_password(password):
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)