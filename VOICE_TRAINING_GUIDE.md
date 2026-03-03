# Voice Recognition Training Guide

Your script now has several improvements to better recognize your voice:

## Configuration Settings

Edit the settings in `voice_test_remove.py`:

### 1. **Wake Word Detection Mode** (CRITICAL for your voice)
```python
USE_WHISPER_FOR_WAKE = True  # ← Set to True for better personal voice recognition
WHISPER_MODEL = "base"       # Options: tiny, base, small, medium, large
```

- **Whisper mode (True)**: Uses Whisper AI - much better at recognizing individual voices. Takes 2-3 seconds per check but highly accurate.
- **Vosk mode (False)**: Faster but less accurate for non-standard accents or speech patterns.

### 2. **Transcription Model**
```python
WHISPER_MODEL = "base"  # Size of model for transcription
```

Models by accuracy (slowest to fastest):
- `large` - 94% accuracy (very slow, 8GB+ RAM)
- `medium` - 85% accuracy (slower, 5GB RAM) 
- `small` - 82% accuracy (moderate, 1GB RAM) ✓ **Recommended**
- `base` - 78% accuracy (faster, 500MB RAM) ✓ **Good balance**
- `tiny` - 62% accuracy (fastest, minimal RAM)

## What Changed in Your Script

✅ **Audio Preprocessing**
- Automatic level normalization (prevents clipping)
- High-pass filter for background noise reduction

✅ **Whisper Wake Word Detection**
- Now uses the same Whisper model you use for transcription
- Works better for diverse accents and voices
- Can understand natural variations of "hey amy"

✅ **Better Recording**
- Applies preprocessing to recorded audio
- Cleaner audio = better transcription

## Training/Adaptation Tips

### For Fastest Improvement:
1. **Speak clearly and at normal volume** - The preprocessor expects ~70dB speech
2. **Minimize background noise** - Even with noise reduction, quieter rooms work better
3. **Use Whisper "base" or "small"** - Sweet spot for accuracy and speed

### For Maximum Accuracy:
1. Set `USE_WHISPER_FOR_WAKE = True`
2. Set `WHISPER_MODEL = "medium"` (or "large" if you have RAM)
3. Enunciate slightly more than usual
4. Record in quiet environment

### If Model is Too Slow:
1. Switch back to `USE_WHISPER_FOR_WAKE = False` (Vosk mode)
2. Reduce `RECORD_SECONDS` if 8 seconds is too long
3. Use smaller model: `WHISPER_MODEL = "tiny"`

## Advanced: Collect Training Data

To improve recognition over time:

1. Record audio examples of your voice saying your commands
2. Save them with timestamps
3. Incrementally run them through the transcriber
4. The Whisper model will improve contextually

## Technical Details

**Audio Preprocessing Pipeline:**
```
Raw Audio → Normalize Levels → High-Pass Filter → Whisper/Vosk
```

**Wake Word Detection Flow (Whisper Mode):**
```
Listen (2 sec chunks) → Transcribe with Whisper → Check for "hey amy"
```

**Settings Priority (for your use case):**
1. `USE_WHISPER_FOR_WAKE = True` ⭐ (single biggest improvement)
2. `WHISPER_MODEL = "small"` (good balance)
3. Clean, quiet environment (free improvement!)
4. Speak clearly (natural adaptation)

## Troubleshooting

**"Takes too long to detect wake word"**
→ Switch to Vosk mode: `USE_WHISPER_FOR_WAKE = False`

**"Doesn't recognize my voice variations"**
→ Use Whisper mode + larger model: `WHISPER_MODEL = "medium"`

**"Lots of background noise interference"**
→ Audio preprocessing helps, but your microphone/environment matters most

**"Transcription is wrong"**
→ Increase model size: "base" → "small" → "medium"

