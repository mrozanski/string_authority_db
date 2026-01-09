#!/bin/bash
cd /home/admin/string-authority/sa-db
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000
