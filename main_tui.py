import sys
import os
import platform
import ctypes
from importlib.util import find_spec
import adk_tools
from datetime import datetime, date  # <--- ADD 'date' HERE
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer # Added QTimer for the notification flash


# --- HARDWARE INITIALIZATION (CRITICAL FOR AGENT STABILITY) ---
# Force CPU usage to prevent the c10.dll/WinError 1114 crash
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

if platform.system() == "Windows":
    try:
        # Pre-load core DLLs to prevent initialization routine failures
        if (spec := find_spec("torch")) and spec.origin:
            lib_path = os.path.join(os.path.dirname(spec.origin), "lib")
            os.add_dll_directory(lib_path) # Modern Python 3.8+ way
            dll_path = os.path.join(lib_path, "c10.dll")
            if os.path.exists(dll_path):
                ctypes.CDLL(os.path.normpath(dll_path))
    except Exception:
        pass

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QHeaderView, QDialog, 
                             QLineEdit, QCheckBox, QFormLayout, QFrame,QTabWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QColor, QFont, QScreen

import db
import main_cli
import listener
import commands

# --- THREADING: THE AGENTIC WORKER ---
class AIWorker(QThread):
    status_update = pyqtSignal(str)
    finished = pyqtSignal()

    def run(self):
        self.status_update.emit("LISTENING...")
        if listener.listen_for_wake_word():
            self.status_update.emit("RECORDING...")
            listener.record_audio()
            
            self.status_update.emit("THINKING...")
            text = listener.transcribe_audio(listener.OUTPUT_FILENAME)
            
            if text:
                cmd_id, args = commands.parse_user_input(text)
                main_cli.process_command(cmd_id, args.get('args', ''))
        
        self.finished.emit()

# --- COMPONENT: TASK INPUT FORM ---
class AddTaskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Task Specification")
        self.setFixedSize(400, 320)
        self.set_style()
        
        layout = QFormLayout(self)
        self.name_in = QLineEdit()
        self.date_in = QLineEdit()
        self.date_in.setPlaceholderText("today, tomorrow, or YYYY-MM-DD")
        self.dur_in = QLineEdit()
        self.prio_in = QLineEdit()
        self.fixed_cb = QCheckBox("Fixed Task (Hard Constraint)")
        
        layout.addRow("Task Name:", self.name_in)
        layout.addRow("Due Date:", self.date_in)
        layout.addRow("Duration (m):", self.dur_in)
        layout.addRow("Priority:", self.prio_in)
        layout.addRow(self.fixed_cb)
        
        self.submit = QPushButton("COMMIT TO DATABASE")
        self.submit.clicked.connect(self.accept)
        layout.addRow(self.submit)

    def set_style(self):
        self.setStyleSheet("""
            QDialog { background-color: #1a1b26; color: #c0caf5; }
            QLabel { color: #7aa2f7; font-weight: bold; }
            QLineEdit { background-color: #24283b; border: 1px solid #414868; color: #c0caf5; padding: 5px; }
            QPushButton { background-color: #9ece6a; color: #1a1b26; font-weight: bold; padding: 10px; border-radius: 4px; }
            QPushButton:hover { background-color: #73daca; }
        """)

    def get_data(self):
        return {
            "name": self.name_in.text(),
            "date": self.date_in.text(),
            "dur": self.dur_in.text(),
            "prio": self.prio_in.text(),
            "fixed": 1 if self.fixed_cb.isChecked() else 0
        }

# --- MAIN INTERFACE ---
class BrotherGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BROTHER AI | AGENTIC WORKSTATION")
        self.resize(1100, 750)
        self.center_on_screen()
        self.apply_global_styles()
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # 1. Header Area
        self.status_lbl = QLabel("SYSTEM STATUS: OPTIMAL")
        self.main_layout.addWidget(self.status_lbl)

        # 2. Tabs System
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # Tab 1: Daily Schedule
        self.schedule_tab = QWidget()
        self.schedule_layout = QVBoxLayout(self.schedule_tab)
        self.schedule_table = QTableWidget()
        self.setup_table_headers(self.schedule_table, ["Start", "Task Name", "Min", "Prio", "Status"])
        self.schedule_layout.addWidget(self.schedule_table)
        self.tabs.addTab(self.schedule_tab, "📅 Daily Schedule")

        # Tab 2: Total Database
        self.db_tab = QWidget()
        self.db_layout = QVBoxLayout(self.db_tab)
        self.db_table = QTableWidget()
        self.setup_table_headers(self.db_table, ["ID", "Task Name", "Due Date", "Prio", "Status"])
        self.db_layout.addWidget(self.db_table)
        self.tabs.addTab(self.db_tab, "💾 Master Database")

        # 3. Enhanced Action Bar (Commands 0-8)
        action_layout = QVBoxLayout()
        
        # Row 1: Primary Task Actions (Add, Mark Complete, Voice)
        row1 = QHBoxLayout()
        self.btn_add = QPushButton("➕ NEW TASK (1)")
        self.btn_done = QPushButton("✅ MARK COMPLETE (6)")
        self.btn_mic = QPushButton("🎤 VOICE MODE (V)")
        for b in [self.btn_add, self.btn_done, self.btn_mic]: row1.addWidget(b)
        
        # Row 2: Viewing & Briefing (Brief, History, List)
        row2 = QHBoxLayout()
        self.btn_brief = QPushButton("☀️ MORNING BRIEF (4)")
        self.btn_history = QPushButton("📜 VIEW HISTORY (8)")
        self.btn_list = QPushButton("📋 REFRESH ALL (5)")
        for b in [self.btn_brief, self.btn_history, self.btn_list]: row2.addWidget(b)
        
        # Row 3: System & Maintenance (Delete, Wipe, Exit)
        row3 = QHBoxLayout()
        self.btn_delete = QPushButton("🗑️ DELETE TASK (2)")
        self.btn_clear = QPushButton("⚠️ WIPE DATABASE (7)")
        self.btn_exit = QPushButton("❌ EXIT (0)")
        for b in [self.btn_delete, self.btn_clear, self.btn_exit]: row3.addWidget(b)

        action_layout.addLayout(row1)
        action_layout.addLayout(row2)
        action_layout.addLayout(row3)
        self.main_layout.addLayout(action_layout)
        
        # New Event Connections
        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_done.clicked.connect(self.mark_done)
        self.btn_mic.clicked.connect(self.run_voice_agent)
        self.btn_brief.clicked.connect(self.run_brief)
        self.btn_history.clicked.connect(self.show_history)
        self.btn_list.clicked.connect(self.load_data)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_clear.clicked.connect(self.wipe_system)
        self.btn_exit.clicked.connect(self.close)

               

        # Notification Label (Starts hidden)
        self.notif_lbl = QLabel("")
        self.notif_lbl.setStyleSheet("color: #f7768e; font-weight: bold; font-size: 14px;")
        self.notif_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.insertWidget(1, self.notif_lbl) # Put it right under the status
        self.main_layout.addWidget(self.notif_lbl) 
        db.init_db()
        self.load_data()

    def notify_spillover(self, task_names):
        """Flashes a red notification when P1 tasks are moved to tomorrow."""
        if not task_names: return
        
        msg = f"⚠️ AUTO-POSTPONED TO TOMORROW: {', '.join(task_names)}"
        self.notif_lbl.setText(msg)
        
        # Simple flash effect
        def clear_notif(): self.notif_lbl.setText("")
        QTimer.singleShot(5000, clear_notif) # Hide after 5 seconds

    def setup_table_headers(self, table, headers):
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

    def load_all_views(self):
        """Refreshes both tabs simultaneously"""
        self.load_daily_schedule()
        self.load_master_db()

    def load_data(self):
        """Main entry point to refresh all UI views."""
        self.load_daily_schedule()
        self.load_master_db()


    def load_daily_schedule(self):
        """Loads schedule and triggers notification if P1 tasks moved."""
        res = adk_tools.generate_optimized_schedule()
        
        # 1. Debugging
        print(f"🖥️ TUI_DEBUG: Scheduled: {len(res.get('scheduled', []))}, Spilled: {len(res.get('spilled', []))}")
        
        # 2. Reset Table
        self.schedule_table.setRowCount(0)
        
        # 3. Handle Spillover Notification
        if res.get('spilled'):
            print(f"🖥️ TUI_DEBUG: Notifying user about: {res.get('spilled')}")
            self.notify_spillover(res.get('spilled'))

        scheduled = res.get('scheduled', [])
        
        # 4. Populate Table
        for t in scheduled:
            row = self.schedule_table.rowCount()
            self.schedule_table.insertRow(row)
            
            # Extract status safely
            status_text = t.get('status', 'PENDING').strip().upper()
            
            items = [
                t.get('start', 'N/A'),
                t.get('task_name', 'N/A'),
                str(t.get('duration_mins', '0')),
                str(t.get('priority', '1')),
                status_text
            ]
            
            # Use 'DONE' check
            is_done = ("DONE" in status_text)
            
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if is_done:
                    item.setBackground(QColor("#2e7d32")) # Engineering Green
                    item.setForeground(QColor("white"))
                self.schedule_table.setItem(row, col, item)

    def load_master_db(self):
        """Loads the raw total database with Overdue and Completion styling."""
        all_tasks = db.get_all_tasks()
        today_str = date.today().isoformat()
        
        self.db_table.setRowCount(0)
        for t in all_tasks:
            row = self.db_table.rowCount()
            self.db_table.insertRow(row)
            
            # Status Logic
            status_text = t.get('status', 'PENDING').strip().upper()
            is_done = ("DONE" in status_text)
            is_pending = (status_text == 'PENDING')
            is_past = t.get('due_date') < today_str if t.get('due_date') else False
            is_overdue = is_pending and is_past

            # Data to display
            display_status = "⚠️ OVERDUE" if is_overdue else status_text
            tid = str(t.get('id') or t.get('task_id'))
            items = [tid, t.get('task_name'), t.get('due_date'), str(t.get('priority')), display_status]
            
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                
                if is_done:
                    item.setBackground(QColor("#2e7d32"))
                    item.setForeground(QColor("white"))
                elif is_overdue:
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)
                    item.setForeground(QColor("#f7768e"))
                
                self.db_table.setItem(row, col, item)

    def mark_done(self):
        # Check which tab is currently active (0 = Schedule, 1 = Master DB)
        current_tab = self.tabs.currentIndex()
        active_table = self.schedule_table if current_tab == 0 else self.db_table
        row = active_table.currentRow()

        row = active_table.currentRow()
        if row >= 0:
            # If in Master DB, ID is in column 0
            if current_tab == 1:
                task_id = active_table.item(row, 0).text()
            else:
                # If in Schedule, we find the ID from the scheduled list
                res = adk_tools.generate_optimized_schedule()
                task_id = res.get('scheduled')[row].get('id')
            
            main_cli.handle_mark_complete(str(task_id))
            
            # FORCE A RE-FETCH
            db.init_db() 
            self.load_data() 
            print(f"✅ Refreshing UI for task {task_id}")
        
    def run_brief(self):
        """Command 4: Morning Brief"""
        self.status_lbl.setText("AGENT STATUS: GENERATING BRIEF...")
        main_cli.handle_morning_brief("") 
        self.status_lbl.setText("SYSTEM STATUS: OPTIMAL")

    def show_history(self):
        """Command 8: View History"""
        self.tabs.setCurrentIndex(1) # Switch to Master DB Tab
        self.status_lbl.setText("AGENT STATUS: FETCHING HISTORY...")
        # This will print to terminal and you can refresh view
        main_cli.handle_find_history()
        self.load_data()

    def delete_selected(self):
        """Command 2: Delete Task"""
        current_tab = self.tabs.currentIndex()
        active_table = self.schedule_table if current_tab == 0 else self.db_table
        row = active_table.currentRow()
        
        if row >= 0:
            # If in Master DB, ID is in col 0. If in Schedule, get from adk_tools logic
            if current_tab == 1:
                task_id = active_table.item(row, 0).text()
            else:
                res = adk_tools.generate_optimized_schedule()
                task_id = res.get('scheduled')[row].get('id')
                
            main_cli.handle_delete_task(str(task_id))
            self.load_data()
        else:
            self.status_lbl.setText("STATUS: SELECT A TASK FIRST")

    def wipe_system(self):
        """Command 7: Clear Database"""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, 'Wipe Database', 
                                   "DANGER: Delete ALL tasks?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            db.clear_all_tasks()
            self.load_data()
            self.status_lbl.setText("SYSTEM STATUS: DATABASE WIPED")

    def center_on_screen(self):
        """Calculates monitor geometry to launch the app in the center."""
        frame_gm = self.frameGeometry()
        screen = QApplication.primaryScreen().availableGeometry().center()
        frame_gm.moveCenter(screen)
        self.move(frame_gm.topLeft())

    def apply_global_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1b26; }
            QFrame#headerFrame { background-color: #24283b; border-bottom: 2px solid #414868; max-height: 60px; }
            QLabel#statusLabel { color: #7aa2f7; font-size: 18px; font-weight: bold; font-family: 'Consolas'; }
            QTableWidget { 
                background-color: #1a1b26; color: #c0caf5; gridline-color: #414868; 
                border: none; selection-background-color: #33467c; 
            }
            QHeaderView::section { background-color: #24283b; color: #bb9af7; padding: 8px; border: 1px solid #414868; }
            QPushButton { background-color: #414868; color: white; padding: 12px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #7aa2f7; }
        """)

    # Inside BrotherGUI in main_tui.py
    def open_add_dialog(self):
        dialog = AddTaskDialog(self)
        if dialog.exec():
            d = dialog.get_data()
            cmd_str = f"{d['name']}\t{d['date']}\t{d['dur']}\t{d['prio']}\t{d['fixed']}"
            main_cli.handle_add_task(cmd_str)
            
            # CRITICAL: Re-run the optimization algorithm to include the new task
            self.load_daily_schedule() 
            self.load_master_db()

    def run_voice_agent(self):
        """Starts the background thread for voice processing."""
        self.btn_mic.setEnabled(False)
        self.worker = AIWorker()
        self.worker.status_update.connect(lambda s: self.status_lbl.setText(f"AGENT STATUS: {s}"))
        self.worker.finished.connect(self.on_agent_finished)
        self.worker.start()

    def on_agent_finished(self):
        self.btn_mic.setEnabled(True)
        self.status_lbl.setText("SYSTEM STATUS: OPTIMAL")
        self.load_data()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BrotherGUI()
    window.show()
    sys.exit(app.exec())