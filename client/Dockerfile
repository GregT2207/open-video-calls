ARG PYTHON_VERSION=3.10.0
FROM python:${PYTHON_VERSION}-slim as base

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxrender1 \
    libsm6 \
    libxext6 \
    libx11-xcb1 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
  && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

ENV SERVER_ADDRESS=127.0.0.1
ENV SERVER_PORT=5000

WORKDIR /app

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

USER appuser

COPY . .

CMD python src/main.py
