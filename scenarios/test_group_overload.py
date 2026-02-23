from utils import clear_db, get_app_context, db
from app.models import Department, Faculty, Course, StudentGroup, Room, Subject

def seed_group_overload_scenario():
    clear_db()
    
    with get_app_context():
        print("Seeding GROUP OVERLOAD scenario (Failure Expected)...")
        
        # 1. Departments
        d = Department(name="Dept CS")
        db.session.add(d)
        db.session.commit()
        
        # 2. Rooms (Plenty of rooms)
        for i in range(1, 6):
            db.session.add(Room(name=f"Room {i}", capacity=100, type="lecture"))
        db.session.commit()
        
        # 3. Course & Group (1 Group)
        c = Course(name="B.Tech CS", department_id=d.id)
        db.session.add(c)
        db.session.commit()
        
        g = StudentGroup(name="Overloaded Group", course_id=c.id, size=40)
        db.session.add(g)
        db.session.commit()
        
        # 4. Faculty
        f = Faculty(name="Prof. X", department_id=d.id, max_hours_per_week=60) # Super human prof
        db.session.add(f)
        db.session.commit()
        
        # 5. Subjects (50 Hours for ONE group)
        # Max slots = 6 days * 8 slots = 48
        # We assign 5 subjects of 10 hours = 50 hours
        for i in range(5):
            s = Subject(name=f"Heavy Subject {i}", course_id=c.id, faculty_id=f.id, hours_per_week=10, is_lab=False)
            db.session.add(s)
            
        db.session.commit()
        
        print("Seeding complete!")
        print("Scenario: GROUP OVERLOAD")
        print("  - Group 'Overloaded Group' has 50 hours of classes")
        print("  - Max Validation: 48 slots/week")
        print("EXPECTED RESULT: Failure (INFEASIBLE)")
        print("EXPECTED DIAGNOSTIC: 'CRITICAL: Group 'Overloaded Group' requires 50 hours/week, but there are only 48 slots available.'")
        print("\nNow run the server (python run.py) and click 'Generate Timetable' on the dashboard.")

if __name__ == "__main__":
    seed_group_overload_scenario()
