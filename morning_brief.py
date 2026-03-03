import adk_tools
import db
import testing.voice.tts as tts
from google import genai # Assuming you're using the new SDK for the brief

def run_brief():
    db.init_db()
    # 1. Fetch the raw optimized schedule
    schedule_data = adk_tools.generate_optimized_schedule()
    items = schedule_data.get('scheduled', [])
    
    if not items:
        msg = "You've got a clear slate today, Brother. No tasks scheduled."
        tts.speak(msg, engine='pyttsx3')
        return

    # 2. Format the data for Gemini to "narrate"
    # We send the raw JSON to Gemini so it can use its "intelligence" to brief us
    prompt = f"Here is my schedule for today: {items}. Give me a short, encouraging morning brief. Mention the top priority tasks and tell me why you've ordered them this way."
    
    # Simple one-shot call to get a conversational summary
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-1.5-flash", 
        contents=prompt
    )
    
    brief_text = response.text
    print(f"Brother's Brief: {brief_text}")

    # 3. Speak the Gemini-generated brief
    tts.speak(brief_text, engine='pyttsx3', blocking=True)

    # 4. Windows Notification (Keep your existing notification logic)
    try:
        from win10toast import ToastNotifier
        body = "\n".join([f"- {t['task_name']}" for t in items[:3]])
        ToastNotifier().show_toast('Brother — Morning Brief', body, duration=10)
    except:
        pass