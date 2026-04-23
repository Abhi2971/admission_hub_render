import uuid
from datetime import datetime

def generate_unique_code(prefix=''):
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"

def format_datetime(dt):
    return dt.isoformat() if dt else None

def safe_objectid(id_str):
    from bson.objectid import ObjectId
    try:
        return ObjectId(id_str)
    except:
        return None