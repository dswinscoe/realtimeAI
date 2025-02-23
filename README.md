# OpenAI Realtime API Client

![Cursor Badge](https://img.shields.io/badge/Built%20with-Cursor-2ea44f?logo=cursor) ![OpenAI Badge](https://img.shields.io/badge/Powered%20by-OpenAI%20o3--mini-412991)

**AI-Assisted Development**  
This entire repository was generated through iterative prompting workflows using [Cursor](https://cursor.sh/) with OpenAI's o3-mini model. The implementation demonstrates practical application of AI pair-programming for complex real-time systems development.

A multi-modal client implementation for OpenAI's Realtime API with voice/text interactions via WebRTC and WebSockets.

![Realtime Architecture Diagram](https://openaidevs.retool.com/api/file/55b47800-9aaf-48b9-90d5-793ab227ddd3)

## Features

**Core Capabilities**

- 🎙️ Real-time voice conversations with GPT-4o models
- 📡 Dual protocol support (WebRTC & WebSockets)
- ⚡ Low-latency audio processing (16-bit PCM)
- 🔄 Bi-directional event handling
- 🔒 Ephemeral key rotation
- 🎯 Voice Activity Detection (VAD) with configurable thresholds
- 🔄 Session lifecycle management (create/update/terminate)

**Modality Support**

- Real-time audio transcriptions
- Text generation with delta updates
- Concurrent multi-modal interactions
- Custom conversation context management
- Speech recognition integration
- Function calling support
- Audio input/output device management

## Installation

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- OpenAI API key
- PortAudio development files (Ubuntu/Debian: `sudo apt install portaudio19-dev python3-dev`)

```bash
# Clone repository
git clone https://github.com/yourusername/realtime-client.git
cd realtime-client

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

# Run Python client
poetry run python app/client.py

# Access web client at: http://localhost:9090
```

## Architecture

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

# Lint checks
poetry run flake8
```

## Documentation

- [Overview](/realtime_client/docs/realtime_overview.md)
- [WebRTC Connection Guide](/realtime_client/docs/realtime_connect_with_WebRTC.md)
- [Model Capabilities](/realtime_client/docs/realtime_model_capabilities.md)
- [WebSocket Implementation](/realtime_client/docs/realtime_connect_with_Websockets.md)
- [AI Development Process](/realtime_client/docs/ai_development_process.md)

**Note:** The `/realtime_client/docs` directory contains unmodified markdown files from OpenAI's public documentation and a new file documenting the AI-assisted development process. These resources provide context for AI-assisted development workflows when using tools like Cursor with o3-mini model.

## License

MIT Licensed. See [LICENSE](LICENSE) for details.
