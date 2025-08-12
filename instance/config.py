# instance/config.py

import os

class Config:
    # Secret key for Flask sessions and CSRF protection
    # IMPORTANT: In production, this should be a strong, randomly generated string
    # and loaded from an environment variable, not hardcoded.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_super_secret_key_here'

    # Database configuration (using SQLite for local development for simplicity)
    # For production, you'd use PostgreSQL:
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:password@host:port/dbname'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Disable tracking modifications for performance
    # UPLOAD_FOLDERS = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/uploads/courses')

