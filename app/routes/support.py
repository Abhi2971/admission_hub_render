# backend/app/routes/support.py
"""
Support Ticket routes for the support system.
"""
from datetime import datetime
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson.objectid import ObjectId
from app.models.support_ticket import SupportTicket
from app.models.activity_log import ActivityLog
from app.utils.validators import validate_object_id
from app.middlewares.auth_middleware import role_required


support_bp = Blueprint('support', __name__)
logger = logging.getLogger(__name__)

def convert_objectid(obj):
    if isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == '_id':
                result['id'] = str(v)
            elif isinstance(v, ObjectId):
                result[k] = str(v)
            elif isinstance(v, datetime):
                result[k] = v.isoformat()
            elif isinstance(v, list):
                result[k] = convert_objectid(v)
            elif isinstance(v, dict):
                result[k] = convert_objectid(v)
            else:
                result[k] = v
        return result
    return obj

# ============================================================
# STUDENT: Create Support Ticket
# ============================================================

@support_bp.route('/tickets', methods=['POST'])
@jwt_required()
def create_ticket():
    """Create a new support ticket (Students only)."""
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get('role')

    # Only students can create tickets via this endpoint
    if user_role != 'student':
        return jsonify({'error': 'Only students can create tickets'}), 403

    data = request.get_json()
    required = ['subject', 'description', 'category']
    if not all(k in data for k in required):
        return jsonify({'error': f'Missing required fields: {required}'}), 400

    if data.get('category') not in SupportTicket.CATEGORY_VALUES:
        return jsonify({'error': 'Invalid category'}), 400

    ticket_data = {
        'user_id': ObjectId(user_id),
        'user_type': 'student',
        'user_role': user_role,
        'subject': data['subject'],
        'description': data['description'],
        'category': data['category'],
        'priority': data.get('priority', 'medium'),
        'status': 'open'
    }

    try:
        ticket_id = SupportTicket.create(ticket_data)
        ActivityLog.log(user_id, 'student', 'create_ticket', 'ticket', {'ticket_id': str(ticket_id)})
        return jsonify({
            'message': 'Ticket created successfully',
            'ticket_id': str(ticket_id)
        }), 201
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        return jsonify({'error': 'Failed to create ticket'}), 500

@support_bp.route('/tickets', methods=['GET'])
@jwt_required()
def get_my_tickets():
    """Get tickets for the current user (student)."""
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get('role')

    if user_role != 'student':
        return jsonify({'error': 'Only students can access this endpoint'}), 403

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    try:
        result = SupportTicket.find_by_user(user_id, 'student', page, per_page)
        result['tickets'] = convert_objectid(result['tickets'])
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}")
        return jsonify({'error': 'Failed to fetch tickets'}), 500

@support_bp.route('/tickets/<ticket_id>', methods=['GET'])
@jwt_required()
def get_ticket(ticket_id):
    """Get single ticket details."""
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get('role')

    if not validate_object_id(ticket_id):
        return jsonify({'error': 'Invalid ticket ID'}), 400

    ticket = SupportTicket.find_by_id(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404

    # Students can only view their own tickets
    if user_role == 'student' and str(ticket.get('user_id')) != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    ticket = convert_objectid(ticket)
    return jsonify({'ticket': ticket}), 200

@support_bp.route('/tickets/<ticket_id>/reply', methods=['POST'])
@jwt_required()
def reply_ticket(ticket_id):
    """Add reply to ticket (Students only)."""
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get('role')

    if user_role != 'student':
        return jsonify({'error': 'Only students can reply'}), 403

    if not validate_object_id(ticket_id):
        return jsonify({'error': 'Invalid ticket ID'}), 400

    ticket = SupportTicket.find_by_id(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404

    if str(ticket.get('user_id')) != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    message = data.get('message')
    if not message:
        return jsonify({'error': 'Message is required'}), 400

    reply_data = {
        'message': message,
        'by': 'student',
        'user_id': user_id
    }

    try:
        SupportTicket.add_reply(ticket_id, reply_data)
        return jsonify({'message': 'Reply added'}), 200
    except Exception as e:
        logger.error(f"Error adding reply: {e}")
        return jsonify({'error': 'Failed to add reply'}), 500

# ============================================================
# SUPPORT: Global Support Routes
# ============================================================

@support_bp.route('/admin/tickets', methods=['GET'])
@jwt_required()
@role_required('global_support', 'local_support', 'super_admin')
def get_all_tickets():
    """Get all tickets (for support staff)."""
    claims = get_jwt()
    user_role = claims.get('role')

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    status = request.args.get('status')
    priority = request.args.get('priority')
    category = request.args.get('category')

    filters = {}
    if status:
        filters['status'] = status
    if priority:
        filters['priority'] = priority
    if category:
        filters['category'] = category

    # Global support sees all tickets
    # Local support sees only college/university tickets
    if user_role == 'local_support':
        college_id = claims.get('college_id')
        university_id = claims.get('university_id')
        
        if college_id:
            filters['college_id'] = ObjectId(college_id)
        elif university_id:
            filters['university_id'] = ObjectId(university_id)
        else:
            return jsonify({'error': 'No college or university associated'}), 400

    try:
        result = SupportTicket.find_for_support(filters, page, per_page)
        result['tickets'] = convert_objectid(result['tickets'])
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}")
        return jsonify({'error': 'Failed to fetch tickets'}), 500

@support_bp.route('/admin/tickets/<ticket_id>', methods=['GET'])
@jwt_required()
@role_required('global_support', 'local_support', 'super_admin')
def get_ticket_admin(ticket_id):
    """Get ticket details (for support staff)."""
    claims = get_jwt()
    user_role = claims.get('role')

    if not validate_object_id(ticket_id):
        return jsonify({'error': 'Invalid ticket ID'}), 400

    ticket = SupportTicket.find_by_id(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404

    # Local support can only view their scope's tickets
    if user_role == 'local_support':
        college_id = claims.get('college_id')
        university_id = claims.get('university_id')
        
        if college_id and str(ticket.get('college_id')) != college_id:
            return jsonify({'error': 'Unauthorized'}), 403
        if university_id and str(ticket.get('university_id')) != university_id:
            return jsonify({'error': 'Unauthorized'}), 403

    ticket = convert_objectid(ticket)
    return jsonify({'ticket': ticket}), 200

@support_bp.route('/admin/tickets/<ticket_id>/assign', methods=['PUT'])
@jwt_required()
@role_required('global_support', 'local_support', 'super_admin')
def assign_ticket(ticket_id):
    """Assign ticket to support staff."""
    claims = get_jwt()
    admin_id = get_jwt_identity()
    user_role = claims.get('role')

    if not validate_object_id(ticket_id):
        return jsonify({'error': 'Invalid ticket ID'}), 400

    ticket = SupportTicket.find_by_id(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404

    data = request.get_json()
    assigned_to = data.get('assigned_to')
    if not assigned_to:
        return jsonify({'error': 'assigned_to is required'}), 400

    try:
        SupportTicket.assign_ticket(ticket_id, assigned_to)
        ActivityLog.log(admin_id, user_role, 'assign_ticket', 'ticket', {
            'ticket_id': str(ticket_id),
            'assigned_to': assigned_to
        })
        return jsonify({'message': 'Ticket assigned'}), 200
    except Exception as e:
        logger.error(f"Error assigning ticket: {e}")
        return jsonify({'error': 'Failed to assign ticket'}), 500

@support_bp.route('/admin/tickets/<ticket_id>/reply', methods=['POST'])
@jwt_required()
@role_required('global_support', 'local_support', 'super_admin')
def reply_ticket_admin(ticket_id):
    """Add reply to ticket (Support staff)."""
    claims = get_jwt()
    user_role = claims.get('role')
    admin_id = get_jwt_identity()

    if not validate_object_id(ticket_id):
        return jsonify({'error': 'Invalid ticket ID'}), 400

    ticket = SupportTicket.find_by_id(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404

    data = request.get_json()
    message = data.get('message')
    if not message:
        return jsonify({'error': 'Message is required'}), 400

    reply_data = {
        'message': message,
        'by': 'support',
        'user_id': admin_id,
        'support_role': user_role
    }

    try:
        SupportTicket.add_reply(ticket_id, reply_data)
        ActivityLog.log(admin_id, user_role, 'reply_ticket', 'ticket', {'ticket_id': str(ticket_id)})
        return jsonify({'message': 'Reply added'}), 200
    except Exception as e:
        logger.error(f"Error adding reply: {e}")
        return jsonify({'error': 'Failed to add reply'}), 500

@support_bp.route('/admin/tickets/<ticket_id>/status', methods=['PUT'])
@jwt_required()
@role_required('global_support', 'local_support', 'super_admin')
def update_ticket_status(ticket_id):
    """Update ticket status."""
    claims = get_jwt()
    user_role = claims.get('role')
    admin_id = get_jwt_identity()

    if not validate_object_id(ticket_id):
        return jsonify({'error': 'Invalid ticket ID'}), 400

    data = request.get_json()
    status = data.get('status')
    if status not in SupportTicket.STATUS_VALUES:
        return jsonify({'error': 'Invalid status'}), 400

    ticket = SupportTicket.find_by_id(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404

    try:
        updates = {'status': status}
        if status == 'resolved' or status == 'closed':
            updates['resolution'] = data.get('resolution', '')
            updates['resolved_at'] = datetime.utcnow()
        
        SupportTicket.update(ticket_id, updates)
        ActivityLog.log(admin_id, user_role, 'update_ticket_status', 'ticket', {
            'ticket_id': str(ticket_id),
            'status': status
        })
        return jsonify({'message': 'Status updated'}), 200
    except Exception as e:
        logger.error(f"Error updating status: {e}")
        return jsonify({'error': 'Failed to update status'}), 500

@support_bp.route('/admin/tickets/<ticket_id>/priority', methods=['PUT'])
@jwt_required()
@role_required('global_support', 'local_support', 'super_admin')
def update_ticket_priority(ticket_id):
    """Update ticket priority."""
    claims = get_jwt()
    user_role = claims.get('role')
    admin_id = get_jwt_identity()

    if not validate_object_id(ticket_id):
        return jsonify({'error': 'Invalid ticket ID'}), 400

    data = request.get_json()
    priority = data.get('priority')
    if priority not in SupportTicket.PRIORITY_VALUES:
        return jsonify({'error': 'Invalid priority'}), 400

    try:
        SupportTicket.update(ticket_id, {'priority': priority})
        ActivityLog.log(admin_id, user_role, 'update_ticket_priority', 'ticket', {
            'ticket_id': str(ticket_id),
            'priority': priority
        })
        return jsonify({'message': 'Priority updated'}), 200
    except Exception as e:
        logger.error(f"Error updating priority: {e}")
        return jsonify({'error': 'Failed to update priority'}), 500

# ============================================================
# STATISTICS
# ============================================================

@support_bp.route('/admin/stats', methods=['GET'])
@jwt_required()
@role_required('global_support', 'local_support', 'super_admin')
def get_ticket_stats():
    """Get ticket statistics for support dashboard."""
    claims = get_jwt()
    user_role = claims.get('role')

    filters = {}
    if user_role == 'local_support':
        college_id = claims.get('college_id')
        university_id = claims.get('university_id')
        if college_id:
            filters['college_id'] = ObjectId(college_id)
        elif university_id:
            filters['university_id'] = ObjectId(university_id)

    try:
        status_counts = SupportTicket.count_by_status(filters)
        
        db = get_db()
        total = db.support_tickets.count_documents(filters) if filters else db.support_tickets.count_documents({})
        
        # Count by category
        category_pipeline = [
            {'$match': filters or {}},
            {'$group': {'_id': '$category', 'count': {'$sum': 1}}}
        ]
        category_counts = list(db.support_tickets.aggregate(category_pipeline))
        categories = {item['_id']: item['count'] for item in category_counts}

        return jsonify({
            'total': total,
            'open': status_counts.get('open', 0),
            'in_progress': status_counts.get('in_progress', 0),
            'resolved': status_counts.get('resolved', 0),
            'closed': status_counts.get('closed', 0),
            'by_category': categories
        }), 200
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

from app.database import get_db
