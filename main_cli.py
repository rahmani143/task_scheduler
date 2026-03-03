"""
Brother — Task Manager (Text + Voice Hybrid Interface)

Supports both text input and voice transcription.
Commands are numbered for clarity and agent efficiency.
"""
import sys
import os
import db
import adk_tools
import listener
import commands
import dateparser
import re
from datetime import datetime

def format_task(task: dict) -> str:
    """Format a task dict for display."""
    tid = task.get('task_id') or task.get('id')
    name = task.get('task_name', 'N/A')
    due = task.get('due_date', 'N/A')
    time_str = task.get('due_time', '')
    dur = task.get('duration_mins', 'N/A')
    prio = task.get('priority', 'N/A')
    status = task.get('status', 'N/A')
    fixed = "fixed" if task.get('is_fixed') else "movable"
    
    due_str = f"{due} {time_str}".strip()
    return f"[{tid}] {name} | Due: {due_str} | Dur: {dur}min | Priority: {prio} | Status: {status} ({fixed})"


def handle_add_task(args_str: str) -> bool:
    """
    Handle ADD_TASK command for both GUI and CLI inputs.
    Ensures dates are normalized to ISO format and relative times match system clock.
    """
    from datetime import datetime
    import dateparser
    import adk_tools

    print("🔧 Add Task")
    
    # 1. Initialize variables to prevent UnboundLocalError
    due_date = None
    due_time = None
    task_name = ""
    duration_mins = 30
    priority = 2
    is_fixed = 0
    
    # Use system local time as the reference base for dateparser
    now = datetime.now()

    # --- CASE A: INPUT FROM GUI OR CLI ARGUMENTS ---
    if args_str:
        parts = args_str.split('\t')
        if len(parts) < 4:
            print("  ❌ Format: task_name<TAB>due_date<TAB>duration_mins<TAB>priority[<TAB>is_fixed]")
            return False
        
        task_name = parts[0].strip()
        due_date_str = parts[1].strip()
        
        try:
            duration_mins = int(parts[2].strip())
            priority = int(parts[3].strip())
            is_fixed = int(parts[4].strip()) if len(parts) > 4 else 0
        except ValueError:
            print("  ❌ duration_mins and priority must be integers.")
            return False
        
        
        # Parse the date string using local 'now' as base
        try:
            # Parse the string (e.g., "today 9pm") relative to right now
            parsed = dateparser.parse(due_date_str, settings={'RELATIVE_BASE': now})
            
            if parsed:
                # 1. Store as '2026-02-26'
                due_date = parsed.date().isoformat()
                
                # 2. Store as '19:33' (24-hour format for the database)
                due_time = parsed.strftime("%H:%M")
            else:
                print(f"  ❌ Could not parse date: {due_date_str}")
                return False
        except Exception as e:
            print(f"  ❌ Date parse error: {e}")
            return False

    # --- CASE B: INTERACTIVE INPUT FROM TERMINAL ---
    else:
        print("  Task name: ", end='')
        task_name = input().strip()
        print("  Due date (e.g., tomorrow 3 PM, 2026-02-26 15:00): ", end='')
        due_date_str = input().strip()
        print("  Duration in minutes: ", end='')
        duration_str = input().strip()
        print("  Priority (1-3): ", end='')
        priority_str = input().strip()
        print("  Is fixed? (0=movable, 1=fixed): ", end='')
        is_fixed_str = input().strip()
        
        try:
            parsed = dateparser.parse(due_date_str, settings={'RELATIVE_BASE': now})
            if not parsed:
                print("  ❌ Could not parse date.")
                return False
            due_date = parsed.date().isoformat()
            due_time = parsed.strftime("%H:%M")
            
            duration_mins = int(duration_str) if duration_str else 30
            priority = int(priority_str) if priority_str else 2
            is_fixed = int(is_fixed_str) if is_fixed_str else 0
        except Exception as e:
            print(f"  ❌ Input error: {e}")
            return False
    
    # --- FINAL: CONSTRUCT TASK AND COMMIT ---
    task = {
        "task_name": task_name,
        "due_date": due_date,
        "due_time": due_time,
        "duration_mins": duration_mins,
        "priority": priority,
        "is_fixed": is_fixed
    }
    
    # Attempt to schedule via ADK Tools
    res = adk_tools.manage_schedule_conflict(task)
    
    if res.get('ok'):
        print(f"  ✅ {res.get('message')}")
        return True
    elif res.get('ask_user'):
        print(f"  ⚠ {res.get('message')}")
        print("  Enter 'y' to move fixed tasks or 'n' to cancel: ", end='')
        confirm = input().strip().lower()
        if confirm in ('y', 'yes'):
            res2 = adk_tools.manage_schedule_conflict(task, force_move_fixed=True)
            if res2.get('ok'):
                print(f"  ✅ {res2.get('message')}")
                return True
        print("  ❌ Task not added.")
        return False
    else:
        print(f"  ❌ {res.get('message')}")
        return False


def handle_delete_task(args_str: str) -> bool:
    """Handle DELETE_TASK command with a table preview."""
    print("\n🗑️ Delete Task")
    
    # --- 1. DISPLAY CURRENT TASKS IN TABLE FORMAT ---
    all_tasks = db.get_all_tasks()
    if not all_tasks:
        print("  ❌ No tasks found to delete.")
        return True

    print("-" * 85)
    print(f"{'ID':<5} | {'Task Name':<25} | {'Due Date':<12} | {'Prio':<5} | {'Status':<10}")
    print("-" * 85)
    for t in all_tasks:
        tid = t.get('task_id') or t.get('id')
        name = (t.get('task_name')[:22] + '..') if len(t.get('task_name', '')) > 22 else t.get('task_name', 'N/A')
        due = t.get('due_date', 'N/A')
        prio = t.get('priority', 'N/A')
        status = t.get('status', 'N/A')
        print(f"{tid:<5} | {name:<25} | {due:<12} | {prio:<5} | {status:<10}")
    print("-" * 85)

    # --- 2. HANDLE THE DELETE LOGIC ---
    task_id = None
    if args_str:
        m = re.search(r'(\d+)', args_str)
        if m:
            task_id = int(m.group(1))
    
    if task_id is None:
        print("  Enter Task ID to delete (or press Enter to cancel): ", end='')
        raw_id = input().strip()
        if not raw_id:
            print("  ❌ Operation cancelled.")
            return False
        try:
            task_id = int(raw_id)
        except ValueError:
            print("  ❌ Invalid task ID.")
            return False

    # --- 3. EXECUTE DELETE ---
    res = adk_tools.delete_task(task_id)
    if res.get('ok'):
        print(f"  ✅ Task {task_id} successfully removed from Brother's records.")
        return True
    else:
        print(f"  ❌ Failed to delete task {task_id}. Check if the ID is correct.")
        return False


def handle_show_schedule(args_str: str = "") -> bool:
    """Handle SHOW_SCHEDULE command."""
    print("📅 Today's Schedule")
    res = adk_tools.generate_optimized_schedule()
    scheduled = res.get('scheduled', [])
    
    if not scheduled:
        print("  No tasks scheduled for today.")
        return True
    
    for item in scheduled:
        print(f"  {item['start']} - {item['task_name']} (Priority {item['priority']}, {item['duration_mins']}min)")
    
    return True


def handle_morning_brief(args_str: str = "") -> bool:
    """Handle MORNING_BRIEF command."""
    print("☀️ Morning Brief")
    # Placeholder for morning brief logic
    print("  Good morning! Here's your task summary:")
    
    all_tasks = db.get_all_tasks()
    pending = [t for t in all_tasks if t.get('status') == 'pending']
    
    if not pending:
        print("  ✅ No pending tasks!")
    else:
        print(f"  📋 {len(pending)} task(s) pending:")
        for t in pending[:5]:  # Show first 5
            print(f"    - {format_task(t)}")
    
    return True


def handle_list_tasks(args_str: str = "") -> bool:
    """Handle LIST_TASKS command."""
    print("📋 All Tasks")
    all_tasks = db.get_all_tasks()
    
    if not all_tasks:
        print("  No tasks in database.")
        return True
    
    for t in all_tasks:
        print(f"  {format_task(t)}")
    
    return True

def handle_clear_db():
    print("⚠️ DANGER: This will delete ALL tasks.")
    print("Confirm by typing 'DELETE ALL': ", end='')
    confirm = input().strip()
    if confirm == "DELETE ALL":
        db.clear_all_tasks() # You'll need to add this to your db.py
        print("✅ Database wiped clean.")
        return True
    print("❌ Operation cancelled.")
    return False
    

def handle_find_history():
    print("📜 Historical Records")
    # Fetch tasks where status is 'completed' or date is before today
    history = db.get_past_tasks() 
    if not history:
        print("  No past records found.")
        return True
    
    for t in history:
        print(f"  {format_task(t)}")
    return True


def handle_mark_complete(args_str: str) -> bool:
    """Handle MARK_COMPLETE command."""
    print("✅ Mark Task Complete")
    
    task_id = None
    if args_str:
        m = re.search(r'(\d+)', args_str)
        if m:
            task_id = int(m.group(1))
        else:
            print("  ❌ No task ID found in input.")
            return False
    else:
        print("  Task ID: ", end='')
        try:
            task_id = int(input().strip())
        except ValueError:
            print("  ❌ Invalid task ID.")
            return False
    
    res = adk_tools.mark_task_complete(task_id)
    print(f"  {res.get('message')}")
    return res.get('ok', False)

def parse_voice_to_cmd(transcribed_text):
    text = transcribed_text.lower()
    if "done" in text or "finish" in text:
        # Extract the ID from "I finished task 5"
        match = re.search(r'\d+', text)
        if match:
            return 6, match.group()
    elif "show" in text or "schedule" in text:
        return 3, ""
    # Fallback to standard parsing
    return commands.parse_user_input(text)

def process_command(cmd_id: int, args_str: str) -> bool:
    """Rigid Command Router."""
    if cmd_id == commands.Commands.ADD_TASK:       # 1
        return handle_add_task(args_str)
    elif cmd_id == commands.Commands.DELETE_TASK:  # 2
        return handle_delete_task(args_str)
    elif cmd_id == commands.Commands.SHOW_SCHEDULE: # 3
        return handle_show_schedule(args_str)
    elif cmd_id == commands.Commands.MORNING_BRIEF: # 4
        return handle_morning_brief(args_str)
    elif cmd_id == commands.Commands.LIST_TASKS:    # 5
        return handle_list_tasks(args_str)
    elif cmd_id == commands.Commands.MARK_COMPLETE: # 6 (Unified)
        return handle_mark_complete(args_str)
    elif cmd_id == 7: # Clear Database
        return handle_clear_db()
    elif cmd_id == 8: # Historical Search
        return handle_find_history()
    elif cmd_id == commands.Commands.EXIT:         # 0
        return False  
    else:
        print(f"  ❌ Unknown command: {cmd_id}")
        return True


def main():
    """Main REPL loop: text + voice hybrid."""
    db.init_db()

    adk_tools.run_overdue_check()

    print("=" * 60)
    print("🤖 Brother — Task Manager")
    print("=" * 60)
    print("Commands: Text input (e.g., '1 task_name\\tdate\\tduration\\tpriority')")
    print("          Voice input: Say wake word 'hey brother' then speak command")
    print("          Menu: Type 'm' or say 'menu' to show all commands")
    print("          Exit: Type '0' or say 'exit'")
    print("=" * 60 + "\n")
    
    try:
        while True:
            commands.print_menu()
            print("Enter command (text) or say 'hey brother' (voice), or 'm' for menu: ", end='')
            
            # Try to get text input first (non-blocking for 2 seconds)
            user_input = input().strip().lower()
            
            if user_input == 'm':
                continue
            elif user_input.startswith('v'):
                # Voice mode: activate listener
                print("\n🎤 Switching to voice mode. Say 'hey brother' to activate...\n")
                if listener.listen_for_wake_word():
                    listener.record_audio(silence_duration=2.0, max_duration=30.0)
                    transcribed = listener.transcribe_audio(listener.OUTPUT_FILENAME)
                    print(f"🎤 You said: {transcribed}\n")
                    user_input = transcribed
                    
                    # Clean up
                    try:
                        if os.path.exists(listener.OUTPUT_FILENAME):
                            os.remove(listener.OUTPUT_FILENAME)
                    except Exception:
                        pass
                else:
                    print("⚠️ Wake word not detected. Returning to text mode.\n")
                    continue
            
            # Parse command
            cmd_id, args = commands.parse_user_input(user_input)
            
            if cmd_id is None:
                print(f"  ❌ Could not parse: {user_input}")
                continue
            
            args_str = args.get('args', '')
            
            # Process command
            success = process_command(cmd_id, args_str)
            
            if not success and cmd_id == commands.Commands.EXIT:
                print("\n👋 Brother shutting down.")
                break
            
            print()
            
    except KeyboardInterrupt:
        print("\n\n👋 Brother interrupted. Shutting down.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
