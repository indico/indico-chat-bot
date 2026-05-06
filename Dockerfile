FROM python:3.14-alpine

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN mkdir /bot/
COPY . /bot/
RUN cd /bot/ && uv sync --locked --extra redis


VOLUME ["/bot/config"]
CMD ["/bot/.venv/bin/indico-chat-bot", "run", "/bot/config/bot.conf"]
