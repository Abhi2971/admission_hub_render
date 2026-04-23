from datetime import datetime
from flask_socketio import emit, join_room, leave_room
from app.models.notification import Notification
from app import socketio

def send_notification(user_id, user_type, title, message, data=None):
    """Create and emit a real-time notification."""
    from bson.objectid import ObjectId
    notif_id = Notification.create({
        'user_id': ObjectId(user_id),
        'user_type': user_type,
        'title': title,
        'message': message,
        'data': data or {}
    })
    room = f"{user_type}_{user_id}"
    socketio.emit('notification', {
        '_id': str(notif_id),
        'title': title,
        'message': message,
        'data': data,
        'created_at': datetime.utcnow().isoformat()
    }, room=room)
    return notif_id

def notify_application_status_change(application, old_status, new_status):
    from app.models.student import Student
    from app.models.admin import Admin
    student = Student.find_by_id(application['student_id'])
    if student:
        send_notification(
            user_id=student['_id'],
            user_type='student',
            title='Application Status Updated',
            message=f'Your application for {application.get("course_name")} is now {new_status}.',
            data={'application_id': str(application['_id']), 'status': new_status}
        )
    admins = Admin.find_by_college(application['college_id'])
    for admin in admins:
        send_notification(
            user_id=admin['_id'],
            user_type='admin',
            title='Application Status Changed',
            message=f'Application {application["_id"]} changed to {new_status}.',
            data={'application_id': str(application['_id']), 'status': new_status}
        )