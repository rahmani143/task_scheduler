import sqlite3

def run_migration():
    # Connect to your tasks.db
    conn = sqlite3.connect('tasks.db')
    cur = conn.cursor()
    
    # This flips every 'COMPLETED' status to 'DONE'
    cur.execute("UPDATE tasks SET status = 'DONE' WHERE status = 'COMPLETED'")
    
    conn.commit()
    conn.close()
    print("Migration successful: All 'COMPLETED' tasks are now 'DONE'.")

if __name__ == "__main__":
    run_migration()