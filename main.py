import chainlit as cl
from agents.task_agent import run as agent_run
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


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    chunks: list[bytes] = cl.user_session.get("audio_chunks")
    chunks.append(bytes(chunk.data))


@cl.on_audio_end
async def on_audio_end(elements):
    chunks: list[bytes] = cl.user_session.get("audio_chunks")
    if not chunks:
        return

    audio_bytes = b"".join(chunks)
    cl.user_session.set("audio_chunks", [])

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

async def _respond(user_text: str):
    messages: list[dict] = cl.user_session.get("messages")
    messages.append({"role": "user", "content": user_text})

    reply = agent_run(messages)

    messages.append({"role": "assistant", "content": reply})
    cl.user_session.set("messages", messages)

    wav_bytes = synthesize(reply)
    audio_el = cl.Audio(content=wav_bytes, mime="audio/wav", auto_play=True)
    await cl.Message(content=reply, elements=[audio_el]).send()
