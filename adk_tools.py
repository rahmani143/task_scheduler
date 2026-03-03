"""
ADK tool wrappers and the Throughput system instruction.
Provides functions that an LLM (Gemini ADK) can call: add_task, delete_task, generate_optimized_schedule.
"""
from datetime import datetime, date, timedelta, time
from typing import List, Dict, Any, Optional
import os
import db as dbmod
import warnings
from datetime import datetime, date, time
from typing import Optional, Dict, List, Any

warnings.filterwarnings("ignore", message=".*EspeakWrapper.*")

# --- RIGID SYSTEM INSTRUCTION ---
SYSTEM_INSTRUCTION = (
    "You are Brother, a rigid task-management controller. "
    "Your core protocol is the 'Priority Waterfall'. "
    "1. P3 tasks take absolute precedence. "
    "2. If P3 and P2 tasks fill the day (6 AM - 10 PM), you must automatically "
    "postpone P1 tasks to the next day. "
    "When asked for a 'MORNING_BRIEF', inform the user if any P1 tasks were spilled over."
)

def ensure_future_date(target_date_str: str) -> str:
    """Ensures dates are always pushed to the next available future occurrence."""
    try:
        now = datetime.now()
        dt = datetime.fromisoformat(target_date_str)
        if dt < now and dt.date() != now.date():
            dt += timedelta(days=7)
        return dt.date().isoformat()
    except:
        return target_date_str


# --- FIXED: ADDED MISSING DELETE FUNCTION ---
def delete_task(task_id: int) -> Dict[str, Any]:
    """Removes a task from the database by ID."""
    success = dbmod.delete_task(task_id)
    return {"ok": success}

# --- FIXED: CORRECTED db -> dbmod ALIAS ---
def run_overdue_check():
    overdue = dbmod.get_overdue_tasks() 
    if not overdue:
        return

    print("\n⚠️ Brother: I noticed some tasks were left unfinished.")
    for t in overdue:
        tid = t.get('task_id') or t.get('id')
        print(f"\n--- Overdue: {t['task_name']} (Due: {t['due_date']}) ---")
        print("What happened? [1] Completed  [2] Postpone  [3] It was missed")
        choice = input("Select (1-3): ").strip()

        if choice == '1':
            dbmod.update_task_status(tid, 'DONE')
            print("✅ Marked as done.")
        elif choice == '2':
            new_date = input("Enter new date (YYYY-MM-DD): ").strip()
            dbmod.update_task_date(tid, new_date)
            print(f"🔄 Postponed to {new_date}.")
        else:
            dbmod.update_task_status(tid, 'missed')
            print("❌ Marked as missed.")
    print("\n--- Cleanup complete. Proceeding to main menu. ---\n")

def mark_task_complete(task_id: int) -> Dict[str, Any]:
    ok = dbmod.update_task_status(task_id, 'DONE')
    return {"ok": ok, "message": f"Task {task_id} marked complete." if ok else "Failed."}

# def generate_optimized_schedule(target_date: Optional[str] = None) -> Dict[str, Any]:
#     from datetime import datetime, date, time, timedelta

#     # 1. Date Normalization
#     if target_date:
#         day = datetime.fromisoformat(target_date).date()
#     else:
#         day = date.today()

#     # 2. Database Fetch
#     tasks = dbmod.fetch_tasks_for_date(day.isoformat())
#     print(f"🧠 ADK_DEBUG: Received {len(tasks)} tasks from DB. Current Time: {datetime.now().time()}")
#     if not tasks:
#         return {"date": day.isoformat(), "scheduled": [], "spilled": []}

#     # 3. Dynamic Start Time (The key to fixing the 7:15 PM issue)
#     now = datetime.now()
#     if day == now.date():
#         # Round up to the next available half-hour
#         next_min = 30 if now.minute < 30 else 0
#         next_hour = now.hour if now.minute < 30 else (now.hour + 1) % 24
#         start_t = time(next_hour, next_min)
#     else:
#         start_t = time(6, 0) # Future days start early

#     # 4. Generate slots until the very end of the day
#     end_t = time(23, 30)
#     all_slots = list(_slot_generator(start_t, end_t)) if start_t < end_t else []
    
#     # NEW DEBUG: Check how many slots we actually have
#     print(f"🧠 ADK_DEBUG: Start Time: {start_t}, End Time: {end_t}")
#     print(f"🧠 ADK_DEBUG: Available slots left today: {len(all_slots)}")

#     schedule = []
#     spilled = []
    
#     for i, t in enumerate(sorted_tasks):
#         if i < len(all_slots):
#             # ... (your existing slotting logic) ...
#             pass
#         else:
#             # This task didn't fit!
#             print(f"⚠️ ADK_DEBUG: Task '{t['task_name']}' did not fit in today's slots.")
#             if t.get('priority', 1) == 1:
#                 tid = t.get('id') or t.get('task_id')
#                 new_date = (day + timedelta(days=1)).isoformat()
#                 dbmod.update_task_date(tid, new_date)
#                 spilled.append(t['task_name'])
#                 print(f"⏭️ ADK_DEBUG: P1 Task '{t['task_name']}' spilled to {new_date}")

#     print(f"🧠 ADK_DEBUG: Final Count -> Scheduled: {len(schedule)}, Spilled: {len(spilled)}")
#     return {"date": day.isoformat(), "scheduled": schedule, "spilled": spilled}

def configure_adk():
    try:
        import google.generativeai as genai
        # Look for the standard variable name
        api_key = os.environ.get('GOOGLE_API_KEY')
        
        if not api_key:
            print("⚠ ERROR: GOOGLE_API_KEY not found in environment variables.")
            return None
            
        genai.configure(api_key=api_key)
        return genai
    except ImportError:
        print("⚠ ERROR: google-generativeai package not installed. Run 'uv add google-generativeai'")
        return None
    except Exception as e:
        print(f"⚠ Configuration error: {e}")
        return None


def ask_agent(prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    genai = configure_adk()
    if genai is None:
        return f"I heard: {prompt}. (ADK not configured)"

    try:
        # 1. Use the specific 1.5-flash-latest model
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash", 
            system_instruction=SYSTEM_INSTRUCTION
        )

        # 2. Relax Safety Settings (Prevents the 'unable to generate content' error)
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        # 3. Format history for model compatibility
        formatted_history = []
        if history:
            for entry in history:
                role = "user" if entry['role'] == "user" else "model"
                formatted_history.append({"role": role, "parts": [entry['content']]})

        # 4. Generate with relaxed safety
        chat = model.start_chat(history=formatted_history)
        response = chat.send_message(prompt, safety_settings=safety_settings)
        
        return response.text

    except Exception as e:
        # If it still fails, check if the response was blocked by the safety filter
        if "FinishReason.SAFETY" in str(e) or "candidate" in str(e):
            return "Brother: My filters blocked that response. Try rephrasing."
        return f"Agent error: {str(e)}"

def add_task(task_name: str, priority: int = 2, due_date: Optional[str] = None, 
             due_time: Optional[str] = None, duration_mins: int = 30, 
             scheduled_start: Optional[str] = None, is_fixed: int = 0, 
             status: str = 'pending') -> Dict[str, Any]:
    
    if due_date:
        due_date = ensure_future_date(due_date)

    task_id = dbmod.add_task(
        task_name,
        priority=int(priority),
        due_date=due_date,
        due_time=due_time,
        duration_mins=int(duration_mins),
        scheduled_start=scheduled_start,
        is_fixed=int(is_fixed),
        status=status
    )
    return {"ok": True, "message": f"Slotted '{task_name}' for {due_date}.", "id": task_id}



def interview_task_draft(task_name: Optional[str], provided: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Interview flow helper for a single-agent drafting state.

    - `provided` contains any fields already known (due_date, due_time, duration_mins, priority, is_fixed).
    - Returns missing fields and a suggested next question for the agent to ask.
    """
    if provided is None:
        provided = {}

    # include task_name as required if not provided or empty
    required = ["due_date", "duration_mins", "priority"]
    if not task_name:
        required.insert(0, "task_name")
    missing = [r for r in required if provided.get(r) is None and r != 'task_name']
    # handle task_name separately
    if 'task_name' in required and (not provided.get('task_name') and not task_name):
        missing.insert(0, 'task_name')

    questions = {
        "due_date": "When is the deadline for this task (date and optional time)?",
        "duration_mins": "How long will this task take in minutes?",
        "priority": "What's the priority for this task? (1 low - 3 high)"
    }

    if missing:
        return {"ok": False, "missing": missing, "next_question": questions[missing[0]]}

    # all required info present
    # final task: prefer provided['task_name'] over parameter
    final_name = provided.get('task_name') or task_name
    task = {
        "task_name": final_name,
        "due_date": provided.get("due_date"),
        "due_time": provided.get("due_time"),
        "duration_mins": int(provided.get("duration_mins")),
        "priority": int(provided.get("priority")),
        "is_fixed": int(provided.get("is_fixed", 0))
    }
    return {"ok": True, "task": task}


def manage_schedule_conflict(new_task: Dict[str, Any], force_move_fixed: bool = False) -> Dict[str, Any]:
    """Attempt to schedule `new_task` before its deadline, resolving conflicts."""
    from datetime import datetime, timedelta

    # 1. Validate required fields
    for key in ("task_name", "due_date", "duration_mins", "priority"):
        if key not in new_task:
            return {"ok": False, "message": f"Missing field: {key}"}

    # 2. Compute deadline from input
    due_date = new_task.get("due_date")
    due_time = new_task.get("due_time") or "23:59"
    try:
        deadline_dt = datetime.fromisoformat(f"{due_date}T{due_time}")
    except Exception:
        try:
            deadline_dt = datetime.fromisoformat(f"{due_date} {due_time}")
        except Exception:
            return {"ok": False, "message": "Invalid due_date/due_time format"}

    duration = int(new_task.get("duration_mins", 30))
    proposed_start = deadline_dt - timedelta(minutes=duration)
    
    # --- CRITICAL FIX: LATE-DAY ALIGNMENT ---
    # If the calculated start is in the past, move it to NOW
    now = datetime.now().replace(second=0, microsecond=0)
    if proposed_start < now and due_date == now.date().isoformat():
        proposed_start = now
    
    proposed_end = proposed_start + timedelta(minutes=duration)

    # 3. Get existing tasks to check for overlaps
    target_date = deadline_dt.date()
    existing = dbmod.fetch_tasks_for_date(target_date)

    conflicts = []
    for t in existing:
        sched = t.get("scheduled_start")
        if not sched: continue
        try:
            t_start = datetime.fromisoformat(sched)
        except: continue
        t_end = t_start + timedelta(minutes=int(t.get("duration_mins", 30)))
        
        # Overlap check
        if (t_start < proposed_end) and (t_end > proposed_start):
            conflicts.append(t)

    # 4. Handle Fixed Task Conflicts
    fixed_conflicts = [t for t in conflicts if int(t.get("is_fixed", 0)) == 1]
    if fixed_conflicts and not force_move_fixed:
        names = ", ".join([t.get("task_name") for t in fixed_conflicts])
        return {"ok": False, "message": f"Conflicts with fixed tasks: {names}.", "ask_user": True, "conflicts": fixed_conflicts}

    # 5. Resolve Conflicts (Push existing tasks forward)
    moved = []
    for t in conflicts:
        old_start = t.get("scheduled_start")
        try:
            t_start = datetime.fromisoformat(old_start)
        except: continue
        
        # Move the conflicting task to start AFTER our new task ends
        new_start = proposed_end 
        dbmod.update_task_scheduled_start(int(t.get("task_id") or t.get("id")), new_start.isoformat())
        moved.append({"task_name": t.get("task_name"), "new_start": new_start.isoformat()})

    # 6. Final DB Insertion
    new_id = dbmod.add_task(
        new_task.get("task_name"),
        priority=int(new_task.get("priority", 2)),
        due_date=due_date,
        due_time=due_time,
        duration_mins=int(duration),
        scheduled_start=proposed_start.isoformat(),
        is_fixed=int(new_task.get("is_fixed", 0)),
        status='confirmed'
    )

    message = f"I've slotted '{new_task.get('task_name')}' for {proposed_start.strftime('%I:%M %p')} today."
    return {"ok": True, "message": message, "new_task_id": new_id, "changes": moved}


def mark_task_complete(task_id: int) -> Dict[str, Any]:
    # --- ADD THIS DEBUG LINE ---
    print(f"🛠️ DEBUG: Setting task {task_id} status to 'DONE'")
    
    ok = dbmod.update_task_status(task_id, 'DONE')
    return {"ok": ok, "message": f"Task {task_id} marked as DONE." if ok else "Failed."}


def _slot_generator(start: time, end: time, slot_minutes: int = 15):
    # Use a dummy date to do the math
    cur = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
    while cur < end_dt: # Use < instead of <= to avoid midnight crashes
        yield cur.time()
        cur += timedelta(minutes=slot_minutes)

# def generate_optimized_schedule(target_date: Optional[str] = None) -> Dict[str, Any]:
#     # 1. Normalize Date
#     if target_date:
#         day = datetime.fromisoformat(target_date).date()
#     else:
#         day = date.today()

#     # 2. Fetch Pending Tasks
#     tasks = dbmod.fetch_tasks_for_date(day.isoformat())
#     if not tasks:
#         return {"date": day.isoformat(), "scheduled": [], "message": "No tasks found."}

#     # 3. Time Slot Generation (6 AM to 10 PM)
#     now = datetime.now()
#     is_today = (day == now.date())
    
#     if is_today:
#         adj_hour = now.hour if now.minute < 30 else (now.hour + 1) % 24
#         adj_min = 30 if now.minute < 30 else 0
#         start_t = time(adj_hour, adj_min)
#     else:
#         start_t = time(6, 0)

#     end_t = time(22, 0)
#     all_available_slots = list(_slot_generator(start_t, end_t)) if start_t < end_t else []
    
#     # 4. Strict Waterfall Sorting (P3 -> P2 -> P1)
#     sorted_tasks = sorted(tasks, key=lambda x: -x.get('priority', 1))

#     schedule = []
#     spilled_tasks = []
    
#     # 5. Allocation with Automatic Spillover
#     for i, t in enumerate(sorted_tasks):
#         if i < len(all_available_slots):
#             # Task fits in today's window
#             slot = all_available_slots[i]
#             schedule.append({
#                 "id": t.get('id') or t.get('task_id'),
#                 "task_name": t['task_name'],
#                 "start": slot.strftime("%I:%M %p"),
#                 "priority": t.get('priority', 1),
#                 "duration_mins": t.get('duration_mins', 30),
#                 "status": "scheduled"
#             })
#         else:
#             # NO SLOTS LEFT: Check if it's a P1 task to move to tomorrow
#             if t.get('priority', 1) == 1:
#                 tomorrow = (day + timedelta(days=1)).isoformat()
#                 tid = t.get('id') or t.get('task_id')
#                 dbmod.update_task_date(tid, tomorrow) # Move in DB
#                 spilled_tasks.append(t['task_name'])

#     message = f"Schedule generated for {day.isoformat()}."
#     if spilled_tasks:
#         message += f" Note: {len(spilled_tasks)} Low Priority (P1) tasks moved to tomorrow due to schedule saturation."

#     return {
#         "date": day.isoformat(), 
#         "scheduled": schedule, 
#         "message": message,
#         "spilled": spilled_tasks
#     }

#     schedule = []
#     spilled = []
    
#     # Track when you are actually free
#     current_free_time = datetime.combine(day, start_t)

#     for t in sorted_tasks:
#         duration = int(t.get('duration_mins', 30))
        
#         # Find the first 30-min slot that starts at or after your current free time
#         available_slot = None
#         for s_time in all_slots:
#             slot_dt = datetime.combine(day, s_time)
#             if slot_dt >= current_free_time:
#                 available_slot = s_time
#                 break
        
#         if available_slot:
#             schedule.append({
#                 "id": t.get('id') or t.get('task_id'),
#                 "task_name": t['task_name'],
#                 "start": available_slot.strftime("%I:%M %p"),
#                 "priority": t.get('priority', 1),
#                 "duration_mins": duration,
#                 "status": t.get('status', 'pending')
#             })
#             # UPDATE FREE TIME: The next task cannot start until this one is finished
#             current_free_time = datetime.combine(day, available_slot) + timedelta(minutes=duration)
#         else:
#             # If no slots are left for this task, spill it
#             if t.get('priority', 1) == 1:
#                 tid = t.get('id') or t.get('task_id')
#                 dbmod.update_task_date(tid, (day + timedelta(days=1)).isoformat())
#                 spilled.append(t['task_name'])

#     return {"date": day.isoformat(), "scheduled": schedule, "spilled": spilled}


def generate_optimized_schedule(target_date: Optional[str] = None) -> Dict[str, Any]:
    # 1. Date Normalization
    if target_date:
        day = datetime.fromisoformat(target_date).date()
    else:
        day = date.today()

    # 2. Database Fetch
    tasks = dbmod.fetch_tasks_for_date(day.isoformat())
    if not tasks:
        return {"date": day.isoformat(), "scheduled": [], "spilled": []}

    # 3. Dynamic Start Time
    now = datetime.now()
    if day == now.date():
        # Round up to next 15-min block
        adj_min = (now.minute // 15 + 1) * 15
        adj_hour = now.hour + (adj_min // 60)
        adj_min = adj_min % 60
        start_t = time(adj_hour % 24, adj_min)
    else:
        start_t = time(6, 0)

    end_t = time(22, 0)
    all_slots = list(_slot_generator(start_t, end_t, slot_minutes=15))

    # 4. Sort by priority
    sorted_tasks = sorted(tasks, key=lambda x: -x.get('priority', 1))

    schedule = []
    spilled = []
    current_free_time = datetime.combine(day, start_t)

    # 5. Allocation with Duration Awareness
    for t in sorted_tasks:
        duration = int(t.get('duration_mins', 30))
        
        # Find first slot >= current_free_time
        available_slot = None
        for s_time in all_slots:
            slot_dt = datetime.combine(day, s_time)
            if slot_dt >= current_free_time:
                available_slot = s_time
                break
        
        if available_slot:
            schedule.append({
                "id": t.get('id') or t.get('task_id'),
                "task_name": t['task_name'],
                "start": available_slot.strftime("%I:%M %p"),
                "priority": t.get('priority', 1),
                "duration_mins": duration,
                "status": t.get('status', 'PENDING').upper()
            })
            current_free_time = datetime.combine(day, available_slot) + timedelta(minutes=duration)
        else:
            # Spill if P1
            if t.get('priority', 1) == 1:
                tid = t.get('id') or t.get('task_id')
                dbmod.update_task_date(tid, (day + timedelta(days=1)).isoformat())
                spilled.append(t['task_name'])

    return {"date": day.isoformat(), "scheduled": schedule, "spilled": spilled}


def calculate_throughput_schedule(db_path: str = dbmod.DB_PATH) -> List[Dict[str, Any]]:
    """
    Implements the user's throughput scheduling algorithm.
    - Considers tasks with status='pending'
    - Sort by priority desc, difficulty desc
    - Simulation start at 6:00 AM
    - Durations: Hard=3h, Med=1.5h, Easy=0.5h
    Returns a list of dicts with task name and window strings.
    """
    import sqlite3
    from datetime import datetime, timedelta

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT task_id, task_name, priority, due_date, duration_mins FROM tasks WHERE status='pending'")
    tasks = cursor.fetchall()

    optimized_schedule = []
    current_time = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)

    # Sort by priority (desc)
    tasks_sorted = sorted(tasks, key=lambda x: (x[2] if x[2] is not None else 0), reverse=True)

    for task in tasks_sorted:
        t_id, name, prio, due_date, duration_mins = task
        # use duration_mins when present, otherwise map priority to duration
        if duration_mins:
            duration_hours = float(duration_mins) / 60.0
        else:
            duration_hours = 3 if prio == 3 else (1.5 if prio == 2 else 0.5)
        start_str = current_time.strftime("%I:%M %p")
        current_time = current_time + timedelta(hours=duration_hours)
        end_str = current_time.strftime("%I:%M %p")
        optimized_schedule.append({
            "task": name,
            "window": f"{start_str} - {end_str}",
            "type": ("High Throughput" if prio == 3 else "Buffer/Maintenance")
        })

    conn.close()
    return optimized_schedule

if __name__ == '__main__':
    dbmod.init_db()
    print('ADK tools ready. System instruction:')
    print(SYSTEM_INSTRUCTION)
