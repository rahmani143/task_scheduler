# Brother — Local Throughput Assistant

Overview
- Local assistant that stores tasks in SQLite, uses Gemini ADK (Gemini 1.5 Flash) for higher-level parsing, and Whisper Base for local STT.

Files
- `db.py`: SQLite helpers and schema.
- `adk_tools.py`: ADK configuration, system instruction, and the callable tool functions: `add_task`, `delete_task`, `generate_optimized_schedule`.
- `listener.py`: Hotkey listener (Ctrl+Shift+F), records 5–7s, transcribes locally with Whisper, and routes commands to ADK/tools.
- `morning_brief.py`: Fetches today's tasks, runs throughput algorithm, and shows a system notification with top 3 tasks.
- `requirements.txt`: Python dependencies.

Setup
1. Create a venv and install packages:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Set Google ADK / Gemini key if you plan to use the ADK client (optional):

Windows PowerShell:

```powershell
$env:GOOGLE_API_KEY = "YOUR_KEY"
```

Notes
- The code includes a local fallback parser so basic voice commands ("add task ...", "delete task <id>") work without Gemini.
- For robust natural-language date parsing the code uses `dateparser`.
- To register the morning brief to run on unlock, see `scheduler_setup.ps1` for a PowerShell snippet to register a Task Scheduler job.

Questions
- At 6 AM, would you prefer a Voice Summary (TTS) or a Dashboard (terminal popup)?
- Do you want me to refine the throughput algorithm further now?
