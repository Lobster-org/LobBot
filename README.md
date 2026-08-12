# LobBot

LobBot is a modular Telegram community bot intended to replace multiple single-purpose bots with one configurable platform. Groups can enable the modules they need while sharing one permission system, database, event bus, and application lifecycle.

## Project status

**Phase 1 — Core Platform: Complete ✅**

Phase 1 established the production foundation. Phase 2 now includes moderation, community automation, games, and group-scoped progression.

| Phase | Status |
| --- | --- |
| Phase 1: Core Platform | ✅ Complete |
| Phase 2: Community, Games & Economy | 🚧 In progress |
| Phase 3: Expanded Music Features | ⏳ Planned |
| Phase 4: Games and Entertainment | 🚧 In progress |
| Phase 5: Economy and Progression | 🚧 In progress |
| Phase 6: Advanced Community Features | ⏳ Planned |
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
- LobMusic membership and voice-chat permission preflight
- One-click LobMusic invitation with expired-link retry
- Automatic administrator promotion attempt for voice-chat management
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
| `/warn @user <reason>` | Add a persistent group warning |
| `/warnings @user` | List active manual and automod warnings |
| `/warnremove <id>` | Remove an active warning |
| `/automod [status\|on\|off]` | Configure automated message moderation |
| `/mute @user <duration> [reason]` | Temporarily restrict a member |
| `/unmute @user` | Manually restore a muted member's permissions |
| `/ban @user [reason]` | Ban a member from the group |
| `/kick @user` | Remove a member without permanently banning them; a reason is optional |
| `/unban @user` | Remove a member's ban |
| `/banned` | Browse active bans and unban with inline buttons |
| `/purge <amount>` or reply with `/purge` | Bulk-delete up to 10,000 recent messages |
| `/rules` | Show the current group rules |
| `/community` | Show community-module configuration |
| `/welcome on\|off` | Configure welcome messages |
| `/setwelcome <message>` | Set a custom welcome template |
| `/goodbye on\|off` | Configure goodbye messages |
| `/setgoodbye <message>` | Set a custom goodbye template |
| `/setrules <text>` | Save group rules |
| `/clearrules` | Clear group rules |
| `/verification on\|off` | Configure newcomer verification |
| `/servicecleanup on\|off` | Configure join/leave service-message cleanup |
| `/games` | List available group games |
| `/cancelgame` | Cancel your active game |
| `/coinflip [heads\|tails]` | Flip a coin with an optional prediction |
| `/guess [number]` | Start or play a number-guessing session |
| `/rps [@user]` | Play a Normal or virtual-coin Bets match over 5, 10, or 20 rounds |
| `/bet <amount>` | Lock a custom stake into an active RPS betting match |
| `/tictactoe [@user]` | Play a single-message 5, 10, or 20-round board match |
| `/connect4 [@user]` | Play a single-message 5, 10, or 20-round board match |
| `/hangman @user` | Invite a player and privately submit a hidden phrase; optional hints appear at three attempts remaining |
| `/trivia` | Select a category and play fresh API-backed 5, 10, or 20-round trivia |
| `/profile` | Show your group economy profile |
| `/balance` | Show your group coin balance |
| `/level` | Show your level and XP |
| `/daily` | Claim the daily reward |
| `/leaderboard [xp\|coins\|wins]` | Show group rankings |
| `/pay @user <amount>` | Transfer coins to another group member |

Automod configuration supports flood bursts, repeated messages, links, excessive caps, and group-specific blocked words. Automod is disabled by default and must be enabled per group with `/automod on`.

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

Economy levels use `floor(sqrt(xp / 100))`. Balance changes use conditional
atomic MongoDB updates. Transfers use an atomic sender debit followed by a
recipient credit with automatic sender compensation if that credit fails.
Strict multi-document transaction guarantees can be added later for MongoDB
replica-set deployments.

## Repository structure

```text
app/
├── core/                 # configuration, container, events, logging
├── database/             # MongoDB lifecycle, models, repositories
├── modules/
│   ├── group/
│   ├── help/
│   ├── management/
│   ├── moderation/
│   ├── music/
│   ├── start/
│   ├── community/
│   ├── economy/
│   └── games/
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

### LobMusic group setup

Music is streamed by the authenticated Telethon user account, shown in Telegram
as LobMusic. Before `/play` can search or download a track, LobMusic must:

1. Be a member of the target group.
2. Be an administrator with **Manage Video Chats** permission.

When LobMusic is missing, `/play` displays an **Invite LobMusic** button. LobBot
creates a short-lived, one-use invite and asks the voice account to join. If
Telegram rejects a newly-created link as expired, LobBot revokes it, creates a
fresh link, and retries once.

After joining, LobBot attempts to promote LobMusic with the required voice-chat
permission. For this to work automatically, LobBot must itself be an
administrator allowed to invite users and add administrators. If it cannot
promote LobMusic, promote the account manually and enable **Manage Video
Chats**.

The same readiness check runs again when a search result is selected. A track
is not downloaded or queued if LobMusic was removed or lost permission after
the initial `/play` request.

Common setup failures:

- **LobMusic is not in the group:** use the invite button or add the account
  from its Telegram profile.
- **Invite rejected twice:** confirm LobMusic is not banned, then add it
  manually.
- **Chat admin privileges are required:** grant LobMusic **Manage Video Chats**
  and ensure LobBot can promote administrators if automatic setup is desired.
- **Playback still cannot start:** confirm the group supports voice chats and
  that neither account has had its administrative permissions changed.

## Docker deployment

Docker runs the current application entrypoint, MongoDB, FFmpeg, and the
Telegram voice client without requiring a host Python environment.

Create the deployment environment file:

```bash
cp .env.example .env
```

At minimum, configure:

```dotenv
ENVIRONMENT=production
LOG_LEVEL=INFO

TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

MONGO_ROOT_USERNAME=lobadmin
MONGO_ROOT_PASSWORD=use_a_long_random_password
MONGO_DATABASE=lobbot
DOCKER_MONGO_URI=mongodb://lobadmin:use_a_long_random_password@mongodb:27017/lobbot?authSource=admin
```

Build the image:

```bash
docker compose build bot
```

The Telethon voice account requires a one-time interactive login. Run the bot
attached the first time and enter the requested phone number, Telegram code,
and two-factor password if applicable:

```bash
docker compose run --rm bot
```

After LobBot reports that it is ready, stop that temporary container with
`Ctrl+C`. The resulting Telethon session remains in the `voice_sessions`
volume. Start the deployment in the background:

```bash
docker compose up -d
```

Inspect application output or stop the deployment with:

```bash
docker compose logs -f bot
docker compose down
```

`docker compose down` preserves named volumes. Do not use `down -v` unless you
intend to delete the MongoDB database, cached music, logs, and saved voice
login. To rebuild after source changes:

```bash
docker compose up -d --build bot
```

MongoDB is internal to the Compose network and is not exposed on a host port.
The bot waits for its health check before starting. Keep `MONGO_ROOT_PASSWORD`
and the password inside `DOCKER_MONGO_URI` identical. URI-encode reserved
characters in the connection-string password.

## Testing

Run tests that do not require a live MongoDB instance:

```bash
pytest -q --ignore=tests/test_mongodb.py --ignore=tests/test_repositories.py
```

The offline suite covers permissions, logging, global errors, help navigation, events, music, moderation, community behavior, persistence, and module lifecycle.

Run the entire suite when a test MongoDB instance is available:

```bash
pytest -q
```

## Current boundaries

The following were deliberately deferred:

- Redis-backed state
- Playlists and favorites
- Lyrics and recommendations
- Spotify integration
- Persistent event history and analytics dashboard
- Real-money economy, payments, and marketplace features
- Web dashboard
- Distributed workers or message brokers

See [ARCHITECTURE.md](ARCHITECTURE.md) and [PLAN.md](PLAN.md) for the broader design and roadmap.

## Vision

One bot. Every community feature. Fully customizable.
