import os

class Config:
    # Use DATABASE_URL for Supabase/Heroku/Vercel, fallback to SQLite locally
    uri = os.environ.get('DATABASE_URL') or 'sqlite:///timetable.db'
    
    if uri.startswith("https://"):
        raise ValueError("DATABASE_URL must be a postgresql connection string, not an HTTPS API URL. Please check your Supabase Database settings.")

    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
