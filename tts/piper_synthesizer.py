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
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        _voice().synthesize(text, wav)
    return buf.getvalue()
