import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.notification import Notification
from app.services.notification_service import send_notification
from app.middlewares.auth_middleware import role_required
from flask_socketio import emit, join_room, leave_room
from app import socketio

notifications_bp = Blueprint('notifications', __name__)
logger = logging.getLogger(__name__)

@socketio.on('connect')
def handle_connect(auth=None):
    print('Client connected')
    logger.info("Socket client connected")

@socketio.on('authenticate')
def handle_authenticate(data):
    from flask_jwt_extended import decode_token
    try:
        token = data['token']
        decoded = decode_token(token)
        user_id = decoded['sub']
        role = decoded['role']
        join_room(f"{role}_{user_id}")
        emit('authenticated', {'status': 'success'})
    except Exception as e:
        emit('authenticated', {'status': 'error', 'message': str(e)})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@notifications_bp.route('/', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = get_jwt_identity()
    user_type = request.args.get('user_type', 'student')
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = int(request.args.get('limit', 50))
    notifs = Notification.find_by_user(user_id, user_type, unread_only, limit)
    for n in notifs:
        n['_id'] = str(n['_id'])
        n['user_id'] = str(n['user_id'])
    return jsonify(notifs), 200

@notifications_bp.route('/<notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_read(notification_id):
    marked = Notification.mark_as_read(notification_id)
    if marked:
        return jsonify({'message': 'Marked as read'}), 200
    return jsonify({'error': 'Notification not found'}), 404

@notifications_bp.route('/read-all', methods=['PUT'])
@jwt_required()
def mark_all_read():
    user_id = get_jwt_identity()
    user_type = request.json.get('user_type', 'student')
    count = Notification.mark_all_read(user_id, user_type)
    return jsonify({'message': f'{count} notifications marked as read'}), 200