FROM python:3.7.1-stretch

ENV DEBUG=

RUN mkdir /bot/
RUN python -m venv /bot/.venv
RUN cd /bot && \
    git clone https://github.com/pferreir/indico-mattermost src
RUN cd /bot/src && \
    /bot/.venv/bin/python setup.py install

VOLUME ["/bot/config"]
ENTRYPOINT [ "/bot/.venv/bin/indico-mm-bot", "run", "/bot/config/bot.conf" ]
