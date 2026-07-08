FROM python:3.12-slim-bookworm

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV REDMOND_GAME_DIR=/opt/redmond/src/redmond_server/game

WORKDIR /opt/redmond

COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts

RUN python -m pip install --upgrade pip \
 && pip install . \
 && chmod +x scripts/container_start.sh scripts/test_compose.sh

RUN useradd --create-home --home-dir /home/redmond --shell /bin/sh redmond \
 && mkdir -p \
    /opt/redmond/src/redmond_server/game/server/.media \
    /opt/redmond/src/redmond_server/game/server/.static \
    /opt/redmond/src/redmond_server/game/server/backups \
    /opt/redmond/src/redmond_server/game/server/logs \
 && chown -R redmond:redmond /opt/redmond

USER redmond

EXPOSE 4000 4001 4002

CMD ["/opt/redmond/scripts/container_start.sh"]
