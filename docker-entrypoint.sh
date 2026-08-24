#!/bin/sh
# docker-entrypoint.sh
set -e

echo "Waiting for database..."
python -c "
import asyncio, sys, time
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import get_settings

async def wait():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    for attempt in range(30):
        try:
            async with engine.connect() as conn:
                pass
            print('Database is ready.')
            return
        except Exception as e:
            print(f'  ...not ready yet (attempt {attempt + 1}/30): {e}')
            time.sleep(2)
    print('Database never became ready — exiting.', file=sys.stderr)
    sys.exit(1)

asyncio.run(wait())
"

echo "Running database migrations..."
alembic upgrade head

echo "Seeding baseline reference data..."
python -m app.seed || true

echo "Starting application..."
exec "$@"
