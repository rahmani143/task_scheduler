
# Brother: Agentic Task Manager

Brother is an intelligent, agentic task-management system designed for high-throughput productivity. It bridges the gap between structured database management and dynamic, voice-enabled interaction, ensuring you never miss a deadline while keeping your daily schedule optimized.

## 1. Core Philosophy: The Priority Waterfall

Brother operates on a rigid **Priority Waterfall** protocol. Your tasks are not just stored; they are simulated through an agentic lens to ensure your day remains manageable:

* **Priority 3 (Critical):** Takes absolute precedence in scheduling.
* **Priority 2 (Standard):** Fills available slots after P3.
* **Priority 1 (Maintenance/Low):** Automatically spilled over to the next day if the current schedule (06:00–22:00) reaches saturation.

## 2. Technical Stack

* **Language:** Python 3.8+
* **Database:** `sqlite3` with automated schema migration.
* **Interface:** `PyQt6` (GUI) and a CLI REPL.
* **AI/Agentic Layer:** Google Generative AI (Gemini 2.0 Flash) via the ADK.
* **Scheduling:** Custom greedy-allocation algorithm with duration-aware slotting.

## 3. Installation

Ensure you have `uv` or `pip` installed.

```bash
# Clone the repository
git clone <your-repo-url>
cd brother

# Install dependencies
pip install PyQt6 dateparser google-generativeai

# Configure your environment
export GOOGLE_API_KEY="your_api_key_here"

```

## 4. System Usage

### GUI Mode

The GUI provides a visual dashboard to manage your tasks.

* **Launch:** `python main_tui.py`
* **Features:** Tabbed views (Daily Schedule / Master Database), real-time notifications for task spillover, and integrated voice agent activation.

### CLI/Voice Mode

For power users, the CLI allows for rapid input and voice processing.

* **Launch:** `python main_cli.py`
* **Wake Word:** Say *"Hey Brother"* after activating voice mode to record commands.

## 5. Command Reference

| ID | Command | Description |
| --- | --- | --- |
| **0** | EXIT | Graceful shutdown. |
| **1** | ADD_TASK | Format: `Name <TAB> Date <TAB> Dur <TAB> Prio <TAB> Fixed` |
| **2** | DELETE_TASK | Remove task by ID with table preview. |
| **3** | SHOW_SCHEDULE | View daily optimized schedule. |
| **4** | MORNING_BRIEF | Agent-generated summary of pending tasks. |
| **5** | LIST_TASKS | View all tasks (sorted by priority). |
| **6** | MARK_COMPLETE | Mark a task as done (updates status). |
| **7** | WIPE DATABASE | Full system reset. |
| **8** | VIEW HISTORY | Query completed and missed tasks. |

## 6. Troubleshooting

* **DLL Load Errors (Windows):** The system force-disables CUDA (`os.environ["CUDA_VISIBLE_DEVICES"] = "-1"`) to prevent `c10.dll` initialization crashes. If you see WinError 1114, ensure your environment variables are correctly pointing to your Torch installation.
* **Safety Filters:** If the Agent blocks a request, it is due to strict safety thresholds. The system is configured to `BLOCK_NONE` for most categories to prevent interference with productivity commands.

