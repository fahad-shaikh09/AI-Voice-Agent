import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.6")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
PIPER_MODEL = os.getenv("PIPER_MODEL", "en_US-lessac-medium")
PIPER_MODEL_DIR = os.getenv("PIPER_MODEL_DIR", "tts/models")
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
