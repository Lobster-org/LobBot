# LobBot

LobBot is a modular Telegram community bot intended to replace multiple single-purpose bots with one configurable platform. Groups can enable the modules they need while sharing one permission system, database, event bus, and application lifecycle.

## Project status

**Phase 1 — Core Platform: Complete ✅**

Phase 1 established the production foundation for future LobBot modules. The next development phase is the moderation system.

| Phase | Status |
| --- | --- |
| Phase 1: Core Platform | ✅ Complete |
| Phase 2: Moderation System | ⏳ Planned |
| Phase 3: Expanded Music Features | ⏳ Planned |
| Phase 4: Games and Entertainment | ⏳ Planned |
| Phase 5: Economy and Progression | ⏳ Planned |
| Phase 6: Community Management | ⏳ Planned |
| Phase 7: AI Features | ⏳ Planned |
| Phase 8: Web Dashboard | ⏳ Planned |
| Phase 9: Scaling and Reliability | ⏳ Planned |

## Phase 1 deliverables

### Core platform

- Modular aiogram v3 command and callback routing
- Explicit module registration and lifecycle hooks
- Application dependency container with consistent ownership
- Ordered startup and reverse-order shutdown
- Central structured logging with rotating general and error logs
- Global aiogram exception handling with safe user responses
- Process-local asynchronous event bus with listener isolation
- `/start` introduction and paginated `/help` command browser

### Users, groups, and permissions

- Atomic MongoDB user and group registration
- User and group activity tracking
- Per-group module enable and disable state
- Central named permission system
- Telegram creator and administrator role mapping
- Persistent custom LobBot moderator roles
- Group-specific permission overrides
- Reusable aiogram permission filter

### Phase 1 music foundation

- YouTube search through `yt-dlp`
- Downloaded WebM audio playback through PyTgCalls
- MongoDB music cache metadata
- Persistent per-group queues and restart restoration
- Duplicate-download protection
- Multi-group playback coordination
- Pause, resume, skip, stop, queue, and remove controls
- Track queued, started, finished, skipped, and stopped events
- Tracked and cancelled playback/download tasks during shutdown

Playlists, favorites, lyrics, recommendations, Spotify integration, and music analytics are intentionally outside Phase 1.

## Architecture

```text
Telegram Update
      |
      v
aiogram Handler / Filter
      |
      v
Service Layer ---------> EventBus ---------> Module listeners
      |
      v
Repository Layer
      |
      v
MongoDB
```

Application dependencies have one lifecycle owner:

```text
Application
  |
  +-- AppContainer
  |     +-- settings
  |     +-- MongoDB / database
  |     +-- EventBus
  |     +-- voice lifecycle
  |     +-- VoiceChatService
  |
  +-- ModuleLoader
        +-- setup(container, dispatcher)
        +-- startup(container)
        +-- shutdown(container)  # reverse order
```

Handlers deal with Telegram input and output, services contain business logic, repositories own database access, and feature modules communicate through events instead of importing each other.

## Available commands

| Command | Purpose |
| --- | --- |
| `/start` | Show a short LobBot introduction |
| `/help` | Browse commands using the inline help menu |
| `/modules` | List modules and their current status |
| `/enable <module>` | Enable a non-core module in a group |
| `/disable <module>` | Disable a non-core module in a group |
| `/role @user moderator` | Assign a custom moderator role |
| `/unrole @user` | Remove a custom LobBot role |
| `/play <song>` | Search for and queue music |
| `/queue` | Show current and upcoming tracks |
| `/remove <position>` | Remove a queued track |
| `/pause` | Pause playback |
| `/resume` | Resume playback |
| `/skip` | Skip the current track |
| `/stop` | Stop playback and clear the queue |

Administrative commands are protected by the centralized permission system. Music must be enabled for the group before its commands are available.

## Technology

- Python 3.13
- aiogram v3
- MongoDB with Motor
- Telethon
- PyTgCalls
- yt-dlp
- FFmpeg
- Docker Compose for local MongoDB

Redis and external message brokers are not part of the current runtime.

## Repository structure

```text
app/
├── core/                 # configuration, container, events, logging
├── database/             # MongoDB lifecycle, models, repositories
├── modules/
│   ├── group/
│   ├── help/
│   ├── management/
│   ├── music/
│   └── start/
├── services/             # shared business services
└── telegram/             # bot client, middleware, filters, voice

tests/                    # isolated service and lifecycle tests
storage/music/            # downloaded music cache
docs/                     # implementation and review notes
```

## Local setup

### Requirements

- Python 3.13
- MongoDB
- FFmpeg available on `PATH`
- Telegram bot token
- Telegram API ID and API hash for the voice client

### Installation

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configure these values in `.env`:

```dotenv
ENVIRONMENT=development
LOG_LEVEL=INFO

TELEGRAM_BOT_TOKEN=
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
VOICE_SESSION_NAME=lobbot_voice

MONGO_URI=mongodb://localhost:27017
MONGO_DATABASE=lobbot

# Reserved for a later phase; required by the current settings schema.
REDIS_URI=redis://localhost:6379/0

MUSIC_STORAGE_PATH=storage/music
```

Start the application:

```bash
python -m app.main
```

The first voice-client login may require Telegram authentication. Never commit tokens, API hashes, codes, or session files.

## Testing

Run tests that do not require a live MongoDB instance:

```bash
pytest -q --ignore=tests/test_mongodb.py --ignore=tests/test_repositories.py
```

Phase 1 currently has **42 passing offline tests**, covering permissions, logging, global errors, help navigation, events, music persistence/playback, and module lifecycle behavior.

Run the entire suite when a test MongoDB instance is available:

```bash
pytest -q
```

## Phase 1 boundaries

The following were deliberately deferred:

- Redis-backed state
- Playlists and favorites
- Lyrics and recommendations
- Spotify integration
- Moderation features
- Economy and analytics modules
- Web dashboard
- Distributed workers or message brokers

See [ARCHITECTURE.md](ARCHITECTURE.md) and [PLAN.md](PLAN.md) for the broader design and roadmap.

## Vision

One bot. Every community feature. Fully customizable.
