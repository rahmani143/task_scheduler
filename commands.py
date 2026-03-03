"""
Enumerated task commands for Brother.
Consolidated and updated for Clear/History functionality.
"""

class Commands:
    """Numbered commands the user/agent can invoke."""
    EXIT = 0
    ADD_TASK = 1
    DELETE_TASK = 2
    SHOW_SCHEDULE = 3
    MORNING_BRIEF = 4
    LIST_TASKS = 5
    MARK_COMPLETE = 6
    CLEAR_DATABASE = 7
    FIND_HISTORY = 8

    COMMAND_NAMES = {
        0: "Exit",
        1: "Add Task",
        2: "Delete Task",
        3: "Show Schedule",
        4: "Morning Brief",
        5: "List All Tasks",
        6: "Mark Task Complete",
        7: "Clear Database (WIPE)",
        8: "View History / Past Tasks"
    }

    COMMAND_HELP = {
        1: "Usage: 1 <task_name> <due_date> <duration_mins> <priority>",
        2: "Usage: 2 <task_id>",
        3: "Usage: 3",
        4: "Usage: 4",
        5: "Usage: 5",
        6: "Usage: 6 <task_id>",
        7: "Usage: 7 (Wipes everything)",
        8: "Usage: 8 (Shows completed/overdue)"
    }


def print_menu():
    """Print the main menu."""
    print("\n" + "="*60)
    print("🤖 Brother — Task Manager")
    print("="*60)
    # Sorting by ID ensures the menu stays rigid and predictable
    for cmd_id in sorted(Commands.COMMAND_NAMES.keys()):
        name = Commands.COMMAND_NAMES[cmd_id]
        print(f"  {cmd_id}. {name}")
    print("="*60)


def parse_user_input(user_input: str) -> tuple:
    """Parse user input (text or speech) into command and args."""
    user_input = user_input.strip().lower()
    tokens = user_input.split()
    if not tokens:
        return None, {}
    
    # 1. Try to extract command by number
    try:
        cmd_id = int(tokens[0])
        args_str = " ".join(tokens[1:])
        return cmd_id, {"args": args_str, "tokens": tokens[1:]}
    except ValueError:
        # 2. Try to match by keyword (Best for Voice transcription)
        if "add" in user_input:
            return Commands.ADD_TASK, {"args": user_input, "tokens": tokens}
        elif "delete" in user_input or "remove" in user_input:
            return Commands.DELETE_TASK, {"args": user_input, "tokens": tokens}
        elif "schedule" in user_input or "today" in user_input:
            return Commands.SHOW_SCHEDULE, {"args": "", "tokens": []}
        elif "brief" in user_input or "morning" in user_input:
            return Commands.MORNING_BRIEF, {"args": "", "tokens": []}
        elif "list" in user_input or "all" in user_input:
            return Commands.LIST_TASKS, {"args": "", "tokens": []}
        elif "complete" in user_input or "done" in user_input or "finish" in user_input:
            return Commands.MARK_COMPLETE, {"args": user_input, "tokens": tokens}
        elif "clear" in user_input or "wipe" in user_input:
            return Commands.CLEAR_DATABASE, {"args": "", "tokens": []}
        elif "history" in user_input or "past" in user_input:
            return Commands.FIND_HISTORY, {"args": "", "tokens": []}
        elif "exit" in user_input or "quit" in user_input:
            return Commands.EXIT, {"args": "", "tokens": []}
        
        return None, {}