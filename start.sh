#!/bin/bash
set -e
cd /app
exec /app/.venv/bin/python -c "
from app.database import init_db
init_db()
import uvicorn
uvicorn.run('app.main:app', host='0.0.0.0', port=8000)
"