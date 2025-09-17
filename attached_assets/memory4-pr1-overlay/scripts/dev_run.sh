#!/usr/bin/env bash
export UVICORN_PORT=${PORT:-8000}
uvicorn app.main:app --host 0.0.0.0 --port $UVICORN_PORT
