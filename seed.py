from app import create_app, db
from app.models import Department, Faculty, Course, StudentGroup, Room, Subject

app = create_app()

def seed_data():
    with app.app_context():
        db.create_all()
        
        if Department.query.first():
            print("Data already exists.")
            return

        print("Seeding data...")
        cs = Department(name="Computer Science")
        ee = Department(name="Electrical Engineering")
        db.session.add_all([cs, ee])
        db.session.commit()

        f1 = Faculty(name="Dr. Alice", department_id=cs.id, max_hours_per_week=15)
        f2 = Faculty(name="Prof. Bob", department_id=cs.id, max_hours_per_week=15)
        f3 = Faculty(name="Dr. Charlie", department_id=ee.id, max_hours_per_week=20) 
        db.session.add_all([f1, f2, f3])
        db.session.commit()

        c1 = Course(name="B.Tech CS", department_id=cs.id)
        c2 = Course(name="B.Tech EE", department_id=ee.id)
        db.session.add_all([c1, c2])
        db.session.commit()

        g1 = StudentGroup(name="CS-A", course_id=c1.id, size=40)
        g2 = StudentGroup(name="CS-B", course_id=c1.id, size=40)
        g3 = StudentGroup(name="EE-A", course_id=c2.id, size=30)
        db.session.add_all([g1, g2, g3])
        db.session.commit()

        r1 = Room(name="Hall 101", capacity=50, type="lecture")
        r2 = Room(name="Hall 102", capacity=50, type="lecture")
        r3 = Room(name="Lab A", capacity=30, type="lab") 
        r4 = Room(name="Lab B", capacity=60, type="lab") 
        db.session.add_all([r1, r2, r3, r4])
        db.session.commit()

        s1 = Subject(name="Data Structures", course_id=c1.id, hours_per_week=4, faculty_id=f1.id, is_lab=False)
        s2 = Subject(name="Algorithms", course_id=c1.id, hours_per_week=3, faculty_id=f2.id, is_lab=False)
        s3 = Subject(name="CS Lab", course_id=c1.id, hours_per_week=2, faculty_id=f1.id, is_lab=True)
        s4 = Subject(name="Circuits", course_id=c2.id, hours_per_week=4, faculty_id=f3.id, is_lab=False)
        s5 = Subject(name="EE Lab", course_id=c2.id, hours_per_week=2, faculty_id=f3.id, is_lab=True)
        db.session.add_all([s1, s2, s3, s4, s5])
        db.session.commit()
        
        print("Seeding complete!")

if __name__ == "__main__":
    seed_data()
