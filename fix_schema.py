import sqlite3

def update_schema():
    conn = sqlite3.connect('instance/timetable.db')
    cursor = conn.cursor()
    
    tables = [
        'department', 'room', 'time_slot', 'faculty', 'course', 
        'student_group', 'subject', 'timetable_entry', 'system_setting'
    ]
    
    for table in tables:
        try:
            print(f"Adding user_id to {table}...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES user(id)")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column already exists in {table}")
            else:
                print(f"Error updating {table}: {e}")
                
    conn.commit()
    conn.close()
    print("Schema update attempt finished.")

if __name__ == "__main__":
    update_schema()
