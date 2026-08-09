# Architecture.md

# Telegram All-in-One Community Bot Architecture

## Overview

The system is designed as a modular Telegram bot platform.

The architecture separates:

* Telegram communication
* Business logic
* Feature modules
* External services
* Background processing
* Data storage

The goal is to allow new features to be added without modifying existing systems.

---

# High-Level Architecture

```
                         Telegram
                            |
                    Telegram Bot Layer
                            |
                    Core Application
                            |
        -----------------------------------------
        |              |              |
    Modules       Services       Event System
        |              |              |
        -----------------------------------------
                            |
                        Data Layer
                            |
              MongoDB + Redis + Storage
```

---

# Core Application

The core is responsible for shared functionality.

Responsibilities:

* Telegram connection
* Command routing
* Authentication
* Permissions
* Module loading
* Configuration
* Logging
* Error handling

Structure:

```
core/
    ├── bot.py
    ├── router.py
    ├── permissions.py
    ├── module_loader.py
    ├── events.py
    ├── config.py
    └── database.py
```

---

# Module Architecture

Each feature exists as an independent module.

Example:

```
modules/
    ├── music/
    ├── moderation/
    ├── games/
    ├── economy/
    ├── welcome/
    ├── reminders/
    ├── giveaways/
    ├── ai/
    └── utilities/
```

Each module contains:

```
module/
    ├── commands.py
    ├── services.py
    ├── models.py
    ├── handlers.py
    └── config.py
```

---

# Module Lifecycle

A module follows:

```
Install Module
      |
Register Commands
      |
Load Configuration
      |
Subscribe To Events
      |
    Run
```

---

# Event System

Modules should communicate through events.

Examples:

```
UserJoined

MessageReceived

SongStarted

SongFinished

GameWon

LevelUp

WarningCreated
```

Example:

```
UserJoined Event
        |
 ---------------------
 |                  |
Welcome Module    XP Module
 |                  |
Send Message     Add XP
```

This prevents modules from becoming tightly coupled.

---

# Database Architecture

Database: MongoDB

Reason:

* Flexible schemas
* Natural document structure
* Easy module expansion
* Good fit for user/group configuration data

---

# MongoDB Collections

## Users

```
users

{
 telegram_id,
 username,
 display_name,
 created_at,
 level,
 experience
}
```

---

## Groups

```
groups

{
 telegram_id,
 title,
 created_at,
 settings
}
```

---

## Modules

```
modules

{
 name,
 enabled,
 version
}
```

---

## Group Modules

Stores enabled features.

```
group_modules

{
 group_id,
 module_name,
 enabled,
 configuration
}
```

Example:

```
{
 music: {
    enabled: true,
    volume: 80
 },

 moderation: {
    enabled: true,
    anti_spam: true
 }
}
```

---

# Redis Usage

Redis handles temporary and high-speed data.

Used for:

* Music queues
* Rate limits
* Temporary sessions
* Locks
* Caching
* Background jobs

Example:

```
Telegram Group
        |
Redis Queue
        |
Music Worker
```

---

# Service Layer

Services provide reusable functionality.

Example:

```
services/
    ├── music/
    │
    ├── ai/
    │
    ├── media/
    │
    ├── search/
    │
    ├── scheduler/
    │
    └── notifications/
```

Modules consume services.

Example:

```
Music Module
      |
Music Service
      |
    yt-dlp
    FFmpeg
    PyTgCalls
```

---

# Music Architecture

```
User
 |
/play Song
 |
Music Module
 |
Music Service
 |
Cache Check
 |
 -------------------
 |                 |
Cached          New Song
 |                 |
Play            Resolve Source
                  |
                yt-dlp
                  |
                FFmpeg
                  |
              PyTgCalls
                  |
            Telegram Voice Chat
```

---

# Worker Architecture

Long-running tasks should not block the bot.

Workers handle:

* Music processing
* Scheduled messages
* Media processing
* AI requests
* Analytics

Architecture:

```
Telegram Bot
      |
    Queue
      |
    Workers
      |
External Services
```

---

# Permission System

Permissions should be centralized.

Example:

```
Permission Service
        |
 -----------------
 |               |
Moderation     Admin Tools
```

Example roles:

```
Owner

Admin

Moderator

Member

Guest
```

---

# Configuration System

Each group gets independent configuration.

Example:

```
Group A

Music: Enabled
Moderation: Enabled
AI: Disabled


Group B

Music: Disabled
Moderation: Enabled
AI: Enabled
```

Stored in MongoDB.

---

# Future Web Dashboard

Architecture:

```
React Dashboard
        |
    API Backend
        |
    Bot Core
        |
    MongoDB
```

Dashboard allows:

* Module management
* Permission management
* Analytics
* Configuration
* Logs

---

# Deployment Architecture

Initial deployment:

```
Docker Compose
|
|-- Bot Service
|
|-- Worker Service
|
|-- Redis
|
|-- MongoDB
|
|-- Media Storage
```

Future scaling:

```
                Load Balancer
                     |
          -----------------------
          |          |          |
       Bot 1      Bot 2      Bot 3
          |          |          |
          -----------------------
                     |
                   Redis
                     |
                MongoDB Cluster
```

---

# Design Principles

## 1. Modular First

Every feature must be removable and independent.

## 2. Event Driven

Modules communicate through events.

## 3. Configuration Driven

Groups customize their experience.

## 4. Scalable

Avoid designs that only work for one group.

## 5. Service Separation

Commands should not contain business logic.

## 6. Expandable

Adding a new feature should mean adding a module, not rewriting the bot.
