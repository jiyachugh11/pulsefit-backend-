"""Read existing stores through the actual FastAPI routes. Run from project root."""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app
from app.db.cassandra_db import session
from app.db.mongo import metadata_collection
from app.db.neo4j_db import session as graph_session
from app.db.redis_db import client as redis_client

with TestClient(app) as client:
    for path in ['/users', '/devices', '/challenges', '/metadata/PB101',
                 '/telemetry/PB101?reading_date=' + os.getenv('TELEMETRY_DEFAULT_DAY', '2026-10-11'), '/social/U101/following',
                 '/social/U101/recommendations', '/leaderboard']:
        result = client.get(path)
        data = result.json()
        print(path, result.status_code, ('rows=' + str(len(data))) if isinstance(data, list) else
              ('document found' if result.is_success else data), flush=True)
with session() as connection:
    print('Cassandra columns:', [(r.column_name, r.type) for r in connection.execute(
        "SELECT column_name, type FROM system_schema.columns WHERE keyspace_name='pulsefit' AND table_name='sensor_readings_by_device_day'")])
with metadata_collection() as collection:
    print('MongoDB indexes:', list(collection.index_information()))
    print('MongoDB device IDs:', [r['device_id'] for r in collection.find({}, {'_id': 0, 'device_id': 1})])
with graph_session() as graph:
    print('Neo4j user IDs:', graph.run('MATCH (u:User) RETURN u.user_id AS user_id ORDER BY user_id').data())
with redis_client() as connection:
    print('Redis ping:', connection.ping())
