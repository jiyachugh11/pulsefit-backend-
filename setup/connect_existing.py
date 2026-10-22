"""Non-destructive index setup and missing leaderboard samples for local stores."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app  # Loads the project's .env before connection modules.
from app.db.mongo import metadata_collection
from app.db.redis_db import client
from app.db.cassandra_db import session

with metadata_collection() as collection:
    collection.create_index('device_id', unique=True)
    print('Unique MongoDB device_id index ready.')
with client() as connection:
    connection.zadd('pulsefit:leaderboard:steps:2026-10-11',
                    {'U101': 25200, 'U102': 24700, 'U103': 23100, 'U104': 18900}, nx=True)
    connection.save()
    print('Missing leaderboard sample scores added and saved; existing scores preserved.')
with session() as connection:
    # One-time inspection only, not a web endpoint. No ALLOW FILTERING or writes.
    print('Existing telemetry partition sample:', [(r.device_id, str(r.reading_date))
          for r in connection.execute('SELECT device_id, reading_date FROM sensor_readings_by_device_day LIMIT 10')])
