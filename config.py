import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///timetable.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
