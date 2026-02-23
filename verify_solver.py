import sys
import os

from app import create_app
from app.models import db, Subject, StudentGroup, Room, Faculty
from app.solver import solve_timetable
from ortools.sat.python import cp_model

def run_verification():
    app = create_app()
    with app.app_context():
        print("Fetching data...")
        subjects = Subject.query.all()
        groups = StudentGroup.query.all()
        rooms = Room.query.all()
        faculties = Faculty.query.all()
        
        if not subjects:
            print("No subjects found. Seed data might not have run.")
            return

        print(f"Found {len(subjects)} subjects, {len(groups)} groups, {len(rooms)} rooms.")

        print("Running solver...")
        status, results = solve_timetable(subjects, groups, rooms, faculties, [])
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print("Solver Success!")
            print(f"Generated {len(results)} entries.")
            # Verify constraints roughly
            schedule = {}
            for r in results:
                k = (r['room'], r['day'], r['slot'])
                if k in schedule:
                    print(f"CONFLICT: Room {r['room']} double booked on {r['day']} slot {r['slot']}")
                schedule[k] = r
            print("Sample schedule:")
            for r in results[:5]:
                print(r)
        else:
            print("Solver Failed to find a solution.")

if __name__ == "__main__":
    run_verification()
