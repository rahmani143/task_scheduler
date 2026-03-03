import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime, date

DB_PATH = "tasks.db"

def init_db(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Desired schema (user-specified):
    # task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    # task_name TEXT NOT NULL,
    # due_date DATE,
    # due_time TIME,
    # duration_mins INTEGER,
    # scheduled_start DATETIME,
    # priority INTEGER,
    # is_fixed INTEGER,
    # status TEXT

    # If tasks table doesn't exist, create with new schema
    cur.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'""")
    if not cur.fetchone():
        cur.execute(
            """
            CREATE TABLE tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                due_date DATE,
                due_time TIME,
                duration_mins INTEGER DEFAULT 30,
                scheduled_start DATETIME,
                priority INTEGER DEFAULT 2,
                is_fixed INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending'
            )
            """
        )
        conn.commit()
        conn.close()
        return

    # If table exists, check columns and attempt a safe migration if needed
    cur.execute("PRAGMA table_info(tasks)")
    cols = [r[1] for r in cur.fetchall()]
    # If already using desired schema (has task_id), nothing to do
    if 'task_id' in cols:
        conn.close()
        return

    # Otherwise: migrate from older schema to new schema
    # Create new table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks_new (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            due_date DATE,
            due_time TIME,
            duration_mins INTEGER DEFAULT 30,
            scheduled_start DATETIME,
            priority INTEGER DEFAULT 2,
            is_fixed INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending'
        )
        """
    )

    # Try to copy rows from old table mapping known columns where possible
    # Common legacy columns: id or task_id, task_name, priority, deadline, status
    # Read current columns to decide mapping
    cur.execute("PRAGMA table_info(tasks)")
    old_cols = [r[1] for r in cur.fetchall()]

    select_cols = []
    if 'id' in old_cols:
        select_cols.append('id')
    if 'task_id' in old_cols:
        select_cols.append('task_id')
    if 'task_name' in old_cols:
        select_cols.append('task_name')
    if 'priority' in old_cols:
        select_cols.append('priority')
    if 'deadline' in old_cols:
        select_cols.append('deadline')
    if 'status' in old_cols:
        select_cols.append('status')

    if select_cols:
        # build simple SELECT
        cur.execute(f"SELECT {', '.join(select_cols)} FROM tasks")
        rows = cur.fetchall()
        for r in rows:
            # map by position
            row_map = dict(zip(select_cols, r))
            name = row_map.get('task_name') or row_map.get('task_id') or row_map.get('id')
            # map deadline -> due_date (if deadline stored as ISO date/time, split)
            deadline = row_map.get('deadline')
            due_date = None
            due_time = None
            if deadline:
                # if contains 'T' or space, split
                if 'T' in str(deadline):
                    parts = str(deadline).split('T')
                    due_date = parts[0]
                    due_time = parts[1]
                elif ' ' in str(deadline):
                    parts = str(deadline).split(' ')
                    due_date = parts[0]
                    due_time = parts[1]
                else:
                    due_date = str(deadline)

            priority = row_map.get('priority') if row_map.get('priority') is not None else 2
            status = row_map.get('status') or 'pending'

            cur.execute(
                "INSERT INTO tasks_new (task_name, due_date, due_time, duration_mins, scheduled_start, priority, is_fixed, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, due_date, due_time, 30, None, int(priority), 0, status)
            )

    # Replace old table
    cur.execute("DROP TABLE IF EXISTS tasks")
    cur.execute("ALTER TABLE tasks_new RENAME TO tasks")
    conn.commit()
    conn.close()


def clear_all_tasks(db_path: str = DB_PATH) -> None:
    """Wipes the database for a fresh start."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks")
    # Also reset the autoincrement counter for task_id
    cur.execute("DELETE FROM sqlite_sequence WHERE name='tasks'")
    conn.commit()
    conn.close()

def get_past_tasks(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Action 8: Retrieves tasks that are completed, missed, or from past dates."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Fetch tasks that are finished OR where the due_date is before today
    today = date.today().isoformat()
    cur.execute("""
        SELECT * FROM tasks 
        WHERE status IN ('completed', 'missed') 
        OR (due_date < ? AND status = 'pending')
        ORDER BY due_date DESC
    """, (today,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_overdue_tasks(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Fetches tasks that are past their due date but still pending."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    cur = conn.cursor()
    today = date.today().isoformat()
    
    # We use 'pending' specifically. Tasks already marked 'missed' 
    # or 'completed' are ignored by this check.
    cur.execute("SELECT * FROM tasks WHERE status = 'pending' AND due_date < ?", (today,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_task_date(task_id: int, new_date: str, db_path: str = DB_PATH) -> bool:
    """
    Updates the due date for a task. 
    Crucial for 'Spillover' logic where P1 tasks move to tomorrow.
    """
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # We ensure task_id is an int to prevent SQL injection or type errors
        cur.execute("UPDATE tasks SET due_date = ? WHERE task_id = ?", (new_date, int(task_id)))
        changed = cur.rowcount
        conn.commit()
        conn.close()
        return changed > 0
    except Exception as e:
        print(f"Database Error (update_task_date): {e}")
        return False


def add_task(task_name: str,
             priority: int = 2,
             due_date: Optional[str] = None,
             due_time: Optional[str] = None,
             duration_mins: int = 30,
             scheduled_start: Optional[str] = None,
             is_fixed: int = 0,
             status: str = 'pending',
             db_path: str = DB_PATH) -> int:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (task_name, due_date, due_time, duration_mins, scheduled_start, priority, is_fixed, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (task_name, due_date, due_time, int(duration_mins), scheduled_start, int(priority), int(is_fixed), status)
    )
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return task_id

def delete_task(task_id: int, db_path: str = DB_PATH) -> bool:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE task_id = ?", (int(task_id),))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed > 0

def get_all_tasks(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT task_id, task_name, due_date, due_time, duration_mins, scheduled_start, priority, is_fixed, status FROM tasks ORDER BY priority DESC")
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "task_id": r[0],
            "id": r[0],
            "task_name": r[1],
            "due_date": r[2],
            "due_time": r[3],
            "duration_mins": r[4],
            "scheduled_start": r[5],
            "priority": r[6],
            "is_fixed": r[7],
            "status": r[8]
        }
        for r in rows
    ]

# def fetch_tasks_for_date(target_date: Any, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
#     # 1. Handle the type check (This is the "Defensive" part)
#     if hasattr(target_date, 'isoformat'):
#         prefix = target_date.isoformat()
#     else:
#         # It's already a string, so just use it
#         prefix = str(target_date)
    
#     # 2. Database Connection
#     conn = sqlite3.connect(db_path)
#     cur = conn.cursor()

#     # 3. Execute Query (Using the 'prefix' we safely created above)
#     # We use LIKE with a % to handle cases where time might be appended
#     cur.execute("""
#         SELECT task_id, task_name, due_date, due_time, duration_mins, 
#                scheduled_start, priority, is_fixed, status 
#         FROM tasks 
#         WHERE (due_date LIKE ? OR due_date IS NULL) 
#         AND status='pending' 
#         ORDER BY priority DESC
#     """, (prefix + '%',))
    
#     rows = cur.fetchall()
#     conn.close()

#     # 4. Map to Dictionary
#     return [
#         {
#             "task_id": r[0],
#             "id": r[0],
#             "task_name": r[1],
#             "due_date": r[2],
#             "due_time": r[3],
#             "duration_mins": r[4],
#             "scheduled_start": r[5],
#             "priority": r[6],
#             "is_fixed": r[7],
#             "status": r[8]
#         }
#         for r in rows
#     ]

def fetch_tasks_for_date(target_date: Any, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    # Normalize prefix
    prefix = target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Query all columns for the specific date
    cur.execute("""
        SELECT task_id, task_name, due_date, due_time, duration_mins, 
               scheduled_start, priority, is_fixed, status 
        FROM tasks 
        WHERE due_date LIKE ? 
        ORDER BY priority DESC
    """, (prefix + '%',))
    
    rows = cur.fetchall()
    conn.close()

    print(f"🔍 DB_DEBUG: Found {len(rows)} raw rows in database for date: {prefix}")
    
    # --- FIXED MAPPING LOGIC ---
    formatted_tasks = []
    for r in rows:
        formatted_tasks.append({
            "task_id": r[0],
            "id": r[0],
            "task_name": r[1],
            "due_date": r[2],
            "due_time": r[3],
            "duration_mins": r[4],
            "scheduled_start": r[5],
            "priority": r[6],
            "is_fixed": r[7],
            "status": r[8]
        })
    return formatted_tasks

def update_task_status(task_id: int, status: str, db_path: str = DB_PATH) -> bool:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (status, int(task_id)))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed > 0


def update_task_scheduled_start(task_id: int, scheduled_start: Optional[str], db_path: str = DB_PATH) -> bool:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET scheduled_start = ? WHERE task_id = ?", (scheduled_start, int(task_id)))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed > 0

if __name__ == '__main__':
    init_db()
    print('Initialized DB at', DB_PATH)
