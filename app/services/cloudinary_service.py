# backend/app/services/cloudinary_service.py
"""
Cloudinary file upload and delete.
"""
import cloudinary
import cloudinary.uploader
from flask import current_app

def init_cloudinary():
    cloudinary.config(
        cloud_name=current_app.config['CLOUDINARY_CLOUD_NAME'],
        api_key=current_app.config['CLOUDINARY_API_KEY'],
        api_secret=current_app.config['CLOUDINARY_API_SECRET']
    )

def upload_file(file, folder='admission_documents'):
    """Upload file to Cloudinary."""
    init_cloudinary()
    result = cloudinary.uploader.upload(file, folder=folder)
    return result

def delete_file(public_id):
    """Delete file from Cloudinary."""
    init_cloudinary()
    result = cloudinary.uploader.destroy(public_id)
    return result