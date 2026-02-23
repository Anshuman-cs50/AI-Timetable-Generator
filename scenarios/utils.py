import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Department, Faculty, Course, StudentGroup, Room, Subject, TimetableEntry

app = create_app()

def clear_db():
    """Clears all data from the database."""
    with app.app_context():
        print("Clearing database...")
        db.session.query(TimetableEntry).delete()
        db.session.query(Subject).delete()
        db.session.query(StudentGroup).delete()
        db.session.query(Course).delete()
        db.session.query(Faculty).delete()
        db.session.query(Room).delete()
        db.session.query(Department).delete()
        db.session.commit()
        print("Database cleared.")

def get_app_context():
    return app.app_context()
