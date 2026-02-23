from utils import clear_db, get_app_context, db
from app.models import Department, Faculty, Course, StudentGroup, Room, Subject

def seed_balanced_scenario():
    clear_db()
    
    with get_app_context():
        print("Seeding BALANCED scenario (Success Expected)...")
        
        # 1. Departments
        depts = [Department(name=f"Dept {i}") for i in range(1, 6)]
        db.session.add_all(depts)
        db.session.commit()
        
        # 2. Rooms (10 Rooms: 8 Lecture, 2 Lab)
        # Capacity: 10 * 48 = 480 slots
        rooms = []
        for i in range(1, 9):
            rooms.append(Room(name=f"Lecture Hall {i}", capacity=60, type="lecture"))
        for i in range(1, 3):
            rooms.append(Room(name=f"Lab {i}", capacity=40, type="lab"))
        db.session.add_all(rooms)
        db.session.commit()
        
        # 3. Courses & Groups (10 Groups)
        courses = []
        groups = []
        for i in range(1, 11):
            c = Course(name=f"Course {i}", department_id=depts[(i-1)%5].id)
            courses.append(c)
            db.session.add(c)
            db.session.commit() # Need ID
            
            g = StudentGroup(name=f"Group {i}", course_id=c.id, size=30)
            groups.append(g)
        
        db.session.add_all(groups)
        db.session.commit()
        
        # 4. Faculty (20 Faculty)
        faculties = []
        for i in range(1, 21):
            # Max 20 hours per week
            f = Faculty(name=f"Prof {i}", department_id=depts[(i-1)%5].id, max_hours_per_week=20)
            faculties.append(f)
        db.session.add_all(faculties)
        db.session.commit()
        
        # 5. Subjects (Load: ~30 hours/group * 10 groups = 300 hours)
        # Each group gets 5 subjects of 4 hours (20) + 1 lab of 4 hours (4) = 24 hours total, well within limits
        subjects = []
        for i, group in enumerate(groups):
            # Assign 5 lecture subjects
            for j in range(5):
                f_idx = (i * 5 + j) % 20
                s = Subject(name=f"Sub {i}-{j}", course_id=group.course_id, faculty_id=faculties[f_idx].id, hours_per_week=4, is_lab=False)
                subjects.append(s)
            
            # Assign 1 lab subject
            f_idx = (i * 5 + 5) % 20
            s_lab = Subject(name=f"Lab {i}", course_id=group.course_id, faculty_id=faculties[f_idx].id, hours_per_week=4, is_lab=True)
            subjects.append(s_lab)
            
        db.session.add_all(subjects)
        db.session.commit()
        
        print("Seeding complete!")
        print("Scenario: BALANCED")
        print("  - 10 Groups, 20 Faculty, 10 Rooms")
        print("  - Total Load: ~240 hours")
        print("  - Total Capacity: 480 slots")
        print("EXPECTED RESULT: Success (OPTIMAL or FEASIBLE)")
        print("\nNow run the server (python run.py) and click 'Generate Timetable' on the dashboard.")

if __name__ == "__main__":
    seed_balanced_scenario()
