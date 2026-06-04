import io
from functools import lru_cache
from faster_whisper import WhisperModel
from config import WHISPER_MODEL


@lru_cache(maxsize=1)
def _model() -> WhisperModel:
    return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")


def transcribe(audio_bytes: bytes) -> str:
    segments, _ = _model().transcribe(io.BytesIO(audio_bytes))
    return " ".join(seg.text.strip() for seg in segments).strip()
