# Indico chat bot

Posts indico events to Mattermost channels. Yep, not really a chat bot, more an Indico bot
that posts events to chat rooms.

## Installation

- `uv sync --locked --extra redis` (when using redis as the storage backend)
- `uv sync --locked` (otherwise)

There's also a docker-compose file, so you can use `docker-compose up` to run in Docker.
