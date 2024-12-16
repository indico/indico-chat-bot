FROM python:3.13-alpine

ENV DEBUG=

RUN mkdir /bot/
RUN python -m venv /bot/.venv
COPY . /bot/src
RUN cd /bot/src && \
    /bot/.venv/bin/pip install .[redis]

VOLUME ["/bot/config"]
ENTRYPOINT [ "/bot/.venv/bin/indico_chat_bot", "run", "/bot/config/bot.conf" ]
