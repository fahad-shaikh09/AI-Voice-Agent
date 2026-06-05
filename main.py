import io
import re
import wave

import chainlit as cl
from agents.task_agent import run as agent_run
from config import AUDIO_SAMPLE_RATE
from stt.whisper_transcriber import transcribe
from tts.piper_synthesizer import synthesize

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are a helpful AI voice assistant. "
        "You can manage tasks, calendar events, and send emails. "
        "Be concise — your responses will be spoken aloud."
    ),
}


@cl.on_chat_start
async def start():
    cl.user_session.set("messages", [SYSTEM_PROMPT])
    cl.user_session.set("audio_chunks", [])


# --- Audio path (mic → whisper → agent → piper → speaker) ---

@cl.on_audio_start
async def on_audio_start():
    cl.user_session.set("audio_chunks", [])
    return True  # Must return truthy so server sends connection_state="on" to frontend


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    chunks: list[bytes] = cl.user_session.get("audio_chunks")
    chunks.append(bytes(chunk.data))


@cl.on_audio_end
async def on_audio_end():
    chunks: list[bytes] = cl.user_session.get("audio_chunks")
    if not chunks:
        return

    pcm_data = b"".join(chunks)
    cl.user_session.set("audio_chunks", [])

    # Browser sends raw PCM16 mono — wrap in WAV so Whisper/FFmpeg can parse it
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_out:
        wav_out.setnchannels(1)
        wav_out.setsampwidth(2)
        wav_out.setframerate(AUDIO_SAMPLE_RATE)
        wav_out.writeframes(pcm_data)
    audio_bytes = buf.getvalue()

    transcript = transcribe(audio_bytes)
    if not transcript:
        return

    await cl.Message(author="You", content=transcript).send()
    await _respond(transcript)


# --- Text path (keyboard → agent → piper → speaker) ---

@cl.on_message
async def on_message(message: cl.Message):
    await _respond(message.content)


# --- Shared agent + TTS logic ---

def _tts_text(text: str) -> str:
    """Strip Qwen3 thinking tags and markdown before sending to Piper."""
    # Remove <think>...</think> blocks (Qwen3 chain-of-thought)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Strip markdown bold/italic/code
    text = re.sub(r"[*_`#]", "", text)
    # Collapse whitespace
    return " ".join(text.split())


async def _respond(user_text: str):
    messages: list[dict] = cl.user_session.get("messages")
    messages.append({"role": "user", "content": user_text})

    reply = agent_run(messages)

    messages.append({"role": "assistant", "content": reply})
    cl.user_session.set("messages", messages)

    tts_input = _tts_text(reply)
    print(f"[TTS] input after strip: {tts_input[:120]!r}", flush=True)
    elements = []
    if tts_input:
        wav_bytes = synthesize(tts_input)
        if len(wav_bytes) > 44:  # more than just the WAV header
            elements.append(cl.Audio(name="response.wav", content=wav_bytes, mime="audio/wav", auto_play=True))
        else:
            print(f"[TTS] WARNING: only {len(wav_bytes)} bytes produced, skipping audio", flush=True)

    await cl.Message(content=reply, elements=elements).send()
