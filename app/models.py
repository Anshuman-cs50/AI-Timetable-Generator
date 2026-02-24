from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_demo = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Nullable for initial migration
    name = db.Column(db.String(100), nullable=False)
    faculties = db.relationship('Faculty', backref='department', lazy=True)
    courses = db.relationship('Course', backref='department', lazy=True)

class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    max_hours_per_week = db.Column(db.Integer, default=20)
    subjects = db.relationship('Subject', backref='faculty', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    groups = db.relationship('StudentGroup', backref='course', lazy=True)
    subjects = db.relationship('Subject', backref='course', lazy=True)

class StudentGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(50), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    size = db.Column(db.Integer, nullable=False)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20), nullable=False)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    hours_per_week = db.Column(db.Integer, nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=True) 
    is_lab = db.Column(db.Boolean, default=False)

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    day = db.Column(db.String(20), nullable=False) 
    slot_number = db.Column(db.Integer, nullable=False) 
    start_time = db.Column(db.String(10)) 
    end_time = db.Column(db.String(10))   

class TimetableEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    slot = db.Column(db.Integer, nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False) 
    
    subject = db.relationship('Subject')
    room = db.relationship('Room')
    group = db.relationship('StudentGroup')

class SystemSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    key = db.Column(db.String(50), nullable=False)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'key', name='_user_setting_uc'),)
