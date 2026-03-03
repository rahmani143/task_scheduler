"""
TTS module with support for Kokoro ONNX models and fallback engines.

Usage:
 - Place `kokoro-v1.0.onnx` and `voices-v1.0.bin` in the project folder, or pass full paths to `speak_kokoro()`.
 - If the Kokoro CLI (`kokoro-onnx` or `kokoro`) is available, this module will try to use it.
 - If not, it attempts to import a Python kokoro package. If that also fails, it falls back to `pyttsx3` (offline) if installed.

Note: Exact Kokoro Python API varies by distribution. This module uses a conservative CLI-first approach
and provides informative messages when a backend is unavailable.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
import sys
from typing import Optional


def _play_wav(path: str) -> None:
    """Play a .wav on Windows using PowerShell Media player (blocking)."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    cmd = [
        'powershell', '-NoProfile', '-Command',
        f"(New-Object Media.SoundPlayer '{path}').PlaySync()"
    ]
    subprocess.run(cmd, check=False)


def speak_kokoro(text: str, model_path: str = 'kokoro-v1.0.onnx', voices_path: str = 'voices-v1.0.bin', out_path: Optional[str] = None, blocking: bool = True) -> Optional[str]:
    """
    Attempt to synthesize `text` using Kokoro ONNX model and voices binary.

    Returns path to generated wav on success, or None on failure.
    - Prefers kokoro CLI if available: `kokoro-onnx` or `kokoro` in PATH.
    - Then tries to import a Python kokoro package (best-effort).
    - Does not implement raw ONNX runtime inference here.
    """
    if out_path is None:
        fd, out_path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)

    # 1) Try kokoro CLI binary
    cli_names = ('kokoro-onnx', 'kokoro')
    for cli in cli_names:
        exe = shutil.which(cli)
        if exe:
            # Best-effort CLI invocation. CLI arg names may differ across versions.
            args = [exe, '--model', model_path, '--voices', voices_path, '--text', text, '--output', out_path]
            try:
                subprocess.run(args, check=True)
                if blocking:
                    _play_wav(out_path)
                return out_path
            except subprocess.CalledProcessError:
                # Try an alternate argument form (some CLIs use --out or -o)
                alt_args = [exe, '--model', model_path, '--voices', voices_path, '--text', text, '-o', out_path]
                try:
                    subprocess.run(alt_args, check=True)
                    if blocking:
                        _play_wav(out_path)
                    return out_path
                except subprocess.CalledProcessError:
                    continue

    # 2) Try Python kokoro package (best-effort; API may vary)
    try:
        import kokoro  # type: ignore
        # Hypothetical API: kokoro.Synthesizer(model_path, voices_path)
        try:
            synth = kokoro.Synthesizer(model_path=model_path, voices_path=voices_path)
            audio = synth.synthesize(text)
            # audio could be bytes or numpy array; try to write bytes
            if isinstance(audio, (bytes, bytearray)):
                with open(out_path, 'wb') as f:
                    f.write(audio)
            else:
                # Best-effort: attempt to save using soundfile if available
                try:
                    import soundfile as sf
                    sf.write(out_path, audio, 24000)
                except Exception:
                    with open(out_path, 'wb') as f:
                        f.write(audio.tobytes())
            if blocking:
                _play_wav(out_path)
            return out_path
        except Exception:
            pass
    except Exception:
        pass

    # 3) Fallback: pyttsx3 (offline)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        if blocking:
            engine.say(text)
            engine.runAndWait()
            return None
        else:
            def _bg_speak():
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception:
                    pass
            import threading
            threading.Thread(target=_bg_speak, daemon=True).start()
            return None
    except Exception:
        print('[TTS] No kokoro CLI/package found and pyttsx3 is not available.')
        print('Place kokoro-v1.0.onnx and voices-v1.0.bin in the project folder and install kokoro-onnx, or pip install pyttsx3.')
        return None


def speak(text: str, engine: str = 'kokoro', **kwargs):
    """Unified speak() that selects kokoro backend first, then falls back.

    engine: 'kokoro'|'pyttsx3'
    """
    if engine == 'kokoro':
        return speak_kokoro(text, **kwargs)
    if engine == 'pyttsx3':
        try:
            import pyttsx3
            eng = pyttsx3.init()
            eng.setProperty('rate', kwargs.get('rate', 150))
            eng.say(text)
            eng.runAndWait()
        except Exception as e:
            print(f'[TTS pyttsx3 error] {e}')
    else:
        print('[TTS] Unknown engine', engine)


if __name__ == '__main__':
    print('TTS module test — attempting kokoro then fallbacks')
    speak('Hello Ibrahim. This is Brother speaking using kokoro if available.', blocking=True)
