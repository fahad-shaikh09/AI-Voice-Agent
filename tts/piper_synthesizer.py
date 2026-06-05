import io
import wave
from functools import lru_cache
from pathlib import Path
from piper import PiperVoice
from config import PIPER_MODEL, PIPER_MODEL_DIR


@lru_cache(maxsize=1)
def _voice() -> PiperVoice:
    model_path = Path(PIPER_MODEL_DIR) / f"{PIPER_MODEL}.onnx"
    return PiperVoice.load(str(model_path))


def synthesize(text: str) -> bytes:
    voice = _voice()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit PCM
        wav.setframerate(voice.config.sample_rate)
        voice.synthesize(text, wav)
    result = buf.getvalue()
    print(f"[TTS] synthesized {len(result)} bytes at {voice.config.sample_rate} Hz for: {text[:80]!r}", flush=True)
    return result
