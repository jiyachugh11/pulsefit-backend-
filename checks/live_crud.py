"""Explicit live verification with unique disposable IDs and cleanup.

Run manually, never on application startup. Existing sample rows are not changed.
"""
import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app
from app.db.postgres import cursor
from app.db.mongo import metadata_collection
from app.db.cassandra_db import session
from app.db.neo4j_db import session as graph_session
from app.db.redis_db import client as redis_client

suffix = uuid.uuid4().hex[:6]
user_id, target_id, device_id, challenge_id = ['T' + p + suffix for p in 'UVDC']
timestamp = '2026-10-22T12:00:00Z'
day = '2026-10-22'
client = TestClient(app)


def request(method, path, body=None, expected=200):
    response = client.request(method, path, json=body) if body is not None else client.request(method, path)
    assert response.status_code == expected, (method, path, response.status_code, response.json())
    print(method, path, response.status_code, flush=True)
    return response.json()


try:
    for identifier in (user_id, target_id):
        request('POST', '/users', dict(user_id=identifier, first_name='Connection', last_name='Check',
                                     email=identifier + '@example.test'), 201)
    request('PUT', '/users/' + user_id, dict(first_name='Updated', last_name='Check', email=user_id+'@example.test'))
    request('GET', '/users/' + user_id)
    device = dict(device_id=device_id, user_id=user_id, device_type='band', brand='Test', model='Test band')
    request('POST', '/devices', device, 201)
    request('PUT', '/devices/' + device_id, {**device, 'model': 'Updated band'})
    request('DELETE', '/users/' + user_id, expected=409)
    challenge = dict(challenge_id=challenge_id, challenge_name='Connection check', start_date=day, end_date=day)
    request('POST', '/challenges', challenge, 201)
    request('PUT', '/challenges/' + challenge_id, {**challenge, 'challenge_name': 'Updated check'})
    metadata = dict(device_id=device_id, model='Test band', sensors=['steps'], settings={'units': 'metric'})
    request('POST', '/metadata', metadata, 201)
    request('POST', '/metadata', metadata, 409)
    request('PUT', '/metadata/' + device_id, {**metadata, 'verified': True})
    assert request('GET', '/metadata/' + device_id)['verified'] is True
    reading = dict(device_id=device_id, reading_date=day, reading_ts=timestamp, heart_rate=80,
                   steps=123, spo2=98, latitude=0, longitude=0)
    request('POST', '/telemetry', reading, 201)
    assert len(request('GET', '/telemetry/' + device_id + '?reading_date=' + day)) == 1
    request('DELETE', f'/telemetry/{device_id}/{day}/{timestamp}')
    follow = dict(user_id=user_id, target_id=target_id)
    request('POST', '/social/follow', follow)
    assert len(request('GET', '/social/' + user_id + '/following')) == 1
    request('DELETE', '/social/follow', follow)
    request('PUT', '/leaderboard/' + user_id, {'steps': 123})
    assert request('GET', '/leaderboard/' + user_id)['steps'] == 123
    request('DELETE', '/metadata/' + device_id)
    request('DELETE', '/devices/' + device_id)
    request('DELETE', '/challenges/' + challenge_id)
    request('DELETE', '/users/' + user_id)
    request('DELETE', '/users/' + target_id)
    print('LIVE CRUD PASSED', flush=True)
finally:
    # Clean only UUID-tagged records created by this run, even after a failure.
    with metadata_collection() as collection:
        collection.delete_one({'device_id': device_id})
    with session() as connection:
        connection.execute('DELETE FROM sensor_readings_by_device_day WHERE device_id=%s AND reading_date=%s',
                           (device_id, day))
    with graph_session() as graph:
        graph.run('MATCH (u:User) WHERE u.user_id IN $ids DETACH DELETE u', ids=[user_id, target_id]).consume()
    with redis_client() as connection:
        connection.zrem('pulsefit:leaderboard:steps:2026-10-11', user_id)
    with cursor() as cur:
        cur.execute('DELETE FROM devices WHERE device_id=%s', (device_id,))
        cur.execute('DELETE FROM challenges WHERE challenge_id=%s', (challenge_id,))
        cur.execute('DELETE FROM users WHERE user_id IN (%s,%s)', (user_id, target_id))
    print('Temporary records cleaned up.', flush=True)
