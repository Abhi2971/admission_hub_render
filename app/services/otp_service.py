import random
import time
from collections import defaultdict

# Simple in-memory store with expiry (for production use Redis)
otp_store = {}  # key: identifier (email/mobile), value: {'otp': '123456', 'expiry': timestamp}
rate_limit_store = defaultdict(list)  # identifier -> list of timestamps

# Temporary storage for user signup data (key: email)
user_temp_store = {}
temp_store = user_temp_store  # alias for backward compatibility

class OTPService:
    @staticmethod
    def generate_otp(identifier, length=6, expiry_minutes=10):
        """Generate OTP and store with expiry."""
        # Rate limit check
        now = time.time()
        rate_limit_store[identifier] = [t for t in rate_limit_store[identifier] if t > now - 3600]  # keep last hour
        if len(rate_limit_store[identifier]) >= 3:
            raise Exception("Rate limit exceeded. Try later.")

        otp = ''.join([str(random.randint(0, 9)) for _ in range(length)])
        expiry = now + (expiry_minutes * 60)
        otp_store[identifier] = {'otp': otp, 'expiry': expiry}
        rate_limit_store[identifier].append(now)
        return otp

    @staticmethod
    def verify_otp(identifier, otp):
        """Verify OTP and remove if valid."""
        entry = otp_store.get(identifier)
        if not entry:
            return False
        if time.time() > entry['expiry']:
            del otp_store[identifier]
            return False
        if entry['otp'] == otp:
            del otp_store[identifier]
            return True
        return False