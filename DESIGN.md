# AI Voice Agent — Design Document

## Overview

A fully offline AI voice agent deployed entirely inside **OpenShift Local (CRC)** on an Apple M5 Mac. Designed to be portable — the same manifests work on any Kubernetes/OpenShift cluster.

| Component | Where it runs | Notes |
|-----------|--------------|-------|
| Chainlit UI | OpenShift pod | Browser-accessible via OpenShift Route |
| Whisper STT | Voice agent pod (in-process) | faster-whisper, CPU |
| Qwen LLM | Ollama pod | PVC holds model weights (seeded once from Mac, never re-downloaded) |
| Tool layer | Voice agent pod (in-process) | calendar, email, tasks |
| Piper TTS | Voice agent pod (in-process) | ONNX CPU, model baked into image |

No MCP. Tool calling uses Ollama's native OpenAI-compatible function-calling format directly in Python.

---

## Pipeline

```
Mic
 ↓  (browser MediaRecorder API → Chainlit audio hook)
Whisper  (faster-whisper, CPU, in-process)
 ↓  (transcript string)
Agent  (Qwen3 via Ollama pod, tool-calling loop)
 ↓  (tool calls dispatched, results fed back)
Tool Calls  (calendar / email / tasks — Python functions)
 ↓  (final LLM text response)
Piper  (ONNX CPU, in-process)
 ↓  (WAV audio bytes)
Speaker  (browser AudioContext)
```

---

## Ollama — Model Weights via PVC (No Re-download)

Ollama runs as its own Deployment inside OpenShift with a PVC for model storage. The already-downloaded Qwen weights (`~/.ollama/models/` on your Mac) are copied into the PVC **once** via `oc cp`. After that, pod restarts reuse the PVC — no internet access, no re-download, works on any cluster.

### One-time seeding procedure

```bash
# 1. Deploy Ollama (PVC will be empty initially)
oc apply -f k8s/ollama-pvc.yaml
oc apply -f k8s/ollama-deployment.yaml
oc apply -f k8s/ollama-service.yaml

# 2. Wait for the pod to be Running
oc wait --for=condition=Ready pod -l app=ollama --timeout=60s

# 3. Copy your local model weights into the PVC (one-time)
OLLAMA_POD=$(oc get pod -l app=ollama -o jsonpath='{.items[0].metadata.name}')
oc cp ~/.ollama/models/ ${OLLAMA_POD}:/root/.ollama/models/

# 4. Verify Ollama sees the model
oc exec ${OLLAMA_POD} -- ollama list
```

After this the PVC persists the weights across all future pod restarts. No init container, no pull, no internet required.

### Why PVC over host IP

| Approach | Portability | Complexity |
|----------|------------|------------|
| Point pods at Mac host IP | Mac-only | Simple config but breaks on any other cluster |
| PVC + one-time `oc cp` seed | Any k8s cluster | One extra setup step, then fully self-contained |

---

## Component Design

### 1. Mic → Whisper (STT)

- Chainlit frontend captures audio via browser `MediaRecorder` API (WebM/Opus).
- Sent to backend via Chainlit's `@cl.on_audio_chunk` / `@cl.on_audio_end` hooks.
- Transcribed with `faster-whisper` (CTranslate2, CPU). Model size set via `WHISPER_MODEL` env var (`base` for speed, `small` for accuracy).
- Whisper model weights are downloaded at container startup into a writable volume (small, ~150 MB for `base`). Optionally bake into the image for faster cold start.

```
stt/
  whisper_transcriber.py   # transcribe(audio_bytes: bytes) -> str
```

### 2. Transcript → Agent (LLM + Tool Loop)

- Transcript becomes the user message in the Chainlit session.
- `ollama.chat()` called with tool definitions in OpenAI function-calling format.
- Agent loop: if response contains tool calls → dispatch → append result → re-call model → repeat until plain text response.
- Ollama is reached via its ClusterIP service at `http://ollama:11434`.

```
agents/
  task_agent.py   # run(messages, tools) -> str
```

### 3. Tool Calls

- Each tool: a Python function + a JSON schema descriptor (`TOOL_DEF`).
- Central registry in `tools/__init__.py` handles listing schemas and dispatching by name.

```
tools/
  __init__.py      # ALL_TOOLS: list[dict], dispatch(name, args) -> str
  calendar.py
  email.py
  tasks.py
```

Tool descriptor shape:
```python
TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "create_task",
        "description": "Create a new task with a title and optional due date.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "due_date": {"type": "string", "description": "ISO 8601 date"}
            },
            "required": ["title"]
        }
    }
}
```

### 4. Agent Response → Piper (TTS)

- Final LLM text passed to `piper-tts`.
- Piper runs a local ONNX voice model (`en_US-lessac-medium`, ~60 MB), baked into the container image.
- Output: 16-bit PCM WAV bytes — fully offline.

```
tts/
  piper_synthesizer.py   # synthesize(text: str) -> bytes  (WAV)
  models/
    en_US-lessac-medium.onnx
    en_US-lessac-medium.onnx.json
```

### 5. WAV → Speaker

- WAV bytes returned to Chainlit as a `cl.Audio` element — browser plays it automatically.

---

## File Structure (target)

```
AI-Voice-Agent/
├── main.py                  # Chainlit entry: audio hooks + message handler
├── config.py                # env-driven config
├── pyproject.toml
├── Dockerfile
│
├── agents/
│   └── task_agent.py
│
├── tools/
│   ├── __init__.py
│   ├── calendar.py
│   ├── email.py
│   └── tasks.py
│
├── stt/
│   └── whisper_transcriber.py
│
├── tts/
│   ├── piper_synthesizer.py
│   └── models/
│       ├── en_US-lessac-medium.onnx
│       └── en_US-lessac-medium.onnx.json
│
└── helm-charts/
    ├── voice-agent/              # Helm chart: Chainlit + Whisper + Piper pod
    │   ├── Chart.yaml
    │   ├── values.yaml
    │   └── templates/
    │       ├── _helpers.tpl
    │       ├── configmap.yaml
    │       ├── deployment.yaml
    │       ├── service.yaml
    │       └── route.yaml        # OpenShift Route (route.openshift.io/v1)
    │
    └── ollama/                   # Helm chart: Ollama pod + PVC
        ├── Chart.yaml
        ├── values.yaml
        └── templates/
            ├── _helpers.tpl
            ├── pvc.yaml
            ├── deployment.yaml
            └── service.yaml
```

---

## Implementation Order

| Phase | What |
|-------|------|
| 1 | Tool registry (`tools/__init__.py`) + agent loop (`task_agent.py`) |
| 2 | `config.py` + wire agent into `main.py` (text chat with tools works) |
| 3 | Whisper STT (`stt/whisper_transcriber.py`) + Chainlit audio hooks |
| 4 | Piper TTS (`tts/piper_synthesizer.py`) + browser audio playback |
| 5 | Full end-to-end wiring: mic → whisper → agent → piper → speaker |
| 6 | Dockerfile + k8s manifests + one-time PVC seed → deploy to CRC |

---

## Configuration (`config.py`)

| Var | Default | Description |
|-----|---------|-------------|
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama ClusterIP service (works on any cluster) |
| `OLLAMA_MODEL` | `qwen3:6` | Model tag |
| `WHISPER_MODEL` | `base` | faster-whisper model size |
| `PIPER_MODEL` | `en_US-lessac-medium` | Piper voice name |
| `PIPER_MODEL_DIR` | `tts/models` | Path to .onnx + .json files |

---

## Kubernetes / OpenShift Deployment

### Architecture

```
OpenShift Cluster (CRC)
│
├── Namespace: ai-voice-agent
│    │
│    ├── Route  ──────────────────────────────────┐
│    │   (HTTPS, TLS edge, WebSocket timeout)      │
│    │                                             ▼
│    ├── Service: voice-agent (ClusterIP :8000)
│    │        ↓
│    ├── Deployment: voice-agent
│    │   └── Pod
│    │        ├── Chainlit  :8000
│    │        ├── faster-whisper (in-process, CPU)
│    │        └── Piper ONNX (in-process, CPU)
│    │
│    ├── Service: ollama (ClusterIP :11434)
│    │        ↓
│    ├── Deployment: ollama
│    │   └── Pod
│    │        └── ollama serve  (qwen3:6)
│    │
│    └── PVC: ollama-models  (model weights, seeded once via oc cp)
```

### Helm chart overview

Two independent charts — deploy and upgrade each separately:

| Chart | Templates | Key values |
|-------|-----------|------------|
| `helm-charts/voice-agent` | configmap, deployment, service, route | `config.ollamaHost`, `image.repository`, `route.host` |
| `helm-charts/ollama` | pvc, deployment, service | `persistence.size`, `model`, `image.tag` |

**Install commands:**

```bash
# Create namespace
oc new-project ai-voice-agent

# Deploy Ollama first (PVC must exist before seeding)
helm install ollama helm-charts/ollama -n ai-voice-agent

# Seed model weights from Mac (one-time)
OLLAMA_POD=$(oc get pod -l app.kubernetes.io/name=ollama -n ai-voice-agent -o jsonpath='{.items[0].metadata.name}')
oc cp ~/.ollama/models/ ${OLLAMA_POD}:/root/.ollama/models/ -n ai-voice-agent

# Deploy voice agent (image must be built and pushed first)
helm install voice-agent helm-charts/voice-agent -n ai-voice-agent

# Upgrade after config changes
helm upgrade voice-agent helm-charts/voice-agent -n ai-voice-agent
helm upgrade ollama helm-charts/ollama -n ai-voice-agent
```

**Override a value without editing values.yaml:**

```bash
helm upgrade voice-agent helm-charts/voice-agent \
  --set config.whisperModel=small \
  --set image.tag=v1.1.0 \
  -n ai-voice-agent
```

### Dockerfile sketch

```dockerfile
FROM python:3.13-slim
WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev

# Piper voice model baked in (~60 MB)
COPY tts/models/ tts/models/

COPY . .
EXPOSE 8000
CMD ["uv", "run", "chainlit", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
```

### OpenShift notes

- **SCC**: voice agent and Ollama pods both run as non-root with the `restricted` SCC — no special privileges needed.
- **WebSocket**: `haproxy.router.openshift.io/timeout: 300s` annotation on the Route keeps Chainlit's WebSocket alive.
- **Secrets**: tool integrations needing OAuth tokens → OpenShift Secret, mounted as env vars.
- **Resource requests (CPU-only, no GPU)**:
  - `voice-agent`: 500m CPU / 512Mi RAM request; 2 CPU / 2Gi RAM limit
  - `ollama`: 2 CPU / 6Gi RAM request; 4 CPU / 8Gi RAM limit

---

## Dependencies (`pyproject.toml`)

```toml
dependencies = [
    "chainlit>=2.11.1",
    "ollama>=0.6.2",
    "faster-whisper>=1.0.0",
    "piper-tts>=1.2.0",
]
```

> `ffmpeg` (system package) is required by faster-whisper for audio decoding — installed in the Dockerfile.

---

## Open Questions / Decisions Deferred

1. **Streaming TTS** — Piper output sentence-by-sentence for lower latency. Needs sentence splitter. Revisit after full round-trip works.
2. **VAD (Voice Activity Detection)** — auto end-of-speech detection via `silero-vad`. Eliminates manual stop button. Phase 2+.
3. **Auth** — Chainlit supports password/OAuth auth. Required before exposing the Route beyond the local cluster.
4. **Whisper model in image vs. runtime download** — baking `base` into the image (~150 MB) eliminates cold-start download; adds to image size. Decide at Dockerfile phase.
