# backend/app/services/auth_service.py
"""
Authentication helper functions.
"""
import bcrypt
from flask_jwt_extended import create_access_token, create_refresh_token

class AuthService:
    @staticmethod
    def hash_password(password):
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)

    @staticmethod
    def check_password(password_hash, password):
        return bcrypt.checkpw(password.encode('utf-8'), password_hash)

    @staticmethod
    def generate_tokens(user_id, role, additional_claims=None):
        claims = {'role': role}
        if additional_claims:
            claims.update(additional_claims)
        access_token = create_access_token(identity=user_id, additional_claims=claims)
        refresh_token = create_refresh_token(identity=user_id)
        return access_token, refresh_token