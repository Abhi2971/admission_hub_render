# backend/app/routes/documents.py
"""
Document upload and management.
"""
import logging
import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from app.models.document import Document
from app.models.application import Application
from app.services.cloudinary_service import upload_file, delete_file
from app.utils.validators import validate_object_id, allowed_file
from app.models.activity_log import ActivityLog

documents_bp = Blueprint('documents', __name__)
logger = logging.getLogger(__name__)

@documents_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_document():
    """Upload a document for an application."""
    student_id = get_jwt_identity()

    # Check if file is present
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Get application_id from form
    application_id = request.form.get('application_id')
    document_type = request.form.get('document_type', 'other')

    if not application_id:
        return jsonify({'error': 'application_id required'}), 400
    if not validate_object_id(application_id):
        return jsonify({'error': 'Invalid application ID'}), 400

    # Verify application belongs to student
    app = Application.find_by_id(application_id)
    if not app or str(app['student_id']) != student_id:
        return jsonify({'error': 'Invalid application'}), 403

    # Validate file
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Allowed: pdf, jpg, jpeg, png, doc, docx'}), 400

    # Secure filename and upload to Cloudinary
    filename = secure_filename(file.filename)
    try:
        upload_result = upload_file(file, folder='admission_documents')
        file_url = upload_result['secure_url']
        public_id = upload_result['public_id']
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        return jsonify({'error': 'File upload failed'}), 500

    # Create document record
    doc_data = {
        'student_id': ObjectId(student_id),
        'application_id': ObjectId(application_id),
        'document_type': document_type,
        'file_url': file_url,
        'cloudinary_public_id': public_id,
        'verification_status': 'pending'
    }
    try:
        doc_id = Document.create(doc_data)
        ActivityLog.log(student_id, 'student', 'upload_document', 'document', {'document_id': str(doc_id), 'application_id': application_id})
        return jsonify({'message': 'Document uploaded', 'document_id': str(doc_id), 'file_url': file_url}), 201
    except Exception as e:
        logger.error(f"Document record creation failed: {e}")
        # Attempt to delete from Cloudinary
        delete_file(public_id)
        return jsonify({'error': 'Failed to save document record'}), 500

@documents_bp.route('/<application_id>', methods=['GET'])
@jwt_required()
def get_documents(application_id):
    """Get all documents for an application."""
    student_id = get_jwt_identity()
    if not validate_object_id(application_id):
        return jsonify({'error': 'Invalid application ID'}), 400

    # Verify application belongs to student or admin (admin handled separately)
    app = Application.find_by_id(application_id)
    if not app or str(app['student_id']) != student_id:
        # For admin, we'll have separate route
        return jsonify({'error': 'Access denied'}), 403

    docs = Document.find_by_application(application_id)
    for doc in docs:
        doc['_id'] = str(doc['_id'])
        doc['student_id'] = str(doc['student_id'])
        doc['application_id'] = str(doc['application_id'])

    return jsonify(docs), 200


@documents_bp.route('/upload-profile', methods=['POST'])
@jwt_required()
def upload_profile_document():
    """Upload a document to student profile (reusable for all applications)."""
    student_id = get_jwt_identity()

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    document_type = request.form.get('document_type', 'other')

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Allowed: pdf, jpg, jpeg, png'}), 400

    # Check if document of this type already exists
    existing = Document.find_by_type(student_id, document_type)
    if existing:
        # Delete old document
        if existing.get('cloudinary_public_id'):
            try:
                delete_file(existing['cloudinary_public_id'])
            except:
                pass
        Document.delete(str(existing['_id']))

    # Upload to Cloudinary
    filename = secure_filename(file.filename)
    try:
        upload_result = upload_file(file, folder='profile_documents')
        file_url = upload_result['secure_url']
        public_id = upload_result['public_id']
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        return jsonify({'error': 'File upload failed'}), 500

    # Create document record
    doc_data = {
        'student_id': ObjectId(student_id),
        'application_id': None,
        'document_type': document_type,
        'file_url': file_url,
        'cloudinary_public_id': public_id,
        'verification_status': 'pending',
        'is_profile_document': True
    }
    try:
        doc_id = Document.create(doc_data)
        ActivityLog.log(student_id, 'student', 'upload_profile_document', 'document', {'document_id': str(doc_id), 'type': document_type})
        return jsonify({'message': 'Document uploaded', 'document_id': str(doc_id), 'file_url': file_url}), 201
    except Exception as e:
        logger.error(f"Document record creation failed: {e}")
        if public_id:
            try:
                delete_file(public_id)
            except:
                pass
        return jsonify({'error': 'Failed to save document record'}), 500


@documents_bp.route('/my-documents', methods=['GET'])
@jwt_required()
def get_my_documents():
    """Get all profile documents for current student."""
    student_id = get_jwt_identity()
    docs = Document.find_by_student(student_id)
    
    result = []
    for doc in docs:
        doc['_id'] = str(doc['_id'])
        doc['student_id'] = str(doc['student_id'])
        if doc.get('application_id'):
            doc['application_id'] = str(doc['application_id'])
        result.append(doc)
    
    return jsonify({'documents': result}), 200


@documents_bp.route('/<document_id>', methods=['DELETE'])
@jwt_required()
def delete_document_by_id(document_id):
    """Delete a document by ID."""
    student_id = get_jwt_identity()
    if not validate_object_id(document_id):
        return jsonify({'error': 'Invalid document ID'}), 400

    doc = Document.find_by_id(document_id)
    if not doc:
        return jsonify({'error': 'Document not found'}), 404

    if str(doc['student_id']) != student_id:
        return jsonify({'error': 'Access denied'}), 403

    public_id = doc.get('cloudinary_public_id')
    if public_id:
        try:
            delete_file(public_id)
        except Exception as e:
            logger.error(f"Failed to delete from Cloudinary: {e}")

    deleted = Document.delete(document_id)
    if deleted:
        ActivityLog.log(student_id, 'student', 'delete_document', 'document', {'document_id': document_id})
        return jsonify({'message': 'Document deleted'}), 200
    else:
        return jsonify({'error': 'Deletion failed'}), 500