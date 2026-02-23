import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_health():
    try:
        response = requests.get(BASE_URL + "/")
        print(f"Health Check: {response.status_code}")
        if response.status_code == 200:
            print("Server is responding.")
            return True
        else:
            print("Server returned unexpected status.")
            return False
    except requests.exceptions.ConnectionError:
        print("Failed to connect to server. Is it running?")
        return False

def test_generation():
    print("\n--- Triggering Timetable Generation ---")
    try:
        response = requests.post(BASE_URL + "/generate-timetable")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200 and response.json().get("status") == "Success":
            print("Generation Successful.")
            return True
        else:
            print("Generation Failed.")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def verify_constraints():
    print("\n--- Verifying Schedule Results ---")
    response = requests.get(BASE_URL + "/view/all")
    if response.status_code != 200:
        print("Failed to fetch timetable.")
        return

    timetable = response.json()
    
    # 1. Check for Conflicts (Simple client-side check)
    # A room cannot have 2 classes at same slot
    # A faculty cannot have 2 classes at same slot
    # A group cannot have 2 classes at same slot
    
    room_schedule = {}
    faculty_schedule = {}
    group_schedule = {}
    
    violation_count = 0
    
    for day, entries in timetable.items():
        for entry in entries:
            slot = entry['slot']
            
            # Key = (Day, Slot, Entity)
            r_key = (day, slot, entry['room'])
            f_key = (day, slot, entry['faculty'])
            g_key = (day, slot, entry['group'])
            
            if r_key in room_schedule:
                print(f"VIOLATION: Room {entry['room']} conflict on {day} slot {slot}")
                violation_count += 1
            room_schedule[r_key] = entry
            
            if f_key in faculty_schedule:
                print(f"VIOLATION: Faculty {entry['faculty']} conflict on {day} slot {slot}")
                violation_count += 1
            faculty_schedule[f_key] = entry
            
            if g_key in group_schedule:
                print(f"VIOLATION: Group {entry['group']} conflict on {day} slot {slot}")
                violation_count += 1
            group_schedule[g_key] = entry

    if violation_count == 0:
        print("No hard constraint violations found in the output!")
    else:
        print(f"Found {violation_count} violations.")

if __name__ == "__main__":
    if test_health():
        if test_generation():
            verify_constraints()
