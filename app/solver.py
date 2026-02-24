from ortools.sat.python import cp_model

def solve_timetable(subjects, groups, rooms, faculties, time_slots, config=None):
    """
    Solves the timetable scheduling problem with dynamic configuration.
    """
    if config is None:
        config = {
            'CONSECUTIVE_LABS_WEIGHT': 100,
            'MAX_HOURS_PENALTY': 500,
            'CONSECUTIVE_PENALTY': 10,
            'SAME_DAY_MULTI_PENALTY': 10,
            'LECTURES_IN_LABS': False,
            'MAX_CONSECUTIVE_LECTURES': 3
        }

    model = cp_model.CpModel()

    # Determine time grid from time_slots or defaults
    if time_slots:
        days_map = sorted(list(set(ts.day for ts in time_slots)))
        slots_map = sorted(list(set(ts.slot_number for ts in time_slots)))
        num_days = len(days_map)
        slots_per_day = len(slots_map)
    else:
        days_map = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        slots_map = list(range(1, 9))
        num_days = 6
        slots_per_day = 8
    
    all_days = range(num_days)
    all_slots = range(slots_per_day)
    
    # Pre-compute valid rooms and organize events
    class_events = []
    for s in subjects:
        course_groups = [g for g in groups if g.course_id == s.course_id]
        if not course_groups:
             continue
        for g in course_groups:
             class_events.append({
                 'subject': s,
                 'group': g,
                 'hours': s.hours_per_week,
                 'faculty_id': s.faculty_id
             })

    # Variables
    x = {}
    for e_idx, event in enumerate(class_events):
        s = event['subject']
        g = event['group']
        
        event_valid_rooms = []
        for r in rooms:
            if s.is_lab and r.type != 'lab': continue
            # If config allows, lectures can happen in labs
            if not s.is_lab and r.type == 'lab' and not config.get('LECTURES_IN_LABS', False): continue
            if r.capacity < g.size: continue
            event_valid_rooms.append(r.id)
            
        event['valid_rooms'] = event_valid_rooms
        
        for d in all_days:
            for sl in all_slots:
                for r_id in event_valid_rooms:
                    x[(e_idx, d, sl, r_id)] = model.NewBoolVar(f'x_e{e_idx}_d{d}_s{sl}_r{r_id}')

    # --- Constraints ---

    # 1. Each event assigned exactly 'hours' times
    for e_idx, event in enumerate(class_events):
        model.Add(sum(x[(e_idx, d, sl, r)] 
                      for d in all_days 
                      for sl in all_slots 
                      for r in event['valid_rooms']) == event['hours'])

    # 2. A room cannot host two classes at same time
    for d in all_days:
        for sl in all_slots:
            for r in rooms:
                room_assignments = []
                for e_idx, event in enumerate(class_events):
                    if r.id in event['valid_rooms']:
                        room_assignments.append(x[(e_idx, d, sl, r.id)])
                model.Add(sum(room_assignments) <= 1)

    # 3. A student group cannot attend two classes at same time
    for g in groups:
        for d in all_days:
            for sl in all_slots:
                group_assignments = []
                for e_idx, event in enumerate(class_events):
                    if event['group'].id == g.id:
                        for r in event['valid_rooms']:
                            group_assignments.append(x[(e_idx, d, sl, r)])
                model.Add(sum(group_assignments) <= 1)

    # 4. Faculty cannot teach two classes at same time
    for f in faculties:
        for d in all_days:
            for sl in all_slots:
                faculty_assignments = []
                for e_idx, event in enumerate(class_events):
                    if event['faculty_id'] == f.id:
                        for r in event['valid_rooms']:
                            faculty_assignments.append(x[(e_idx, d, sl, r)])
                model.Add(sum(faculty_assignments) <= 1)

    # 5. Heavy penalty for exceeding faculty weekly hours limit (now a soft constraint but very heavy)
    obj_terms = []
    if config.get('CONSTRAINT_FACULTY_MAX_HOURS_ENABLED', True):
        for f in faculties:
            faculty_total_hours = []
            for e_idx, event in enumerate(class_events):
                if event['faculty_id'] == f.id:
                     for d in all_days:
                        for sl in all_slots:
                            for r in event['valid_rooms']:
                                faculty_total_hours.append(x[(e_idx, d, sl, r)])
            if faculty_total_hours:
                 excess_hours = model.NewIntVar(0, slots_per_day * num_days, f'excess_hours_f{f.id}')
                 model.Add(excess_hours >= sum(faculty_total_hours) - f.max_hours_per_week)
                 obj_terms.append(excess_hours * config.get('MAX_HOURS_PENALTY', 500))

    # --- Soft Constraints & Objective ---
    consecutive_penalty_weight = config.get('CONSECUTIVE_PENALTY', 10)
    same_day_multi_penalty_weight = config.get('SAME_DAY_MULTI_PENALTY', 10)
    max_consecutive = config.get('MAX_CONSECUTIVE_LECTURES', 3)

    # 1. Avoid > MAX_CONSECUTIVE lectures
    if config.get('CONSTRAINT_FACULTY_CONSECUTIVE_ENABLED', True):
        for f in faculties:
            for d in all_days:
                for start_slot in range(slots_per_day - max_consecutive):
                    window_assignments = []
                    for delta in range(max_consecutive + 1):
                        sl = start_slot + delta
                        for e_idx, event in enumerate(class_events):
                             if event['faculty_id'] == f.id:
                                 for r in event['valid_rooms']:
                                     window_assignments.append(x[(e_idx, d, sl, r)])
                    
                    is_overworked = model.NewBoolVar(f'overwork_f{f.id}_d{d}_s{start_slot}')
                    model.Add(sum(window_assignments) > max_consecutive).OnlyEnforceIf(is_overworked)
                    model.Add(sum(window_assignments) <= max_consecutive).OnlyEnforceIf(is_overworked.Not())
                    obj_terms.append(is_overworked * consecutive_penalty_weight)

    # 2. Distribute subject hours or group them (if Lab)
    for e_idx, event in enumerate(class_events):
        s = event['subject']
        for d in all_days:
            day_assignments = []
            for sl in all_slots:
                for r in event['valid_rooms']:
                    day_assignments.append(x[(e_idx, d, sl, r)])
            
            if s.is_lab and config.get('CONSTRAINT_LAB_CONSECUTIVE_ENABLED', True):
                # For labs, we WANT them together if scheduled on same day
                # We penalize fragmentation: if scheduled at sl and sl+2 but NOT sl+1
                for sl in range(slots_per_day - 2):
                    # fragments = is_sl AND (NOT is_sl+1) AND is_sl+2
                    at_sl = model.NewBoolVar(f'at_sl_{e_idx}_{d}_{sl}')
                    model.Add(at_sl == sum(x[(e_idx, d, sl, r)] for r in event['valid_rooms']))
                    
                    at_sl_plus_1 = model.NewBoolVar(f'at_sl1_{e_idx}_{d}_{sl}')
                    model.Add(at_sl_plus_1 == sum(x[(e_idx, d, sl+1, r)] for r in event['valid_rooms']))
                    
                    at_sl_plus_2 = model.NewBoolVar(f'at_sl2_{e_idx}_{d}_{sl}')
                    model.Add(at_sl_plus_2 == sum(x[(e_idx, d, sl+2, r)] for r in event['valid_rooms']))
                    
                    is_fragmented = model.NewBoolVar(f'fragment_{e_idx}_{d}_{sl}')
                    # (at_sl AND NOT at_sl1 AND at_sl2) -> is_fragmented
                    model.AddBoolAnd([at_sl, at_sl_plus_1.Not(), at_sl_plus_2]).OnlyEnforceIf(is_fragmented)
                    obj_terms.append(is_fragmented * config.get('CONSECUTIVE_LABS_WEIGHT', 100))
            elif not s.is_lab and config.get('CONSTRAINT_SUBJECT_DISTRIBUTION_ENABLED', True):
                # For lectures, we generally want to distribute them (avoid > 1 per day if hours <= days)
                if event['hours'] <= num_days:
                    is_clustered = model.NewBoolVar(f'cluster_e{e_idx}_d{d}')
                    model.Add(sum(day_assignments) > 1).OnlyEnforceIf(is_clustered)
                    model.Add(sum(day_assignments) <= 1).OnlyEnforceIf(is_clustered.Not())
                    obj_terms.append(is_clustered * same_day_multi_penalty_weight)

    model.Minimize(sum(obj_terms))

    # --- Solve ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(config.get('SOLVER_TIME_LIMIT', 30))
    status = solver.Solve(model)

    results = []
    obj_value = None
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        obj_value = solver.ObjectiveValue()
        for e_idx, event in enumerate(class_events):
            for d in all_days:
                for sl in all_slots:
                    for r_id in event['valid_rooms']:
                        if solver.Value(x[(e_idx, d, sl, r_id)]):
                            results.append({
                                'day': days_map[d],
                                'slot': slots_map[sl],
                                'subject': event['subject'].name,
                                'room': next(r.name for r in rooms if r.id == r_id),
                                'faculty': next(f.name for f in faculties if f.id == event['faculty_id']),
                                'group': event['group'].name,
                                'subject_id': event['subject'].id,
                                'room_id': r_id,
                                'group_id': event['group'].id,
                                'day_idx': d, 
                                'slot_idx': sl
                            })
    return status, results, obj_value

def analyze_constraints(subjects, groups, rooms, faculties, time_slots):
    """
    Analyzes the data to find potential reasons for infeasibility.
    Returns a list of strings (reasons).
    """
    reasons = []
    
    # Constants from data
    if time_slots:
        num_days = len(set(ts.day for ts in time_slots))
        slots_per_day = len(set(ts.slot_number for ts in time_slots))
    else:
        num_days = 6
        slots_per_day = 8
        
    total_slots = num_days * slots_per_day
    
    # 1. Global Slot Sufficiency
    total_course_hours = 0
    for s in subjects:
        course_groups = [g for g in groups if g.course_id == s.course_id]
        if course_groups:
             total_course_hours += s.hours_per_week * len(course_groups)
    
    total_room_slots = len(rooms) * total_slots
    if total_course_hours > total_room_slots:
        reasons.append(f"CRITICAL: Total required subject hours ({total_course_hours}) exceeds total available room slots ({total_room_slots}). Add more rooms or reduce course hours.")
        
    # 2. Room Type Bottlenecks
    lab_hours = 0
    lecture_hours = 0
    for s in subjects:
         course_groups = [g for g in groups if g.course_id == s.course_id]
         if course_groups:
             hrs = s.hours_per_week * len(course_groups)
             if s.is_lab: lab_hours += hrs
             else: lecture_hours += hrs
             
    lab_rooms = [r for r in rooms if r.type == 'lab']
    lecture_rooms = [r for r in rooms if r.type != 'lab'] 
    
    total_lab_slots = len(lab_rooms) * total_slots
    total_lecture_slots = len(lecture_rooms) * total_slots
    
    if lab_hours > total_lab_slots:
        reasons.append(f"CRITICAL: Total Lab hours ({lab_hours}) exceeds available Lab room slots ({total_lab_slots}). Add more Lab rooms.")
    if lecture_hours > total_lecture_slots:
        reasons.append(f"WARNING: Total Lecture hours ({lecture_hours}) exceeds available Lecture room slots ({total_lecture_slots}). Add more Lecture halls.")

    # 3. Group Hard Limits
    for g in groups:
        group_hours = 0
        for s in subjects:
            if s.course_id == g.course_id:
                group_hours += s.hours_per_week
        
        if group_hours > total_slots:
            reasons.append(f"CRITICAL: Group '{g.name}' requires {group_hours} hours/week, but there are only {total_slots} slots available.")

    # 4. Room Size Mismatch
    max_lab_capacity = max([r.capacity for r in lab_rooms]) if lab_rooms else 0
    max_lecture_capacity = max([r.capacity for r in lecture_rooms]) if lecture_rooms else 0
    
    for g in groups:
        has_lab = any(s.is_lab and s.course_id == g.course_id for s in subjects)
        has_lecture = any(not s.is_lab and s.course_id == g.course_id for s in subjects)
        
        if has_lab and g.size > max_lab_capacity:
            reasons.append(f"CRITICAL: Group '{g.name}' (Size: {g.size}) is too large for any Lab room (Max Cap: {max_lab_capacity}).")
            
        if has_lecture and g.size > max_lecture_capacity:
            reasons.append(f"CRITICAL: Group '{g.name}' (Size: {g.size}) is too large for any Lecture room (Max Cap: {max_lecture_capacity}).")

    return reasons
