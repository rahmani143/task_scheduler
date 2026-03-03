
import queue
import sounddevice as sd
import vosk
import json
import wave
import whisper
from kokoro import KPipeline
import numpy as np
#
import warnings
# Suppress specific categories
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ----------------------------
# Settings
# ----------------------------
MODEL_PATH = "vosk-model-en-us-0.42-gigaspeech"  # Path to vosk model folder (downloaded + unzipped)
WAKE_WORD = "hey brother"
OUTPUT_FILENAME = "Recorded.raw"
RECORD_SECONDS = 8
RATE = 16000
CHANNELS = 1
CHUNK = 1024
WHISPER_MODEL = "small"  # tiny, base, small, medium, large (larger = more accurate but slower)

# ----------------------------
# Audio Processing Functions
# ----------------------------
def normalize_audio(data):
    """Normalize audio levels to prevent clipping"""
    data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    # Get max amplitude
    max_val = np.abs(data).max()
    if max_val > 0:
        # Normalize to 90% of max range to prevent clipping
        data = (data / max_val) * (32767 * 0.9)
    return data.astype(np.int16).tobytes()

def reduce_noise(data):
    """Simple high-pass filter to reduce low-frequency noise"""
    data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    # Simple high-pass filter (removes rumble)
    filtered = np.zeros_like(data)
    for i in range(2, len(data)):
        filtered[i] = 0.95 * (filtered[i-1] + data[i] - data[i-1])
    return filtered.astype(np.int16).tobytes()

def preprocess_audio(data):
    """Apply audio preprocessing: normalize + noise reduction"""
    data = normalize_audio(data)
    return reduce_noise(data)

# ----------------------------
# Wake word listener
# ----------------------------
model = vosk.Model(MODEL_PATH)
repo_id='hexgrad/Kokoro-82M'
pipeline = KPipeline(lang_code='a', repo_id=repo_id)
q = queue.Queue()

# Audio callback function
def audio_callback(indata, frames, time, status):
    """Collect microphone input in queue for Vosk processing"""
    if status:
        print(status)
    q.put(bytes(indata))

# Listen for wake word function
def listen_for_wake_word():
    """Continuously listens until the wake word is detected"""
    return listen_for_wake_word_vosk()

def listen_for_wake_word_vosk():
    """Vosk-based wake word detection - fast and designed for wake words"""
    recognizer = vosk.KaldiRecognizer(model, RATE)
    recognizer.SetWords(["hey", "brother"])  # Tell vosk to focus on these words

    with sd.RawInputStream(samplerate=RATE, blocksize=8000, dtype='int16', channels=1, callback=audio_callback):
        print("Listening for wake word... Say 'hey brother'")

        while True:
            data = q.get()
            # Preprocess audio for better recognition
            data = preprocess_audio(data)
            
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()
                
                # Only print and match on confident final results
                if text and len(text) > 2:  # Ignore very short/empty results
                    # Check for wake word (must have either "hey" or "brother")
                    has_hey = "hey" in text
                    has_wake = "brother" in text
                    
                    if has_hey or has_wake:
                        print("\n✓ Wake word detected!")
                        speak("I am up.")
                        return True

# ----------------------------
# Recording function
# ----------------------------
def record_audio(output_filename=OUTPUT_FILENAME, record_seconds=RECORD_SECONDS):
    """Record audio for N seconds and save to WAV with preprocessing"""
    print(f"Recording for {record_seconds} seconds...")

    p = sd.RawInputStream(samplerate=RATE, blocksize=CHUNK, dtype='int16', channels=CHANNELS)
    frames = []

    with p:
        for _ in range(0, int(RATE / CHUNK * record_seconds)):
            chunk, _ = p.read(CHUNK)
            # Preprocess: normalize and reduce noise
            chunk = preprocess_audio(chunk)
            frames.append(chunk)

    # Save WAV file
    wf = wave.open(output_filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(2)  # 16-bit PCM = 2 bytes
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    #print(f"Saved recording to {output_filename}")

#transcribe the audios
def transcribe_audio(filename, model_name=None):
    if model_name is None:
        model_name = WHISPER_MODEL
    print(f"Transcribing with {model_name} model...")
    speak("Processing your request.")
    model = whisper.load_model(model_name)
    result = model.transcribe(filename, language='en', fp16=False)
    return result["text"]

#speak converted audio to text
def speak(text):
    generator = pipeline(text, voice='af_heart')

    # Play and save each chunk
    for i, (gs, ps, audio) in enumerate(generator):
        #print(f"Chunk {i}: Graphemes: {gs}, Phonemes: {ps}")
        
        # Play audio chunk
        sd.play(audio, samplerate=24000)
        sd.wait()  # Wait until this chunk finishes playings
# ----------------------------
# Main Loop
# ----------------------------
if __name__ == "__main__":
    while True:
        if listen_for_wake_word():   # Wait for "hey brother"
            record_audio()           # Record 5 seconds
            #print("You can now transcribe or process the audio...")
            text = transcribe_audio(OUTPUT_FILENAME)
            print("Transcription:", text)
            speak(text)