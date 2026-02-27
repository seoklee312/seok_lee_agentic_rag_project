#!/bin/bash
cd "$(dirname "$0")/backend/src"
export $(grep -v '^#' ../../.env | xargs)
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
