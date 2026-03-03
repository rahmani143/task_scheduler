# # """
# # Wake word listener that continuously listens for "hey brother", records audio, 
# # transcribes with Whisper, and routes commands to ADK/tools.

# # Wake Word: "hey brother"
# # Uses Vosk for fast wake word detection and Kokoro for TTS.
# # """
# # import warnings
# # warnings.filterwarnings('ignore', category=FutureWarning)
# # warnings.filterwarnings('ignore', category=UserWarning)

# # import queue
# # import sounddevice as sd
# # import vosk
# # import json
# # import wave
# # import whisper
# # import numpy as np
# # import os
# # import tempfile
# # import adk_tools
# # import db
# # import dateparser
# # import re
# # from kokoro import KPipeline
# # import time

# # # ----------------------------
# # # Settings
# # # ----------------------------
# # MODEL_PATH = "vosk-model-en-us-0.42-gigaspeech"
# # WAKE_WORD = "hey brother"
# # OUTPUT_FILENAME = "Recorded.wav"
# # RECORD_SECONDS = 8
# # RATE = 16000
# # CHANNELS = 1
# # CHUNK = 1024
# # WHISPER_MODEL = "base"

# # # TTS Pipeline
# # repo_id = 'hexgrad/Kokoro-82M'
# # pipeline = KPipeline(lang_code='a', repo_id=repo_id)

# # # Models initialized once
# # vosk_model = vosk.Model(MODEL_PATH)
# # whisper_model = None
# # q = queue.Queue()

# # # ----------------------------
# # # Audio Processing Functions
# # # ----------------------------
# # def normalize_audio(data):
# #     """Normalize audio levels to prevent clipping"""
# #     data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
# #     # Get max amplitude
# #     max_val = np.abs(data).max()
# #     if max_val > 0:
# #         # Normalize to 90% of max range to prevent clipping
# #         data = (data / max_val) * (32767 * 0.9)
# #     return data.astype(np.int16).tobytes()

# # def reduce_noise(data):
# #     """Simple high-pass filter to reduce low-frequency noise"""
# #     data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
# #     # Simple high-pass filter (removes rumble)
# #     filtered = np.zeros_like(data)
# #     for i in range(2, len(data)):
# #         filtered[i] = 0.95 * (filtered[i-1] + data[i] - data[i-1])
# #     return filtered.astype(np.int16).tobytes()

# # def preprocess_audio(data):
# #     """Apply audio preprocessing: normalize + noise reduction"""
# #     data = normalize_audio(data)
# #     return reduce_noise(data)

# # # Audio callback function
# # def audio_callback(indata, frames, time, status):
# #     """Collect microphone input in queue for Vosk processing"""
# #     if status:
# #         print(status)
# #     q.put(bytes(indata))

# # # ----------------------------
# # # Wake word listener
# # # ----------------------------
# # def listen_for_wake_word():
# #     """Continuously listens until the wake word is detected"""
# #     try:
# #         recognizer = vosk.KaldiRecognizer(vosk_model, RATE)
# #         recognizer.SetWords(["hey", "brother"])

# #         with sd.RawInputStream(samplerate=RATE, blocksize=8000, dtype='int16', channels=1, callback=audio_callback):
# #             print("🎤 Listening for wake word... Say 'hey brother'")

# #             while True:
# #                 data = q.get()
# #                 # Preprocess audio for better recognition
# #                 data = preprocess_audio(data)
                
# #                 if recognizer.AcceptWaveform(data):
# #                     result = json.loads(recognizer.Result())
# #                     text = result.get("text", "").lower()
                    
# #                     # Only match on confident final results
# #                     if text and len(text) > 2:
# #                         has_hey = "hey" in text
# #                         has_wake = "brother" in text
                        
# #                         if has_hey or has_wake:
# #                             print("\n✓ Wake word detected!")
# #                             speak("I am up.")
# #                             return True
# #     except Exception as e:
# #         print(f'⚠ Wake word listener error: {e}')
# #         return False

# # # ----------------------------
# # # Recording with end-of-speech detection
# # # ----------------------------
# # def record_audio(output_filename=OUTPUT_FILENAME, silence_duration: float = 2.0, max_duration: float = 60.0):
# #     """Record audio until `silence_duration` seconds of silence after speech.

# #     - Uses a simple RMS-based VAD on 16-bit PCM chunks.
# #     - `max_duration` prevents runaway recording.
# #     - Writes a WAV file to `output_filename`.
# #     """
# #     print(f"🎙️ Recording (waiting for end of speech: {silence_duration}s)...")

# #     p = sd.RawInputStream(samplerate=RATE, blocksize=CHUNK, dtype='int16', channels=CHANNELS)
# #     frames = []

# #     rms_threshold = 500.0
# #     silence_time = 0.0
# #     spoke = False
# #     start_time = time.time()

# #     try:
# #         with p:
# #             while True:
# #                 if time.time() - start_time > max_duration:
# #                     break

# #                 chunk, _ = p.read(CHUNK)
# #                 # Preprocess: normalize and reduce noise
# #                 proc = preprocess_audio(chunk)
# #                 frames.append(proc)

# #                 # compute RMS on raw chunk (before preprocessing for stability)
# #                 arr = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
# #                 rms = float(np.sqrt(np.mean(arr * arr))) if arr.size else 0.0

# #                 if rms > rms_threshold:
# #                     spoke = True
# #                     silence_time = 0.0
# #                 else:
# #                     if spoke:
# #                         silence_time += CHUNK / float(RATE)
# #                         if silence_time >= silence_duration:
# #                             break
# #                     else:
# #                         # haven't started speaking yet; keep listening
# #                         pass

# #         # Save WAV file
# #         wf = wave.open(output_filename, 'wb')
# #         wf.setnchannels(CHANNELS)
# #         wf.setsampwidth(2)  # 16-bit PCM = 2 bytes
# #         wf.setframerate(RATE)
# #         wf.writeframes(b''.join(frames))
# #         wf.close()

# #         print(f'✅ Saved recording to {output_filename}')
# #     except Exception as e:
# #         print(f'⚠ Recording error: {e}')

# # # ----------------------------
# # # Transcription
# # # ----------------------------
# # def transcribe_audio(filename, model_name=None):
# #     """Transcribe audio file with Whisper"""
# #     global whisper_model
# #     if model_name is None:
# #         model_name = WHISPER_MODEL
    
# #     try:
# #         print(f"🔄 Transcribing with {model_name} model...")
# #         speak("Processing your request.")
        
# #         if whisper_model is None:
# #             whisper_model = whisper.load_model(model_name)
        
# #         result = whisper_model.transcribe(filename, language='en', fp16=False)
# #         return result["text"]
# #     except Exception as e:
# #         print(f'⚠ Transcription error: {e}')
# #         return ""

# # # ----------------------------
# # # Text-to-Speech
# # # ----------------------------
# # def speak(text):
# #     """Convert text to speech using Kokoro"""
# #     try:
# #         generator = pipeline(text, voice='af_heart')
        
# #         # Play each chunk
# #         for i, (gs, ps, audio) in enumerate(generator):
# #             sd.play(audio, samplerate=24000)
# #             sd.wait()
# #     except Exception as e:
# #         print(f'⚠ TTS Error: {e}')


# # # ----------------------------
# # # Command Processing
# # # ----------------------------
# # def process_command(text: str):
# #     """Process transcribed voice command"""
# #     text = text.lower().strip()
# #     print('📝 Transcribed:', text)
    
# #     # Guard: if empty transcription, ask user
# #     if not text:
# #         msg = '⚠ Did you want to say something?'
# #         print(msg)
# #         speak(msg)
# #         return
    
# #     # Simple local parser
# #     # Detect intent to add/schedule a task more broadly (covers "I'll do a task...", "remind me to...", etc.)
# #     add_intent = False
# #     if re.search(r'\b(add task|add|remind me to|remind|schedule|task|todo)\b', text):
# #         # exclude phrases that are clearly other commands
# #         if not any(k in text for k in ('show schedule', 'delete', 'morning brief', 'brief')):
# #             add_intent = True

# #     if add_intent:
# #         # Begin single-agent drafting interview
# #         raw_name = text
# #         # try to strip common verbs/phrases
# #         raw_name = re.sub(r"^(i(?:'ll| will)?(?: do)?|remind me to|please|i want to|i'll)", '', raw_name, flags=re.I).strip()
# #         # if 'for' appears, split off time/target
# #         if ' for ' in raw_name:
# #             parts = raw_name.split(' for ', 1)
# #             candidate = parts[0].strip()
# #         else:
# #             candidate = raw_name

# #         # if candidate is too short or still looks like a verb phrase, treat as missing name
# #         if len(candidate) < 3 or candidate.lower().startswith(('tonight', 'today', 'tomorrow', 'at', "i'll", 'i am')):
# #             name = None
# #         else:
# #             name = re.sub(r' priority .*', '', candidate)
# #             name = re.sub(r' deadline .*', '', name)

# #         # pre-fill provided fields if present in speech
# #         provided = {}
# #         m = re.search(r'priority (\d)', text)
# #         if m:
# #             provided['priority'] = int(m.group(1))
# #         m = re.search(r'duration (\d+)', text)
# #         if m:
# #             provided['duration_mins'] = int(m.group(1))
# #         m = re.search(r'(\d{1,2}:\d{2})', text)
# #         if m:
# #             provided['due_time'] = m.group(1)
# #         m = re.search(r'deadline (.+)$', text)
# #         if m:
# #             parsed = dateparser.parse(m.group(1))
# #             if parsed:
# #                 provided['due_date'] = parsed.date().isoformat()

# #         # if name is present, allow provided override
# #         if name:
# #             provided['task_name'] = name.strip().capitalize()

# #         # run interview flow
# #         draft_resp = adk_tools.interview_task_draft(name.strip().capitalize(), provided)
# #         while not draft_resp.get('ok'):
# #             missing = draft_resp.get('missing', [])
# #             q = draft_resp.get('next_question', 'Can you provide more details?')
# #             print('Question:', q)
# #             speak(q)
# #             # record short answer (VAD: stop after 2s silence)
# #             record_audio(silence_duration=2.0, max_duration=20.0)
# #             ans = transcribe_audio(OUTPUT_FILENAME)
# #             print('Answer:', ans)

# #             # map answer to the missing field
# #             if not ans:
# #                 speak('I did not get that. Please repeat.')
# #                 draft_resp = adk_tools.interview_task_draft(name.strip().capitalize(), provided)
# #                 continue

# #             for field in missing:
# #                 if field == 'due_date':
# #                     parsed = dateparser.parse(ans)
# #                     if parsed:
# #                         provided['due_date'] = parsed.date().isoformat()
# #                         # try to extract time if present
# #                         if parsed.time() and parsed.time().hour != 0:
# #                             provided['due_time'] = parsed.time().strftime('%H:%M')
# #                 elif field == 'duration_mins':
# #                     m2 = re.search(r'(\d+)', ans)
# #                     if m2:
# #                         provided['duration_mins'] = int(m2.group(1))
# #                 elif field == 'priority':
# #                     m2 = re.search(r'([123])', ans)
# #                     if m2:
# #                         provided['priority'] = int(m2.group(1))
# #                 elif field == 'task_name':
# #                     provided['task_name'] = ans.strip().capitalize()

# #             draft_resp = adk_tools.interview_task_draft(name.strip().capitalize(), provided)

# #         # draft_resp contains the drafted task
# #         task = draft_resp.get('task')

# #         # attempt to schedule with conflict resolution
# #         res = adk_tools.manage_schedule_conflict(task)
# #         if not res.get('ok') and res.get('ask_user'):
# #             # ask user for permission to move fixed tasks
# #             conflicts = res.get('conflicts', [])
# #             names = ', '.join([c.get('task_name') for c in conflicts])
# #             speak(res.get('message'))
# #             speak('Do you want me to move these fixed tasks to make room? Say yes or no.')
# #             # record user response (VAD: stop after 2s silence)
# #             record_audio(silence_duration=2.0, max_duration=20.0)
# #             ans = transcribe_audio(OUTPUT_FILENAME)
# #             if ans and ans.lower().strip() in ('yes', 'y', 'yeah', 'sure', 'ok'):
# #                 res2 = adk_tools.manage_schedule_conflict(task, force_move_fixed=True)
# #                 if res2.get('ok'):
# #                     speak(res2.get('message'))
# #                 else:
# #                     speak('I could not schedule the task. ' + res2.get('message',''))
# #             else:
# #                 speak('Okay. I will not move fixed tasks. Task not scheduled.')
# #         elif res.get('ok'):
# #             speak(res.get('message'))
# #         else:
# #             speak('I could not schedule the task: ' + res.get('message',''))

# #         # ensure cleanup of recorded file
# #         try:
# #             if os.path.exists(OUTPUT_FILENAME):
# #                 os.remove(OUTPUT_FILENAME)
# #         except Exception:
# #             pass

# #         return
    
# #     if 'delete task' in text or text.startswith('delete '):
# #         m = re.search(r'(?:delete task|delete) (\d+)', text)
# #         if m:
# #             ok = adk_tools.delete_task(int(m.group(1)))
# #             msg = f'✓ Deleted task {m.group(1)}'
# #             print(msg)
# #             speak(f'Deleted task {m.group(1)}.')
# #             return
    
# #     if 'show schedule' in text or 'schedule' in text:
# #         out = adk_tools.generate_optimized_schedule()
# #         print('📅 Schedule:')
# #         for item in out.get('scheduled', []):
# #             print(f"  - {item['task_name']} @ {item['start']}")
# #         speak('Here is your schedule for today.')
# #         return
    
# #     if 'morning brief' in text or 'brief' in text:
# #         schedule = adk_tools.generate_ramadan_schedule()
# #         speech = adk_tools.format_assistant_speech(schedule)
# #         print(speech)
# #         speak(speech)
# #         return
    
# #     # Otherwise: hand off to conversational agent for chat
# #     print('💬 No local command matched; forwarding to conversational agent...')
# #     # maintain a short ephemeral conversation history stored locally in this function's attribute
# #     if not hasattr(process_command, 'history'):
# #         process_command.history = []

# #     # append user message
# #     process_command.history.append({"role": "user", "content": text})

# #     # ask agent
# #     reply = adk_tools.ask_agent(text, history=process_command.history[-6:])
# #     # append assistant reply to history
# #     process_command.history.append({"role": "assistant", "content": reply})

# #     print('🤖 Agent reply:', reply)
# #     speak(reply)

# # # ----------------------------
# # # Main Loop
# # # ----------------------------
# # if __name__ == "__main__":
# #     db.init_db()
# #     print('🎤 Brother is starting...')
    
# #     try:
# #         while True:
# #             if listen_for_wake_word():           # Wait for "hey brother"
# #                 record_audio()                   # Record N seconds
# #                 text = transcribe_audio(OUTPUT_FILENAME)
                
# #                 if text:
# #                     print("✓ Transcription:", text)
# #                     process_command(text)
# #                 else:
# #                     speak("I did not catch that. Please try again.")
                
# #                 # Clean up temp file
# #                 if os.path.exists(OUTPUT_FILENAME):
# #                     os.remove(OUTPUT_FILENAME)
                
# #                 print('\n' + '='*50)
                
# #     except KeyboardInterrupt:
# #         print('\n👋 Brother is shutting down.')
# #     except Exception as e:
# #         print(f'❌ Error: {e}')
# #         import traceback
# #         traceback.print_exc()













# # edit 1:





# """
# Optimized Wake word listener for Agentic AI Workflows.
# Uses Vosk for wake word, Faster-Whisper for high-speed transcription, and Kokoro for TTS.
# """
# import warnings
# warnings.filterwarnings('ignore', category=FutureWarning)
# warnings.filterwarnings('ignore', category=UserWarning)

# import queue
# import sounddevice as sd
# import vosk
# import json
# import wave
# import numpy as np
# import os
# import time
# import re
# import dateparser

# # Modular imports
# import adk_tools
# import db
# from faster_whisper import WhisperModel  # Switch to high-performance engine
# from kokoro import KPipeline

# os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
# os.environ["USE_CPU_ONLY"] = "1"

# # ----------------------------
# # Settings & Global State
# # ----------------------------
# MODEL_PATH = "vosk-model-en-us-0.42-gigaspeech"
# WAKE_WORD = "hey brother"
# OUTPUT_FILENAME = "Recorded.wav"
# RATE = 16000
# CHANNELS = 1
# CHUNK = 1024

# # Global model caches (Singletons)
# _whisper_model = None
# _kokoro_pipeline = None
# vosk_model = vosk.Model(MODEL_PATH)
# q = queue.Queue()

# # ----------------------------
# # Singleton Getters (Engineered for Speed)
# # ----------------------------

# def get_tts():
#     global _kokoro_pipeline
#     if _kokoro_pipeline is None:
#         _kokoro_pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
#     return _kokoro_pipeline

# # ----------------------------
# # Audio Utilities
# # ----------------------------
# def preprocess_audio(data):
#     """Normalize and high-pass filter to help the Agent 'hear' better."""
#     arr = np.frombuffer(data, dtype=np.int16).astype(np.float32)
#     max_val = np.abs(arr).max()
#     if max_val > 0:
#         arr = (arr / max_val) * (32767 * 0.9)
#     # Simple High-pass filter
#     filtered = np.zeros_like(arr)
#     for i in range(2, len(arr)):
#         filtered[i] = 0.95 * (filtered[i-1] + arr[i] - arr[i-1])
#     return filtered.astype(np.int16).tobytes()

# def audio_callback(indata, frames, time, status):
#     if status: print(status)
#     q.put(bytes(indata))

# # ----------------------------
# # Core Agentic ear functions
# # ----------------------------
# def speak(text):
#     """Convert text to speech using Kokoro."""
#     try:
#         pipeline = get_tts()
#         generator = pipeline(text, voice='af_heart')
#         for i, (gs, ps, audio) in enumerate(generator):
#             sd.play(audio, samplerate=24000)
#             sd.wait()
#     except Exception as e:
#         print(f'⚠ TTS Error: {e}')

# def listen_for_wake_word():
#     """Vosk-based wake word detection."""
#     try:
#         recognizer = vosk.KaldiRecognizer(vosk_model, RATE)
#         recognizer.SetWords(["hey", "brother"])
#         with sd.RawInputStream(samplerate=RATE, blocksize=8000, dtype='int16', channels=1, callback=audio_callback):
#             print("🎤 Listening for wake word...")
#             while True:
#                 data = q.get()
#                 if recognizer.AcceptWaveform(preprocess_audio(data)):
#                     result = json.loads(recognizer.Result())
#                     text = result.get("text", "").lower()
#                     if "hey" in text or "brother" in text:
#                         print("\n✓ Wake word detected!")
#                         speak("I am up.")
#                         return True
#     except Exception as e:
#         print(f'⚠ Wake word error: {e}'); return False

# def record_audio(output_filename=OUTPUT_FILENAME, silence_duration=2.0, max_duration=60.0):
#     """VAD-aware recording."""
#     print("🎙️ Listening...")
#     frames = []
#     rms_threshold = 500.0
#     silence_time = 0.0
#     spoke = False
#     start_time = time.time()

#     with sd.RawInputStream(samplerate=RATE, blocksize=CHUNK, dtype='int16', channels=CHANNELS) as stream:
#         while time.time() - start_time < max_duration:
#             chunk, _ = stream.read(CHUNK)
#             proc = preprocess_audio(chunk)
#             frames.append(proc)
            
#             arr = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
#             rms = float(np.sqrt(np.mean(arr * arr))) if arr.size else 0.0
            
#             if rms > rms_threshold:
#                 spoke = True
#                 silence_time = 0.0
#             elif spoke:
#                 silence_time += CHUNK / RATE
#                 if silence_time >= silence_duration: break

#     with wave.open(output_filename, 'wb') as wf:
#         wf.setnchannels(CHANNELS)
#         wf.setsampwidth(2)
#         wf.setframerate(RATE)
#         wf.writeframes(b''.join(frames))

# from whisper_cpp_python import Whisper

# _whisper_cache = None

# def get_whisper():
#     global _whisper_cache
#     if _whisper_cache is None:
#         # This loads the GGUF model format (same as Llama.cpp)
#         # It's pure C++ and won't trigger the DLL error
#         _whisper_cache = Whisper(model_path="path/to/ggml-base.bin") 
#     return _whisper_cache

# def transcribe_audio(filename):
#     print("🔄 C++ Inference Engine Transcribing...")
#     model = get_whisper()
#     result = model.transcribe(filename)
#     return result["text"].strip()

# # ----------------------------
# # Logic Bridge
# # ----------------------------
# def process_command(text: str):
#     """Refactored to route to ADK tools."""
#     text = text.lower().strip()
#     print('📝 Agent Received:', text)
    
#     if not text:
#         speak("I didn't catch that.")
#         return

#     # Logic for scheduling, deleting, or chatting (Keep your existing process_command logic here)
#     # ... (Your logic for add_intent, delete, etc.)
#     # For brevity, I'm assuming the rest of your logic remains identical
    
#     # NEW: Forward to conversational agent if no local match
#     if 'show schedule' not in text and 'add' not in text:
#         reply = adk_tools.ask_agent(text)
#         speak(reply)

# if __name__ == "__main__":
#     db.init_db()
#     print('🤖 Brother AI Agent is active.')
#     while True:
#         if listen_for_wake_word():
#             record_audio()
#             command = transcribe_audio(OUTPUT_FILENAME)
#             if command:
#                 process_command(command)
#             if os.path.exists(OUTPUT_FILENAME):
#                 os.remove(OUTPUT_FILENAME)







"""
Optimized Wake word listener for Agentic AI Workflows.
Fully Integrated: Vosk (Wake), Faster-Whisper (ASR), Kokoro (TTS), and ADK Task Logic.
"""
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings("ignore", message=".*EspeakWrapper.*")

import queue
import sounddevice as sd
import vosk
import json
import wave
import numpy as np
import os
import time
import re
import dateparser

# Modular imports
import adk_tools
import db
from faster_whisper import WhisperModel
from kokoro import KPipeline

# Force CPU to avoid the WinError 1114 DLL crash
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# ----------------------------
# Settings & Global State
# ----------------------------
MODEL_PATH = "vosk-model-en-us-0.42-gigaspeech"
WAKE_WORD = "hey brother"
OUTPUT_FILENAME = "Recorded.wav"
RATE = 16000
CHANNELS = 1
CHUNK = 1024

# Global model caches (Singletons)
_whisper_model = None
_kokoro_pipeline = None
vosk_model = vosk.Model(MODEL_PATH)
q = queue.Queue()

# ----------------------------
# Singleton Getters
# ----------------------------
def get_tts():
    global _kokoro_pipeline
    if _kokoro_pipeline is None:
        _kokoro_pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
    return _kokoro_pipeline

def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        print("🚀 Loading 'Small' Model for better accent support...")
        # 'small' is the sweet spot for NITW hostel WiFi/speed
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    return _whisper_model

# ----------------------------
# Audio Utilities
# ----------------------------
def preprocess_audio(data):
    arr = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    max_val = np.abs(arr).max()
    if max_val > 0:
        arr = (arr / max_val) * (32767 * 0.9)
    filtered = np.zeros_like(arr)
    for i in range(2, len(arr)):
        filtered[i] = 0.95 * (filtered[i-1] + arr[i] - arr[i-1])
    return filtered.astype(np.int16).tobytes()

def audio_callback(indata, frames, time, status):
    if status: print(status)
    q.put(bytes(indata))

# ----------------------------
# Core Ear Functions
# ----------------------------
def speak(text):
    try:
        pipeline = get_tts()
        generator = pipeline(text, voice='af_heart')
        for i, (gs, ps, audio) in enumerate(generator):
            sd.play(audio, samplerate=24000)
            sd.wait()
    except Exception as e:
        print(f'⚠ TTS Error: {e}')

def listen_for_wake_word():
    try:
        recognizer = vosk.KaldiRecognizer(vosk_model, RATE)
        recognizer.SetWords(["hey", "brother"])
        with sd.RawInputStream(samplerate=RATE, blocksize=8000, dtype='int16', channels=1, callback=audio_callback):
            print("🎤 Listening for 'hey brother'...")
            while True:
                data = q.get()
                if recognizer.AcceptWaveform(preprocess_audio(data)):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").lower()
                    if "hey" in text or "brother" in text:
                        print("\n✓ Wake word detected!")
                        speak("I am up.")
                        return True
    except Exception as e:
        print(f'⚠ Wake word error: {e}'); return False

def record_audio(output_filename=OUTPUT_FILENAME, silence_duration=2.0, max_duration=60.0):
    print("🎙️ Listening...")
    frames = []
    rms_threshold = 500.0
    silence_time = 0.0
    spoke = False
    start_time = time.time()

    with sd.RawInputStream(samplerate=RATE, blocksize=CHUNK, dtype='int16', channels=CHANNELS) as stream:
        while time.time() - start_time < max_duration:
            chunk, _ = stream.read(CHUNK)
            proc = preprocess_audio(chunk)
            frames.append(proc)
            
            arr = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
            rms = float(np.sqrt(np.mean(arr * arr))) if arr.size else 0.0
            
            if rms > rms_threshold:
                spoke = True
                silence_time = 0.0
            elif spoke:
                silence_time += CHUNK / RATE
                if silence_time >= silence_duration: break

    with wave.open(output_filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

def transcribe_audio(filename):
    model = get_whisper()
    # Adding a prompt helps the AI resolve your accent
    prompt = "Ibrahim, NIT Warangal, Hanamkonda, B-Tech, ECE, VLSI, SDE, WhatsApp."
    
    segments, _ = model.transcribe(
        filename, 
        beam_size=5, 
        language="en", 
        initial_prompt=prompt
    )
    return " ".join([s.text for s in segments]).strip()

# ----------------------------
# Logic Bridge (RESTORED FULL LOGIC)
# ----------------------------
def process_command(text: str):
    text = text.lower().strip()
    print('📝 Transcribed:', text)
    
    if not text:
        speak('Did you want to say something?')
        return
    
    # 1. DELETE TASK
    if 'delete task' in text or text.startswith('delete '):
        m = re.search(r'(?:delete task|delete) (\d+)', text)
        if m:
            adk_tools.delete_task(int(m.group(1)))
            speak(f'Deleted task {m.group(1)}.')
            return

    # 2. SHOW SCHEDULE / MORNING BRIEF
    if any(k in text for k in ('show schedule', 'morning brief', 'brief')):
        if 'brief' in text:
            schedule = adk_tools.generate_ramadan_schedule()
            speech = adk_tools.format_assistant_speech(schedule)
            speak(speech)
        else:
            adk_tools.generate_optimized_schedule()
            speak('Here is your schedule for today.')
        return

    # 3. ADD / SCHEDULE TASK (The Interview Flow)
    add_intent = False
    if re.search(r'\b(add task|add|remind me to|remind|schedule|task|todo)\b', text):
        add_intent = True

    if add_intent:
        raw_name = re.sub(r"^(i(?:'ll| will)?(?: do)?|remind me to|please|i want to|i'll)", '', text, flags=re.I).strip()
        candidate = raw_name.split(' for ', 1)[0].strip() if ' for ' in raw_name else raw_name
        
        name = candidate if len(candidate) >= 3 else None
        provided = {}
        
        # Regex extraction
        m = re.search(r'priority (\d)', text)
        if m: provided['priority'] = int(m.group(1))
        m = re.search(r'duration (\d+)', text)
        if m: provided['duration_mins'] = int(m.group(1))
        m = re.search(r'(\d{1,2}:\d{2})', text)
        if m: provided['due_time'] = m.group(1)

        # Interview Loop
        # Interview Loop
        draft_resp = adk_tools.interview_task_draft(name.capitalize() if name else "", provided)
        while not draft_resp.get('ok'):
            q_text = draft_resp.get('next_question', 'Details?')
            speak(q_text)
            record_audio(silence_duration=2.0)
            ans = transcribe_audio(OUTPUT_FILENAME).lower().strip()
            print(f"DEBUG: User answered: '{ans}' to question: '{q_text}'")

            # 1. Handle Date/Time
            if 'due' in q_text or 'date' in q_text:
                parsed = dateparser.parse(ans)
                if parsed:
                    provided['due_date'] = parsed.date().isoformat()
                    if parsed.time() and parsed.time().hour != 0:
                        provided['due_time'] = parsed.time().strftime('%H:%M')

            # 2. Handle Duration
            elif 'long' in q_text or 'duration' in q_text:
                # Extracts "30" from "30 minutes" or "half an hour" logic could go here
                m2 = re.search(r'(\d+)', ans)
                if m2:
                    provided['duration_mins'] = int(m2.group(1))

            # 3. Handle Priority (THIS WAS MISSING)
            elif 'priority' in q_text:
                priority_map = {"one": 1, "two": 2, "three": 3, "high": 1, "medium": 2, "low": 3}
                # Check for digit 1-3
                m2 = re.search(r'([1-3])', ans)
                if m2:
                    provided['priority'] = int(m2.group(1))
                else:
                    # Check for words like "two" or "medium"
                    for word, val in priority_map.items():
                        if word in ans:
                            provided['priority'] = val
                            break

            # 4. Handle Task Name (If it was missed initially)
            elif 'name' in q_text or 'called' in q_text:
                if len(ans) > 2:
                    provided['task_name'] = ans.capitalize()
                    name = ans # Update local name variable too

            # Re-check with the updated 'provided' dict
            draft_resp = adk_tools.interview_task_draft(name.capitalize() if name else "", provided)

        # Conflict Resolution
        res = adk_tools.manage_schedule_conflict(draft_resp.get('task'))
        if not res.get('ok') and res.get('ask_user'):
            speak(res.get('message') + " Should I move fixed tasks?")
            record_audio(silence_duration=2.0)
            ans = transcribe_audio(OUTPUT_FILENAME)
            if ans.lower() in ('yes', 'yeah', 'sure', 'ok'):
                res = adk_tools.manage_schedule_conflict(draft_resp.get('task'), force_move_fixed=True)
        
        speak(res.get('message'))
        return

    # 4. CONVERSATIONAL FALLBACK
    print('💬 Forwarding to LLM Agent...')
    if not hasattr(process_command, 'history'): process_command.history = []
    process_command.history.append({"role": "user", "content": text})
    reply = adk_tools.ask_agent(text, history=process_command.history[-6:])
    process_command.history.append({"role": "assistant", "content": reply})
    speak(reply)

# ----------------------------
# Main Loop
# ----------------------------
if __name__ == "__main__":
    db.init_db()
    print('🤖 Brother AI Agent is active.')
    try:
        while True:
            if listen_for_wake_word():
                record_audio()
                cmd = transcribe_audio(OUTPUT_FILENAME)
                if cmd:
                    process_command(cmd)
                if os.path.exists(OUTPUT_FILENAME):
                    os.remove(OUTPUT_FILENAME)
                print('\n' + '='*50)
    except KeyboardInterrupt:
        print('\n👋 Shutting down.')