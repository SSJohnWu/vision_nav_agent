# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vision-Aided AR Navigation System — a smart assistant for visually impaired people and the elderly that provides real-time obstacle detection and voice-guided navigation. Uses computer vision (YOLOv8 + OpenCV) for detection and OpenClaw AI for decision-making, with voice interface for output.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Two Run Modes                                 │
├──────────────────────┬──────────────────────────────────────────┤
│ src/main.py          │ src/web_main.py                          │
│ Desktop direct mode   │ FastAPI web server (port 8000)           │
│ Camera + voice local │ Mobile browser accesses via ngrok HTTPS  │
└──────────────────────┴──────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
         ┌──────────────────┐  ┌─────────────────┐
         │ NavigationAgent  │  │ VisionAnalyzer  │
         │ (decision brain)│  │ (product recog) │
         └────────┬─────────┘  └────────┬────────┘
                  │                     │
       ┌──────────┴──────────┐        │
       ▼                      ▼        ▼
┌─────────────┐      ┌─────────────┐  OpenClaw
│ObstacleDetector│   │ OpenClaw AI │  (port 18789)
│ (YOLOv8+CV) │      │ endpoint    │
└─────────────┘      └─────────────┘
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `src/agent/navigation_agent.py` | AI decision brain — orchestrates detection, calls OpenClaw API |
| `src/vision/obstacle_detector.py` | YOLOv8 object detection + OpenCV edge radar for unknown obstacles |
| `src/vision/vision_analyzer.py` | Product recognition via OpenClaw (WebSocket RPC + HTTP REST fallback) |
| `src/audio/voice_interface.py` | TTS/STT interface (currently prints; TTS not fully wired) |
| `src/web_main.py` | FastAPI server — serves `src/templates/index.html` and handles `/api/*` |

### Detection Pipeline (ObstacleDetector)

1. **YOLO layer**: Detects COCO objects (person, car, bike, etc.) with Chinese translation
2. **OpenCV edge radar**: Scans bottom 1/3 of frame for unknown obstacles (ground clutter)

Results are joined into a warning string and returned immediately — no AI call needed for basic obstacles.

### OpenClaw Integration

- **Endpoint**: `http://127.0.0.1:18789` (configured in `config/config.yaml` under `ai.endpoint`)
- OpenClaw server **must be running** before starting the application
- `VisionAnalyzer` auto-detects WebSocket RPC first, falls back to HTTP REST

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure OpenClaw server is running at port 18789

# Mode A: Desktop direct (camera + voice local)
python src/main.py

# Mode B: Web server for mobile (requires ngrok for HTTPS)
python src/web_main.py
# Then in another terminal:
ngrok http 8000
# Open the ngrok HTTPS URL on mobile browser
```

### Camera Configuration

Edit `config/config.yaml`:
```yaml
camera:
  index: 1              # USB camera (0=built-in, 1+=external)
  # OR for network camera:
  index: "rtsp://username:password@192.168.1.100/stream"
```

## Key Design Decisions

- **No AI call for basic obstacles**: YOLO+OpenCV warning is returned directly for speed
- **OpenClaw used for complex reasoning** (product recognition, detailed path advice)
- **Browser WebSpeechAPI for mobile TTS**: Voice output uses browser's native speech synthesis
- **Python speech recognition only in desktop mode**: Mobile uses browser audio recording sent to `/api/command_audio`
- **VisionAnalyzer WebSocket protocol**: Uses native OpenClaw RPC with nonce challenge/response handshake

## Configuration

All settings in `config/config.yaml`:
- `camera.index` — camera selection
- `ai.endpoint` — OpenClaw server URL
- `ai.model` — model name (default: gemini-3-flash)
- `voice.rate`, `voice.voice` — TTS settings
- `obstacle_detection.model`, `obstacle_detection.confidence` — YOLO settings
