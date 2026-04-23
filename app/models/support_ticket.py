# backend/app/models/support_ticket.py
"""
Support Ticket model for the support system.
"""
from datetime import datetime
from app.database import get_db

class SupportTicket:
    """Represents a support ticket."""

    collection_name = 'support_tickets'

    STATUS_VALUES = ['open', 'in_progress', 'resolved', 'closed']
    PRIORITY_VALUES = ['low', 'medium', 'high', 'urgent']
    CATEGORY_VALUES = ['admission', 'payment', 'document', 'technical', 'other', 'general']
    USER_TYPES = ['student', 'admin']

    @classmethod
    def create(cls, data):
        """Create a new support ticket."""
        db = get_db()
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = data['created_at']
        data['status'] = data.get('status', 'open')
        data['priority'] = data.get('priority', 'medium')
        data['replies'] = []
        
        # Generate ticket ID
        count = db[cls.collection_name].count_documents({})
        data['ticket_id'] = f"TKT-{datetime.utcnow().strftime('%Y%m%d')}-{str(count + 1).zfill(4)}"
        
        result = db[cls.collection_name].insert_one(data)
        return result.inserted_id

    @classmethod
    def find_by_id(cls, ticket_id):
        """Find ticket by _id."""
        from bson.objectid import ObjectId
        db = get_db()
        return db[cls.collection_name].find_one({'_id': ObjectId(ticket_id)})

    @classmethod
    def find_by_ticket_id(cls, ticket_id):
        """Find ticket by ticket_id string."""
        db = get_db()
        return db[cls.collection_name].find_one({'ticket_id': ticket_id})

    @classmethod
    def find_by_user(cls, user_id, user_type, page=1, per_page=20):
        """Find tickets for a user."""
        from bson.objectid import ObjectId
        db = get_db()
        skip = (page - 1) * per_page
        query = {'user_id': ObjectId(user_id), 'user_type': user_type}
        tickets = list(db[cls.collection_name].find(query).skip(skip).limit(per_page).sort('created_at', -1))
        total = db[cls.collection_name].count_documents(query)
        return {'tickets': tickets, 'total': total, 'page': page, 'per_page': per_page}

    @classmethod
    def find_for_support(cls, filters=None, page=1, per_page=20):
        """Find tickets for support team with filters."""
        db = get_db()
        skip = (page - 1) * per_page
        query = filters or {}
        
        tickets = list(db[cls.collection_name].find(query).skip(skip).limit(per_page).sort('created_at', -1))
        total = db[cls.collection_name].count_documents(query)
        return {'tickets': tickets, 'total': total, 'page': page, 'per_page': per_page}

    @classmethod
    def find_by_college(cls, college_id, page=1, per_page=20):
        """Find tickets for a college."""
        from bson.objectid import ObjectId
        db = get_db()
        skip = (page - 1) * per_page
        query = {'college_id': ObjectId(college_id)}
        tickets = list(db[cls.collection_name].find(query).skip(skip).limit(per_page).sort('created_at', -1))
        total = db[cls.collection_name].count_documents(query)
        return {'tickets': tickets, 'total': total, 'page': page, 'per_page': per_page}

    @classmethod
    def find_by_university(cls, university_id, page=1, per_page=20):
        """Find tickets for a university."""
        from bson.objectid import ObjectId
        db = get_db()
        skip = (page - 1) * per_page
        query = {'university_id': ObjectId(university_id)}
        tickets = list(db[cls.collection_name].find(query).skip(skip).limit(per_page).sort('created_at', -1))
        total = db[cls.collection_name].count_documents(query)
        return {'tickets': tickets, 'total': total, 'page': page, 'per_page': per_page}

    @classmethod
    def update(cls, ticket_id, updates):
        """Update ticket details."""
        from bson.objectid import ObjectId
        db = get_db()
        updates['updated_at'] = datetime.utcnow()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(ticket_id)},
            {'$set': updates}
        )
        return result.modified_count > 0

    @classmethod
    def add_reply(cls, ticket_id, reply_data):
        """Add a reply to ticket."""
        from bson.objectid import ObjectId
        db = get_db()
        reply_data['created_at'] = datetime.utcnow()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(ticket_id)},
            {
                '$push': {'replies': reply_data},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        return result.modified_count > 0

    @classmethod
    def assign_ticket(cls, ticket_id, assigned_to):
        """Assign ticket to support staff."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(ticket_id)},
            {
                '$set': {
                    'assigned_to': ObjectId(assigned_to),
                    'assigned_at': datetime.utcnow(),
                    'status': 'in_progress',
                    'updated_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0

    @classmethod
    def resolve(cls, ticket_id, resolution):
        """Resolve a ticket."""
        from bson.objectid import ObjectId
        db = get_db()
        result = db[cls.collection_name].update_one(
            {'_id': ObjectId(ticket_id)},
            {
                '$set': {
                    'status': 'resolved',
                    'resolution': resolution,
                    'resolved_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0

    @classmethod
    def count_by_status(cls, filters=None):
        """Count tickets by status."""
        db = get_db()
        query = filters or {}
        pipeline = [
            {'$match': query},
            {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
        ]
        result = list(db[cls.collection_name].aggregate(pipeline))
        return {item['_id']: item['count'] for item in result}
