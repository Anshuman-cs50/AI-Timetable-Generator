from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
import csv
import io
from app import db
from app.models import (Department, Faculty, Course, StudentGroup, 
                        Room, Subject, TimetableEntry, SystemSetting, TimeSlot)
from app.solver import solve_timetable, analyze_constraints
from ortools.sat.python import cp_model
from flask_login import login_required, current_user

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('landing.html')
        
    _seed_default_settings()
    _seed_time_slots()
    if current_user.username == 'demo_institution':
        _seed_demo_data()

    # Fetch stats for the logged-in user
    stats = { 
        'faculty': Faculty.query.filter_by(user_id=current_user.id).count(),
        'courses': Course.query.filter_by(user_id=current_user.id).count(),
        'rooms': Room.query.filter_by(user_id=current_user.id).count(),
        'subjects': Subject.query.filter_by(user_id=current_user.id).count()
    }
    settings = SystemSetting.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', stats=stats, settings=settings)
    

@main.route('/manage')
@login_required
def manage():
    _seed_default_settings()
    data = {
        'departments': Department.query.filter_by(user_id=current_user.id).all(),
        'courses': Course.query.filter_by(user_id=current_user.id).all(),
        'groups': StudentGroup.query.filter_by(user_id=current_user.id).all(),
        'faculty': Faculty.query.filter_by(user_id=current_user.id).all(),
        'rooms': Room.query.filter_by(user_id=current_user.id).all(),
        'subjects': Subject.query.filter_by(user_id=current_user.id).all()
    }
    settings = SystemSetting.query.filter_by(user_id=current_user.id).all()
    return render_template('manage.html', data=data, settings=settings)

@main.route('/api/department/add', methods=['POST'])
@login_required
def add_department():
    name = request.form.get('name')
    d = Department(name=name, user_id=current_user.id)
    db.session.add(d)
    db.session.commit()
    return jsonify({"status": "success", "item": {"id": d.id, "name": d.name}})

@main.route('/api/department/delete/<int:id>', methods=['POST'])
@login_required
def delete_department(id):
    d = Department.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    # Check for dependencies
    if Faculty.query.filter_by(department_id=id).first() or Course.query.filter_by(department_id=id).first():
        return jsonify({"status": "error", "message": "Department has associated faculty or courses"}), 400
    db.session.delete(d)
    db.session.commit()
    return jsonify({"status": "success"})

@main.route('/api/course/add', methods=['POST'])
@login_required
def add_course():
    name = request.form.get('name')
    dept_id = request.form.get('department_id')
    c = Course(name=name, department_id=dept_id, user_id=current_user.id)
    db.session.add(c)
    db.session.commit()
    return jsonify({"status": "success", "item": {"id": c.id, "name": c.name}})

@main.route('/api/course/delete/<int:id>', methods=['POST'])
@login_required
def delete_course(id):
    c = Course.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    if StudentGroup.query.filter_by(course_id=id).first() or Subject.query.filter_by(course_id=id).first():
        return jsonify({"status": "error", "message": "Course has associated groups or subjects"}), 400
    db.session.delete(c)
    db.session.commit()
    return jsonify({"status": "success"})

@main.route('/api/group/add', methods=['POST'])
@login_required
def add_group():
    name = request.form.get('name')
    course_id = request.form.get('course_id')
    size = request.form.get('size')
    g = StudentGroup(name=name, course_id=course_id, size=size, user_id=current_user.id)
    db.session.add(g)
    db.session.commit()
    return jsonify({"status": "success", "item": {"id": g.id, "name": g.name}})

@main.route('/api/group/delete/<int:id>', methods=['POST'])
@login_required
def delete_group(id):
    g = StudentGroup.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(g)
    db.session.commit()
    return jsonify({"status": "success"})

@main.route('/timetable')
@login_required
def view_timetable():
    # Filtering
    filter_type = request.args.get('type')
    filter_value = request.args.get('value')
    
    # Base queries filtered by user
    all_groups = StudentGroup.query.filter_by(user_id=current_user.id).all()
    all_days = [d[0] for d in db.session.query(TimeSlot.day).filter_by(user_id=current_user.id).distinct().all()]
    if not all_days:
        all_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    all_slots = [s[0] for s in db.session.query(TimeSlot.slot_number).filter_by(user_id=current_user.id).distinct().order_by(TimeSlot.slot_number).all()]
    if not all_slots:
        all_slots = list(range(1, 9))

    query = TimetableEntry.query.filter_by(user_id=current_user.id)
    
    if filter_type and filter_value:
        if filter_type == 'faculty':
            query = query.join(Subject).filter(Subject.faculty_id == filter_value)
        elif filter_type == 'room':
            query = query.filter(TimetableEntry.room_id == filter_value)
        elif filter_type == 'group':
            query = query.filter(TimetableEntry.group_id == filter_value)
            
    entries = query.all()
    
    # Structure: group_name -> day -> slot -> entry
    grouped_schedule = {}
    
    # Initialize structure
    active_groups = all_groups
    if filter_type == 'group' and filter_value:
        active_groups = [g for g in all_groups if g.id == int(filter_value)]

    for group in active_groups:
        grouped_schedule[group.name] = {}
        for day in all_days:
            grouped_schedule[group.name][day] = {}
            for slot in all_slots:
                grouped_schedule[group.name][day][slot] = None

    # Fill data
    for e in entries:
        g_name = e.group.name
        if g_name in grouped_schedule:
            if e.day in grouped_schedule[g_name]:
                grouped_schedule[g_name][e.day][e.slot] = {
                    "subject": e.subject.name,
                    "faculty": e.subject.faculty.name if e.subject.faculty else "N/A",
                    "room": e.room.name
                }
    
    # Fetch solver score
    score_setting = SystemSetting.query.filter_by(user_id=current_user.id, key='LAST_SOLVER_SCORE').first()
    score = float(score_setting.value) if score_setting else 0.0

    # Pass filter options
    filter_options = {
        'faculty': Faculty.query.filter_by(user_id=current_user.id).all(),
        'groups': all_groups,
        'rooms': Room.query.filter_by(user_id=current_user.id).all()
    }
        
    return render_template('timetable.html', 
                          grouped_schedule=grouped_schedule, 
                          days=all_days, 
                          slots=all_slots,
                          filter_options=filter_options, 
                          score=score,
                          current_filter={'type': filter_type, 'value': int(filter_value) if filter_value else None})


@main.route('/generate-timetable', methods=['POST'])
@login_required
def generate():
    try:
        # 1. Fetch current user's settings and data
        settings = SystemSetting.query.filter_by(user_id=current_user.id).all()
        config = {s.key: _parse_setting_value(s.value) for s in settings}

        # Helper for user-specific data with limits
        def _get_limited(model, limit_key):
            limit = config.get(limit_key, 0)
            query = model.query.filter_by(user_id=current_user.id)
            if limit > 0:
                query = query.limit(limit)
            return query.all()

        subjects = _get_limited(Subject, 'LIMIT_MAX_SUBJECTS')
        groups = _get_limited(StudentGroup, 'LIMIT_MAX_GROUPS')
        rooms = _get_limited(Room, 'LIMIT_MAX_ROOMS')
        faculties = _get_limited(Faculty, 'LIMIT_MAX_FACULTIES')
        time_slots = TimeSlot.query.filter_by(user_id=current_user.id).all()
        
        if not subjects or not rooms:
             return jsonify({"error": "Insufficient data to generate timetable"}), 400

        # 2. Run Solver
        status, results, obj_value = solve_timetable(subjects, groups, rooms, faculties, time_slots, config=config)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # 3. Save to DB - isolated by user
            TimetableEntry.query.filter_by(user_id=current_user.id).delete() 
            
            # Save solver score
            score_setting = SystemSetting.query.filter_by(user_id=current_user.id, key='LAST_SOLVER_SCORE').first()
            if not score_setting:
                score_setting = SystemSetting(user_id=current_user.id, key='LAST_SOLVER_SCORE', value=str(obj_value))
                db.session.add(score_setting)
            else:
                score_setting.value = str(obj_value)
            
            for r in results:
                entry = TimetableEntry(
                    user_id=current_user.id,
                    subject_id=r['subject_id'],
                    room_id=r['room_id'],
                    group_id=r['group_id'],
                    day=r['day'],
                    slot=r['slot']
                )
                db.session.add(entry)
            
            db.session.commit()
            return jsonify({"status": "Success", "entries_generated": len(results), "solver_status": int(status)})
        else:
            # Create a simple mapping for status
            status_map = {
                cp_model.UNKNOWN: "UNKNOWN",
                cp_model.MODEL_INVALID: "MODEL_INVALID",
                cp_model.FEASIBLE: "FEASIBLE",
                cp_model.OPTIMAL: "OPTIMAL",
                cp_model.INFEASIBLE: "INFEASIBLE"
            }
            status_name = status_map.get(status, f"UNKNOWN STATUS CODE: {status}")
            # print(f"DEBUG: Solver returned status: {status} ({status_name})")
            
            # Analyze reasons
            reasons = analyze_constraints(subjects, groups, rooms, faculties, time_slots)
            
            return jsonify({
                "status": "Failed", 
                "message": f"No solution found. Status: {status_name}",
                "reasons": reasons
            }), 400


    except Exception as e:
        db.session.rollback()
        import traceback
        print("DEBUG: Exception occurred in generate()")
        traceback.print_exc()
        with open('error.log', 'w') as f:
            traceback.print_exc(file=f)
        return jsonify({"error": str(e)}), 500

@main.route('/api/faculty/add', methods=['POST'])
@login_required
def add_faculty():
    name = request.form.get('name')
    dept_id = request.form.get('department_id')
    max_hours = request.form.get('max_hours')
    
    f = Faculty(name=name, department_id=dept_id, max_hours_per_week=max_hours, user_id=current_user.id)
    db.session.add(f)
    db.session.commit()
    return jsonify({
        "status": "success",
        "item": {
            "id": f.id,
            "name": f.name,
            "max_hours_per_week": f.max_hours_per_week
        }
    })

@main.route('/api/faculty/delete/<int:id>', methods=['POST'])
@login_required
def delete_faculty(id):
    f = Faculty.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    Subject.query.filter_by(faculty_id=id, user_id=current_user.id).delete()
    db.session.delete(f)
    db.session.commit()
    return jsonify({"status": "success"})

@main.route('/api/import/preview', methods=['POST'])
@login_required
def import_preview():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
    
    file = request.files['file']
    entity_type = request.form.get('type') # 'faculty', 'room', 'subject', etc.
    
    if not file.filename.endswith('.csv'):
        return jsonify({"status": "error", "message": "Only CSV files allowed"}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        rows = list(csv_reader)
        
        # Basic validation of headers based on type
        expected_headers = {
            'department': ['Name'],
            'course': ['Name', 'Department'],
            'group': ['Name', 'Course', 'Size'],
            'faculty': ['Name', 'Department', 'Max Hours'],
            'room': ['Name', 'Capacity', 'Type'],
            'subject': ['Name', 'Course', 'Faculty', 'Hours', 'Is Lab']
        }
        
        if entity_type not in expected_headers:
            return jsonify({"status": "error", "message": f"Invalid entity type: {entity_type}"}), 400
            
        # Check if any required header is missing (case insensitive)
        actual_headers = [h.lower().strip() for h in rows[0].keys()] if rows else []
        missing = [h for h in expected_headers[entity_type] if h.lower().strip() not in actual_headers]
        
        if missing:
            return jsonify({"status": "error", "message": f"Missing columns: {', '.join(missing)}"}), 400

        return jsonify({"status": "success", "data": rows, "headers": expected_headers[entity_type]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route('/api/import/finalize', methods=['POST'])
@login_required
def import_finalize():
    data = request.json.get('data')
    entity_type = request.json.get('type')
    mode = request.json.get('mode', 'append')
    
    if not data or not entity_type:
        return jsonify({"status": "error", "message": "Missing data or type"}), 400

    try:
        count = 0
        if mode == 'replace':
            if entity_type == 'department':
                Department.query.filter_by(user_id=current_user.id).delete()
            elif entity_type == 'course':
                Course.query.filter_by(user_id=current_user.id).delete()
            elif entity_type == 'group':
                StudentGroup.query.filter_by(user_id=current_user.id).delete()
            elif entity_type == 'faculty':
                Faculty.query.filter_by(user_id=current_user.id).delete()
            elif entity_type == 'room':
                Room.query.filter_by(user_id=current_user.id).delete()
            elif entity_type == 'subject':
                Subject.query.filter_by(user_id=current_user.id).delete()

        if entity_type == 'department':
            existing = {d.name.lower(): d for d in Department.query.filter_by(user_id=current_user.id).all()}
            for row in data:
                name = row.get('Name') or row.get('name')
                if name and name.lower() not in existing:
                    db.session.add(Department(name=name, user_id=current_user.id))
                    count += 1
        
        elif entity_type == 'course':
            depts = {d.name.lower(): d.id for d in Department.query.filter_by(user_id=current_user.id).all()}
            existing = {c.name.lower(): c for c in Course.query.filter_by(user_id=current_user.id).all()}
            for row in data:
                name = row.get('Name') or row.get('name')
                dept_name = (row.get('Department') or row.get('department') or "").lower().strip()
                if name and dept_name in depts and name.lower() not in existing:
                    db.session.add(Course(name=name, department_id=depts[dept_name], user_id=current_user.id))
                    count += 1

        elif entity_type == 'group':
            courses = {c.name.lower(): c.id for c in Course.query.filter_by(user_id=current_user.id).all()}
            existing = {g.name.lower(): g for g in StudentGroup.query.filter_by(user_id=current_user.id).all()}
            for row in data:
                name = row.get('Name') or row.get('name')
                course_name = (row.get('Course') or row.get('course') or "").lower().strip()
                size = row.get('Size') or row.get('size') or 60
                if name and course_name in courses and name.lower() not in existing:
                    db.session.add(StudentGroup(name=name, course_id=courses[course_name], size=size, user_id=current_user.id))
                    count += 1

        elif entity_type == 'faculty':
            depts = {d.name.lower(): d.id for d in Department.query.filter_by(user_id=current_user.id).all()}
            existing = {f.name.lower(): f for f in Faculty.query.filter_by(user_id=current_user.id).all()}
            for row in data:
                name = row.get('Name') or row.get('name')
                dept_name = (row.get('Department') or row.get('department') or "").lower().strip()
                hours = row.get('Max Hours') or row.get('hours') or 20
                if name and dept_name in depts and name.lower() not in existing:
                    db.session.add(Faculty(name=name, department_id=depts[dept_name], max_hours_per_week=hours, user_id=current_user.id))
                    count += 1

        elif entity_type == 'room':
            existing = {r.name.lower(): r for r in Room.query.filter_by(user_id=current_user.id).all()}
            for row in data:
                name = row.get('Name') or row.get('name')
                cap = row.get('Capacity') or row.get('capacity') or 50
                rtype = (row.get('Type') or row.get('type') or 'lecture').lower()
                if name and name.lower() not in existing:
                    db.session.add(Room(name=name, capacity=cap, type=rtype, user_id=current_user.id))
                    count += 1

        elif entity_type == 'subject':
            courses = {c.name.lower(): c.id for c in Course.query.filter_by(user_id=current_user.id).all()}
            faculty = {f.name.lower(): f.id for f in Faculty.query.filter_by(user_id=current_user.id).all()}
            existing = {s.name.lower(): s for s in Subject.query.filter_by(user_id=current_user.id).all()}
            for row in data:
                name = row.get('Name') or row.get('name')
                course_name = (row.get('Course') or row.get('course') or "").lower().strip()
                f_name = (row.get('Faculty') or row.get('faculty') or "").lower().strip()
                hours = row.get('Hours') or row.get('hours') or 3
                lab = str(row.get('Is Lab') or row.get('is_lab') or "").lower() == 'true'
                
                if name and course_name in courses and name.lower() not in existing:
                    s = Subject(
                        name=name, 
                        course_id=courses[course_name], 
                        faculty_id=faculty.get(f_name), 
                        hours_per_week=hours, 
                        is_lab=lab, 
                        user_id=current_user.id
                    )
                    db.session.add(s)
                    count += 1

        db.session.commit()
        return jsonify({"status": "success", "count": count})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route('/api/room/add', methods=['POST'])
@login_required
def add_room():
    name = request.form.get('name')
    capacity = request.form.get('capacity')
    rtype = request.form.get('type')
    r = Room(name=name, capacity=capacity, type=rtype, user_id=current_user.id)
    db.session.add(r)
    db.session.commit()
    return jsonify({
        "status": "success",
        "item": {
            "id": r.id,
            "name": r.name,
            "capacity": r.capacity,
            "type": r.type
        }
    })

@main.route('/api/room/delete/<int:id>', methods=['POST'])
@login_required
def delete_room(id):
    r = Room.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(r)
    db.session.commit()
    return jsonify({"status": "success"})

@main.route('/api/subject/add', methods=['POST'])
@login_required
def add_subject(): 
    name = request.form.get('name')
    course_id = request.form.get('course_id')
    faculty_id = request.form.get('faculty_id')
    hours = request.form.get('hours')
    is_lab = request.form.get('is_lab') == 'on'
    
    s = Subject(name=name, course_id=course_id, faculty_id=faculty_id, hours_per_week=hours, is_lab=is_lab, user_id=current_user.id)
    db.session.add(s)
    db.session.commit()
    return jsonify({
        "status": "success",
        "item": {
            "id": s.id,
            "name": s.name,
            "faculty_name": s.faculty.name if s.faculty else 'Unassigned',
            "hours_per_week": s.hours_per_week,
            "is_lab": s.is_lab
        }
    })

@main.route('/api/subject/delete/<int:id>', methods=['POST'])
@login_required
def delete_subject(id):
    s = Subject.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(s)
    db.session.commit()
    return jsonify({"status": "success"})



@main.route('/api/view/all', methods=['GET'])
@login_required
def get_all_timetable_api():
    entries = TimetableEntry.query.filter_by(user_id=current_user.id).all()
    # restructure by day
    output = {}
    for e in entries:
        if e.day not in output: output[e.day] = []
        output[e.day].append({
            "slot": e.slot,
            "subject": e.subject.name,
            "faculty": e.subject.faculty.name if e.subject.faculty else "N/A",
            "room": e.room.name,
            "group": e.group.name
        })
    # Sort
    for d in output:
        output[d].sort(key=lambda x: x['slot'])
        
    return jsonify(output)

@main.route('/faculty/<int:id>', methods=['GET'])
def get_faculty_timetable(id):
    entries = (TimetableEntry.query
               .join(Subject, TimetableEntry.subject_id == Subject.id)
               .filter(Subject.faculty_id == id)
               .all())
    
    return jsonify(_format_entries(entries))
    

@main.route('/department/<int:id>', methods=['GET'])
def get_dept_timetable(id):
    entries = (TimetableEntry.query
               .join(Subject)
               .join(Course)
               .filter(Course.department_id == id)
               .all())
    return jsonify(_format_entries(entries))

@main.route('/group/<int:id>', methods=['GET'])
def get_group_timetable(id):
    entries = TimetableEntry.query.filter_by(group_id=id).all()
    return jsonify(_format_entries(entries))



@main.route('/master-control')
@login_required
def master_control():
    _seed_default_settings()
    settings = SystemSetting.query.filter_by(user_id=current_user.id).all()
    return render_template('master_control.html', settings=settings)

@main.route('/api/settings/update', methods=['POST'])
@login_required
def update_settings():
    data = request.json
    for key, value in data.items():
        setting = SystemSetting.query.filter_by(key=key, user_id=current_user.id).first()
        if setting:
            setting.value = str(value)
    db.session.commit()
    return jsonify({"status": "success"})

@main.route('/api/settings/natural-language', methods=['POST'])
@login_required
def natural_language_control():
    prompt = request.json.get('prompt', '').lower()
    
    # Mapping of intent to setting changes
    nlp_map = {
        "faculty rest": {
            'CONSECUTIVE_PENALTY': 50,
            'MAX_CONSECUTIVE_LECTURES': 2,
            'CONSTRAINT_FACULTY_CONSECUTIVE_ENABLED': 'True'
        },
        "consecutive labs": {
            'CONSECUTIVE_LABS_WEIGHT': 200,
            'CONSTRAINT_LAB_CONSECUTIVE_ENABLED': 'True'
        },
        "distribute": {
            'SAME_DAY_MULTI_PENALTY': 50,
            'CONSTRAINT_SUBJECT_DISTRIBUTION_ENABLED': 'True'
        },
        "allow lecture in lab": {
            'LECTURES_IN_LABS': 'True'
        }
    }

    updates = {}
    found_intent = False
    redundant = True
    
    for intent, changes in nlp_map.items():
        if intent in prompt:
            found_intent = True
            for key, val in changes.items():
                setting = SystemSetting.query.filter_by(key=key, user_id=current_user.id).first()
                if not setting or setting.value != str(val):
                    redundant = False
                updates[key] = val

    if not found_intent:
        return jsonify({
            "status": "not_found", 
            "message": "I don't recognize this constraint. Try 'prioritize faculty rest' or 'consecutive labs'."
        }), 400

    if redundant:
        return jsonify({
            "status": "redundant",
            "message": "This constraint is already active and configured as requested."
        }), 200

    for key, val in updates.items():
        setting = SystemSetting.query.filter_by(key=key, user_id=current_user.id).first()
        if setting:
            setting.value = str(val)
        else:
            # Add if missing (though they should be seeded)
            new_setting = SystemSetting(key=key, value=str(val), user_id=current_user.id)
            db.session.add(new_setting)
    
    db.session.commit()
    return jsonify({"status": "success", "message": "Constraint updated successfully!"})

def _seed_time_slots():
    if not current_user.is_authenticated:
        return
    if TimeSlot.query.filter_by(user_id=current_user.id).first():
        return
        
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for day in days:
        for slot in range(1, 9):
            ts = TimeSlot(day=day, slot_number=slot, user_id=current_user.id)
            db.session.add(ts)
    db.session.commit()

def _seed_demo_data():
    if not current_user.is_authenticated or current_user.username != 'demo_institution':
        return
    if Faculty.query.filter_by(user_id=current_user.id).first():
        return

    # Departments
    cs = Department(name="Computer Science", user_id=current_user.id)
    ee = Department(name="Electrical Engineering", user_id=current_user.id)
    db.session.add_all([cs, ee])
    db.session.commit()

    # Faculty - CS
    f1 = Faculty(name="Dr. Sarah Johnson", department_id=cs.id, max_hours_per_week=20, user_id=current_user.id)
    f2 = Faculty(name="Prof. Michael Chen", department_id=cs.id, max_hours_per_week=18, user_id=current_user.id)
    f3 = Faculty(name="Dr. Alan Turing", department_id=cs.id, max_hours_per_week=15, user_id=current_user.id)
    f4 = Faculty(name="Grace Hopper", department_id=cs.id, max_hours_per_week=18, user_id=current_user.id)
    
    # Faculty - EE
    f5 = Faculty(name="Dr. Emily Davis", department_id=ee.id, max_hours_per_week=22, user_id=current_user.id)
    f6 = Faculty(name="Nikola Tesla", department_id=ee.id, max_hours_per_week=20, user_id=current_user.id)
    f7 = Faculty(name="James Maxwell", department_id=ee.id, max_hours_per_week=15, user_id=current_user.id)
    
    db.session.add_all([f1, f2, f3, f4, f5, f6, f7])
    db.session.commit()

    # Courses & Groups
    c1 = Course(name="B.Tech CS", department_id=cs.id, user_id=current_user.id)
    c2 = Course(name="B.Tech EE", department_id=ee.id, user_id=current_user.id)
    db.session.add_all([c1, c2])
    db.session.commit()

    g1 = StudentGroup(name="CS-2024", course_id=c1.id, size=60, user_id=current_user.id)
    g2 = StudentGroup(name="CS-2023", course_id=c1.id, size=55, user_id=current_user.id)
    g3 = StudentGroup(name="EE-2024", course_id=c2.id, size=45, user_id=current_user.id)
    g4 = StudentGroup(name="EE-2023", course_id=c2.id, size=40, user_id=current_user.id)
    db.session.add_all([g1, g2, g3, g4])
    db.session.commit()

    # Rooms
    r1 = Room(name="Lecture Hall 1", capacity=100, type="lecture", user_id=current_user.id)
    r2 = Room(name="CS Lab Alpha", capacity=75, type="lab", user_id=current_user.id)
    r3 = Room(name="EE Lab Beta", capacity=60, type="lab", user_id=current_user.id)
    r4 = Room(name="Seminar Room 1", capacity=50, type="lecture", user_id=current_user.id)
    db.session.add_all([r1, r2, r3, r4])
    db.session.commit()

    # Subjects - CS
    s1 = Subject(name="Deep Learning", course_id=c1.id, hours_per_week=4, faculty_id=f1.id, is_lab=False, user_id=current_user.id)
    s2 = Subject(name="Data Structures", course_id=c1.id, hours_per_week=3, faculty_id=f2.id, is_lab=False, user_id=current_user.id)
    s3 = Subject(name="AI Lab", course_id=c1.id, hours_per_week=2, faculty_id=f1.id, is_lab=True, user_id=current_user.id)
    s4 = Subject(name="Operating Systems", course_id=c1.id, hours_per_week=3, faculty_id=f3.id, is_lab=False, user_id=current_user.id)
    s5 = Subject(name="Database Systems", course_id=c1.id, hours_per_week=3, faculty_id=f4.id, is_lab=False, user_id=current_user.id)
    
    # Subjects - EE
    s6 = Subject(name="Power Systems", course_id=c2.id, hours_per_week=4, faculty_id=f5.id, is_lab=False, user_id=current_user.id)
    s7 = Subject(name="Control Theory", course_id=c2.id, hours_per_week=3, faculty_id=f6.id, is_lab=False, user_id=current_user.id)
    s8 = Subject(name="Electromagnetism", course_id=c2.id, hours_per_week=3, faculty_id=f7.id, is_lab=False, user_id=current_user.id)
    s9 = Subject(name="Circuit Design", course_id=c2.id, hours_per_week=3, faculty_id=f6.id, is_lab=True, user_id=current_user.id)
    
    db.session.add_all([s1, s2, s3, s4, s5, s6, s7, s8, s9])
    db.session.commit()

def _parse_setting_value(val):
    if val.lower() == 'true': return True
    if val.lower() == 'false': return False
    try:
        if '.' in val: return float(val)
        return int(val)
    except:
        return val

def _seed_default_settings():
    if not current_user.is_authenticated:
        return
        
    defaults = [
        ('CONSECUTIVE_LABS_WEIGHT', '100', 'Penalty for fragmented lab slots'),
        ('MAX_HOURS_PENALTY', '500', 'Penalty for exceeding faculty max hours'),
        ('CONSECUTIVE_PENALTY', '10', 'Penalty for too many consecutive lectures'),
        ('SAME_DAY_MULTI_PENALTY', '10', 'Penalty for multiple lectures of same subject on same day'),
        ('LECTURES_IN_LABS', 'False', 'Allow lectures to be scheduled in lab rooms'),
        ('MAX_CONSECUTIVE_LECTURES', '3', 'Max lectures a faculty can teach in a row'),
        ('SOLVER_TIME_LIMIT', '30', 'Max seconds the solver will run (Max 60 recommended)'),
        ('LIMIT_MAX_FACULTIES', '0', 'Limit number of faculties for routine (0 for all)'),
        ('LIMIT_MAX_GROUPS', '0', 'Limit number of student groups for routine (0 for all)'),
        ('LIMIT_MAX_SUBJECTS', '0', 'Limit number of subjects for routine (0 for all)'),
        ('LIMIT_MAX_ROOMS', '0', 'Limit number of rooms for routine (0 for all)'),
        ('CONSTRAINT_LAB_CONSECUTIVE_ENABLED', 'True', 'Enable consecutive lab slot constraints'),
        ('CONSTRAINT_FACULTY_MAX_HOURS_ENABLED', 'True', 'Enforce faculty weekly hour limits'),
        ('CONSTRAINT_FACULTY_CONSECUTIVE_ENABLED', 'True', 'Enforce limits on consecutive lectures'),
        ('CONSTRAINT_SUBJECT_DISTRIBUTION_ENABLED', 'True', 'Distribute subjects across different days'),
        ('LAST_SOLVER_SCORE', '0', 'Last optimization score')
    ]
    for key, val, desc in defaults:
        setting = SystemSetting.query.filter_by(key=key, user_id=current_user.id).first()
        if not setting:
            db.session.add(SystemSetting(key=key, value=val, description=desc, user_id=current_user.id))
        elif setting.description != desc:
            setting.description = desc
    db.session.commit()

def _format_entries(entries):
    output = {}
    for e in entries:
        if e.day not in output: output[e.day] = []
        output[e.day].append({
            "slot": e.slot,
            "subject": e.subject.name,
            "faculty": e.subject.faculty.name if e.subject.faculty else "N/A",
            "room": e.room.name,
            "group": e.group.name
        })
    for d in output:
        output[d].sort(key=lambda x: x['slot'])
    return output
