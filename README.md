# OpenAI Realtime API Client

A multi-modal client implementation for OpenAI's Realtime API with voice/text interactions via WebRTC and WebSockets.

![Realtime Architecture Diagram](https://openaidevs.retool.com/api/file/55b47800-9aaf-48b9-90d5-793ab227ddd3)

## Features

- 🎙️ Real-time voice conversations with GPT-4o models
- 📡 Dual protocol support (WebRTC & WebSockets)
- ⚡ Low-latency audio processing (16-bit PCM)
- 🔄 Bi-directional event handling
- 🔒 Ephemeral key rotation

## Installation

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- OpenAI API key

## Key Features

**Core Capabilities**

- Voice Activity Detection (VAD) with configurable thresholds
- 16-bit PCM audio encoding/decoding
- Ephemeral key rotation for secure connections
- Session lifecycle management (create/update/terminate)
- Cross-platform compatibility (Python/JS)

**Modality Support**

- Real-time audio transcriptions
- Text generation with delta updates
- Concurrent multi-modal interactions
- Custom conversation context management

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key
- Poetry package manager

## Features

- **Multi-modal Interaction**

  - Real-time voice conversations with GPT-4o models
  - Text-based chat interface
  - Audio stream processing (16-bit PCM encoding/decoding)
  - Speech-to-text transcription
  - Audio playback of model responses

- **Connection Protocols**

  - WebRTC for browser-based low-latency communication
  - WebSocket support for server-to-server integration
  - STUN/TURN server configuration
  - Data channel management for real-time events

- **Session Management**

  - Ephemeral key handling
  - Session lifecycle control (create/update/terminate)
  - Automatic reconnection logic
  - ICE candidate negotiation

- **Advanced Capabilities**
  - Speech recognition integration
  - Function calling support
  - Voice activity detection
  - Real-time transcript updates
  - Cross-platform compatibility (Python/JS)
  - Audio input/output device management

## Configuration

```env
OPENAI_API_KEY=your-api-key-here
MODEL_ID=gpt-4o-realtime-preview-2024-12-17
```

```bash
# Clone repository
git clone https://github.com/yourusername/realtime-client.git
cd realtime-client

# Install system dependencies (Ubuntu/Debian)
sudo apt install portaudio19-dev python3-dev

# Install project dependencies
poetry install

# Configure environment
cp .env.example .env
nano .env  # Add your OpenAI API key
```

## Usage

```bash
# Start FastAPI server (development mode)
poetry run uvicorn app.server:app --reload --port 9090

# In separate terminal, run Python client
poetry run python app/client.py

# Access web client at: http://localhost:9090
```

## Key Components

| Component           | Description                                   |
| ------------------- | --------------------------------------------- |
| `/app/server.py`    | FastAPI endpoint for ephemeral keys           |
| `/app/client.py`    | Python WebRTC implementation                  |
| `/static/client.js` | Browser WebRTC client with speech recognition |
| `pyproject.toml`    | Dependency configuration                      |

## Development

```bash
# Run tests
poetry run pytest

# Format code
poetry run black .

# Check linting
poetry run flake8
```

## Documentation

- [WebRTC Connection Guide](/docs/realtime_connect_with_WebRTC.md)
- [Model Capabilities](/docs/realtime_model_capabilities.md)
- [WebSocket Implementation](/docs/reltime_connect_with_Websockets.md)

## License

MIT Licensed. See [LICENSE](LICENSE) for details.
