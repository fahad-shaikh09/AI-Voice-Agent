# AI Voice Agent

An offline, fully local AI voice assistant. Speak into the mic, the agent understands you, calls tools, and speaks back — no cloud APIs required.

## Pipeline

```
Mic → Whisper (STT) → Qwen (LLM + tools) → Piper (TTS) → Speaker
```

| Stage | Implementation |
|---|---|
| UI / session | Chainlit (web app, also accepts text input) |
| Speech-to-text | `faster-whisper` — `base` model, CPU, int8 quantized |
| LLM | Qwen3.6 via Ollama (`qwen3.6` model) |
| Tool execution | Custom dispatcher in `tools/` |
| Text-to-speech | Piper TTS — `en_US-lessac-medium` ONNX voice |

Qwen3's `<think>...</think>` chain-of-thought blocks are stripped before text is passed to Piper, as are markdown symbols.

## Tools

The agent has three built-in tools (in-memory, no persistence across restarts):

| Tool | Functions |
|---|---|
| Tasks | `create_task`, `list_tasks` |
| Calendar | `create_event`, `list_events` |
| Email | `send_email`, `list_sent_emails` |

## Project Structure

```
main.py                  # Chainlit app — audio/text handlers, TTS playback
config.py                # All settings read from env vars (with defaults)
agents/task_agent.py     # Ollama tool-calling loop
stt/whisper_transcriber.py
tts/piper_synthesizer.py
tools/
  __init__.py            # ALL_TOOLS list + dispatch()
  tasks.py
  calendar.py
  email.py
public/autostop.js       # Client-side JS to auto-stop mic recording
```

## Running Locally

**Prerequisites:** Ollama running with `qwen3.6` pulled, Python 3.13+, `uv`.

```bash
# Pull the LLM
ollama pull qwen3.6

# Install dependencies
uv sync

# Download Piper voice model
mkdir -p tts/models
curl -fsSL -o tts/models/en_US-lessac-medium.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
curl -fsSL -o tts/models/en_US-lessac-medium.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"

# Run
uv run chainlit run main.py
```

Open `http://localhost:8000`. Click the mic icon to speak, or type.

## Configuration

All settings are env vars with sensible defaults:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `qwen3.6` | Model name |
| `WHISPER_MODEL` | `base` | faster-whisper model size |
| `PIPER_MODEL` | `en_US-lessac-medium` | Piper voice name |
| `PIPER_MODEL_DIR` | `tts/models` | Directory with `.onnx` files |
| `AUDIO_SAMPLE_RATE` | `16000` | Mic capture sample rate (Hz) |

## Deployment — OpenShift

The project ships with two Helm charts:

- `helm-charts/ollama/` — deploys Ollama with a PVC for model storage
- `helm-charts/voice-agent/` — deploys the Chainlit app

The Dockerfile bakes the Whisper `base` model and the Piper ONNX file into the image at build time (no runtime downloads). It runs as UID 1001 and is compatible with OpenShift's arbitrary-UID security policy.

```bash
# Build image (from project root)
docker build -t ai-voice-agent:latest .

# Deploy Ollama first
helm upgrade --install ollama helm-charts/ollama/

# Deploy voice agent
helm upgrade --install voice-agent helm-charts/voice-agent/
```

The OpenShift Route is TLS-terminated (edge) with a 300s HAProxy timeout to accommodate long audio responses.

## Known Limitations / What's Not Implemented

- **No persistence** — tasks, calendar events, and sent emails live in memory and are lost on restart
- **Single channel** — web UI only (no phone, WhatsApp, etc.)
- **No dashboard** — no conversation history view, analytics, or admin UI
- **Email is simulated** — `send_email` logs to memory, does not actually send SMTP
- **English only** — Piper voice and Whisper model are English

## Future Direction (Separate Project)

A LiveKit-based rewrite would give: lower-latency streaming audio via WebRTC, built-in VAD, SIP/PSTN phone support, and a single agent core serving multiple channels (web, WhatsApp, voice call) — similar to what platforms like nabrah.ai offer.
