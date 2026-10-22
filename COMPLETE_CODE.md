# PulseFit — complete source

Updated October 22, 2026. Local credentials are excluded. See LOCAL_SETUP.md for the connected computer and .env.example for a safe template.

## .env.example

````
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pulsefit
POSTGRES_USER=postgres
POSTGRES_PASSWORD=
# original = supplied ZIP/setup SQL; existing = local split-name/model schema
POSTGRES_LAYOUT=original
MONGO_URI=mongodb://localhost:27017/
CASSANDRA_HOST=127.0.0.1
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=
REDIS_URL=redis://localhost:6379/0
TELEMETRY_DEFAULT_DAY=2026-10-11

````

## .gitignore

````
.venv/
__pycache__/
*.pyc
.env

````

## app/__init__.py

````

````

## app/db/__init__.py

````

````

## app/db/cassandra_db.py

````
import os
from contextlib import contextmanager
from fastapi import HTTPException
from cassandra import DriverException
from cassandra.cluster import Cluster
from cassandra.io.asyncorereactor import AsyncoreConnection


@contextmanager
def session():
    cluster = None
    try:
        # Explicit portable reactor; pyasyncore supplies it on Python >= 3.12.
        cluster = Cluster([os.getenv('CASSANDRA_HOST', '127.0.0.1')],
                          connection_class=AsyncoreConnection, connect_timeout=5)
        connection = cluster.connect('pulsefit')
        connection.default_timeout = 5
        yield connection
    except (DriverException, OSError) as exc:
        raise HTTPException(503, 'Cassandra unavailable or schema missing. Check setup and .env.') from exc
    finally:
        if cluster is not None:
            cluster.shutdown()

````

## app/db/mongo.py

````
import os
from contextlib import contextmanager
from fastapi import HTTPException
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError


@contextmanager
def metadata_collection():
    client = None
    try:
        client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'),
                             serverSelectionTimeoutMS=5000, socketTimeoutMS=5000)
        yield client['pulsefit']['device_metadata']
    except DuplicateKeyError as exc:
        raise HTTPException(409, 'Metadata already exists for this device.') from exc
    except PyMongoError as exc:
        raise HTTPException(503, 'MongoDB unavailable. Check setup and .env.') from exc
    finally:
        if client is not None:
            client.close()

````

## app/db/neo4j_db.py

````
import os
from contextlib import contextmanager
from fastapi import HTTPException
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, DriverError


@contextmanager
def session():
    driver = None
    try:
        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            auth=(os.getenv('NEO4J_USER', 'neo4j'), os.getenv('NEO4J_PASSWORD', '')),
            connection_timeout=5, connection_acquisition_timeout=5,
        )
        with driver.session() as connection:
            yield connection
    except (Neo4jError, DriverError) as exc:
        raise HTTPException(503, 'Neo4j unavailable. Check setup and .env.') from exc
    finally:
        if driver is not None:
            driver.close()

````

## app/db/postgres.py

````
"""Original psycopg2 connection pattern, with transactions per request."""
import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException

# The supplied ZIP and the user's existing database use different column names.
EXISTING_LAYOUT = os.getenv('POSTGRES_LAYOUT', 'original') == 'existing'


@contextmanager
def cursor():
    connection = None
    try:
        # Also accept the PG* variables used in the supplied demo.
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', os.getenv('PGHOST', 'localhost')),
            port=os.getenv('POSTGRES_PORT', os.getenv('PGPORT', '5432')),
            dbname=os.getenv('POSTGRES_DB', os.getenv('PGDATABASE', 'pulsefit')),
            user=os.getenv('POSTGRES_USER', os.getenv('PGUSER', 'postgres')),
            password=os.getenv('POSTGRES_PASSWORD', os.getenv('PGPASSWORD', '')),
            connect_timeout=5,
        )
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
    except psycopg2.errors.ForeignKeyViolation as exc:
        raise HTTPException(409, 'Invalid user reference, or user still owns devices.') from exc
    except psycopg2.errors.UniqueViolation as exc:
        raise HTTPException(409, 'That ID or email already exists.') from exc
    except psycopg2.Error as exc:
        raise HTTPException(503, 'PostgreSQL unavailable or schema missing. Check setup and .env.') from exc
    finally:
        if connection is not None:
            connection.close()

````

## app/db/redis_db.py

````
import os
from contextlib import contextmanager
from fastapi import HTTPException
import redis


@contextmanager
def client():
    connection = None
    try:
        connection = redis.Redis.from_url(
            os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            decode_responses=True, socket_connect_timeout=5, socket_timeout=5,
        )
        yield connection
    except redis.RedisError as exc:
        raise HTTPException(503, 'Redis unavailable. Check setup and .env.') from exc
    finally:
        if connection is not None:
            connection.close()

````

## app/main.py

````
from pathlib import Path
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')

from app.routes import users, devices, challenges, metadata, telemetry, social, leaderboard

app = FastAPI(title='PulseFit', description='Five databases. One fitness application.')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
templates = Jinja2Templates(directory=ROOT / 'app' / 'templates')
for module in (users, devices, challenges, metadata, telemetry, social, leaderboard):
    app.include_router(module.router)


@app.get('/', include_in_schema=False)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name='index.html',
        context={'telemetry_day': os.getenv('TELEMETRY_DEFAULT_DAY', '2026-10-11')})

````

## app/routes/__init__.py

````

````

## app/routes/challenges.py

````
from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from app.db.postgres import cursor

router = APIRouter(prefix='/challenges', tags=['challenges'])
COLUMNS = 'challenge_id, challenge_name, start_date, end_date'


class ChallengeData(BaseModel):
    challenge_name: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date

    @model_validator(mode='after')
    def check_dates(self):
        if self.end_date < self.start_date:
            raise ValueError('End date must be on or after start date.')
        return self


class ChallengeCreate(ChallengeData):
    challenge_id: str = Field(min_length=1, max_length=20, pattern=r'^[A-Za-z0-9_-]+$')


@router.get('')
def list_challenges():
    with cursor() as cur:
        cur.execute(f'SELECT {COLUMNS} FROM challenges ORDER BY challenge_id')
        return cur.fetchall()


@router.get('/{challenge_id}')
def get_challenge(challenge_id: str):
    with cursor() as cur:
        cur.execute(f'SELECT {COLUMNS} FROM challenges WHERE challenge_id = %s', (challenge_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'Challenge not found.')
        return row


@router.post('', status_code=201)
def create_challenge(data: ChallengeCreate):
    with cursor() as cur:
        cur.execute(f'''INSERT INTO challenges (challenge_id, challenge_name, start_date, end_date)
            VALUES (%s, %s, %s, %s) RETURNING {COLUMNS}''',
            (data.challenge_id, data.challenge_name, data.start_date, data.end_date))
        return cur.fetchone()


@router.put('/{challenge_id}')
def update_challenge(challenge_id: str, data: ChallengeData):
    with cursor() as cur:
        cur.execute(f'''UPDATE challenges SET challenge_name = %s, start_date = %s, end_date = %s
            WHERE challenge_id = %s RETURNING {COLUMNS}''',
            (data.challenge_name, data.start_date, data.end_date, challenge_id))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'Challenge not found.')
        return row


@router.delete('/{challenge_id}')
def delete_challenge(challenge_id: str):
    with cursor() as cur:
        cur.execute('DELETE FROM challenges WHERE challenge_id = %s RETURNING challenge_id', (challenge_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, 'Challenge not found.')
        return {'message': 'Challenge deleted.'}


````

## app/routes/devices.py

````
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db.postgres import cursor, EXISTING_LAYOUT

router = APIRouter(prefix='/devices', tags=['devices'])
MODEL_COLUMN = 'model' if EXISTING_LAYOUT else 'device_name'
COLUMNS = f'device_id, user_id, device_type, brand, {MODEL_COLUMN} AS model, registered_at'


class DeviceData(BaseModel):
    user_id: str = Field(min_length=1, max_length=20)
    device_type: str = Field(min_length=1, max_length=50)
    brand: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)


class DeviceCreate(DeviceData):
    device_id: str = Field(min_length=1, max_length=20, pattern=r'^[A-Za-z0-9_-]+$')


@router.get('')
def list_devices():
    with cursor() as cur:
        cur.execute(f'SELECT {COLUMNS} FROM devices ORDER BY device_id')
        return cur.fetchall()


@router.get('/{device_id}')
def get_device(device_id: str):
    with cursor() as cur:
        cur.execute(f'SELECT {COLUMNS} FROM devices WHERE device_id = %s', (device_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'Device not found.')
        return row


@router.post('', status_code=201)
def create_device(data: DeviceCreate):
    with cursor() as cur:
        cur.execute(f'''INSERT INTO devices (device_id, user_id, device_type, brand, {MODEL_COLUMN})
            VALUES (%s, %s, %s, %s, %s) RETURNING {COLUMNS}''',
            (data.device_id, data.user_id, data.device_type, data.brand, data.model))
        return cur.fetchone()


@router.put('/{device_id}')
def update_device(device_id: str, data: DeviceData):
    with cursor() as cur:
        cur.execute(f'''UPDATE devices SET user_id = %s, device_type = %s, brand = %s, {MODEL_COLUMN} = %s
            WHERE device_id = %s RETURNING {COLUMNS}''',
            (data.user_id, data.device_type, data.brand, data.model, device_id))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'Device not found.')
        return row


@router.delete('/{device_id}')
def delete_device(device_id: str):
    with cursor() as cur:
        cur.execute('DELETE FROM devices WHERE device_id = %s RETURNING device_id', (device_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, 'Device not found.')
        return {'message': 'Device deleted.'}


````

## app/routes/leaderboard.py

````
from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db.redis_db import client
from app.routes.users import get_user

router = APIRouter(prefix='/leaderboard', tags=['leaderboard'])
SAMPLE_DAY = date(2026, 10, 11)


class Score(BaseModel):
    steps: int = Field(ge=0, le=2147483647)


def key(day: date):
    return f'pulsefit:leaderboard:steps:{day.isoformat()}'


@router.get('')
def leaderboard(day: date = SAMPLE_DAY):
    with client() as connection:
        rows = connection.zrevrange(key(day), 0, -1, withscores=True)
        return [{'rank': rank, 'user_id': user_id, 'steps': int(score)}
                for rank, (user_id, score) in enumerate(rows, start=1)]


@router.get('/{user_id}')
def user_rank(user_id: str, day: date = SAMPLE_DAY):
    with client() as connection:
        with connection.pipeline() as pipe:
            pipe.zrevrank(key(day), user_id)
            pipe.zscore(key(day), user_id)
            rank, score = pipe.execute()
        if rank is None:
            raise HTTPException(404, 'User has no score for this day.')
        return {'rank': rank + 1, 'user_id': user_id, 'steps': int(score)}


@router.put('/{user_id}')
def update_score(user_id: str, data: Score, day: date = SAMPLE_DAY):
    get_user(user_id)
    with client() as connection:
        with connection.pipeline() as pipe:
            pipe.zadd(key(day), {user_id: data.steps})
            pipe.zrevrank(key(day), user_id)
            _, rank = pipe.execute()
        return {'rank': rank + 1, 'user_id': user_id, 'steps': data.steps}

````

## app/routes/metadata.py

````
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.db.mongo import metadata_collection
from app.routes.devices import get_device

router = APIRouter(prefix='/metadata', tags=['metadata'])


class Metadata(BaseModel):
    # Keep model-specific fields such as PW501's ecg_enabled.
    model_config = ConfigDict(extra='allow')
    device_id: str = Field(min_length=1, max_length=20)
    model: str = Field(min_length=1, max_length=100)
    schema_version: int = Field(default=1, ge=1)
    sensors: list[str]
    settings: dict

    @model_validator(mode='after')
    def reject_internal_fields(self):
        def check(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == '_id' or key.startswith('$') or '.' in key:
                        raise ValueError('Metadata keys cannot contain dots, start with $, or use _id.')
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
        check(self.model_dump())
        return self


@router.get('/{device_id}')
def get_metadata(device_id: str):
    with metadata_collection() as collection:
        doc = collection.find_one({'device_id': device_id}, {'_id': 0})
        if doc is None:
            raise HTTPException(404, 'Device metadata not found.')
        return doc


@router.post('', status_code=201)
def create_metadata(data: Metadata):
    get_device(data.device_id)
    doc = data.model_dump()
    with metadata_collection() as collection:
        collection.insert_one(dict(doc))
    return doc


@router.put('/{device_id}')
def update_metadata(device_id: str, data: Metadata):
    if data.device_id != device_id:
        raise HTTPException(422, 'Body device_id must match the URL.')
    get_device(device_id)
    with metadata_collection() as collection:
        # Retain the supplied $set pattern, including fields not sent in this update.
        result = collection.update_one({'device_id': device_id}, {'$set': data.model_dump()})
        if result.matched_count == 0:
            raise HTTPException(404, 'Device metadata not found; create it first.')
        return collection.find_one({'device_id': device_id}, {'_id': 0})


@router.delete('/{device_id}')
def delete_metadata(device_id: str):
    with metadata_collection() as collection:
        if collection.delete_one({'device_id': device_id}).deleted_count == 0:
            raise HTTPException(404, 'Device metadata not found.')
    return {'message': 'Metadata deleted.'}

````

## app/routes/social.py

````
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from app.db.neo4j_db import session
from app.routes.users import get_user

router = APIRouter(prefix='/social', tags=['social'])


class Follow(BaseModel):
    user_id: str = Field(min_length=1, max_length=20)
    target_id: str = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def no_self_follow(self):
        if self.user_id == self.target_id:
            raise ValueError('A user cannot follow themselves.')
        return self


@router.post('/follow')
def follow(data: Follow):
    user, target = get_user(data.user_id), get_user(data.target_id)
    with session() as graph:
        graph.run('''MERGE (a:User {user_id: $user_id}) SET a.name = $name
            MERGE (b:User {user_id: $target_id}) SET b.name = $target_name
            MERGE (a)-[:FOLLOWS]->(b)''', user_id=data.user_id, target_id=data.target_id,
            name=user['full_name'], target_name=target['full_name']).consume()
    return {'message': 'Follow relationship saved.'}


@router.delete('/follow')
def unfollow(data: Follow):
    with session() as graph:
        record = graph.run('''MATCH (:User {user_id: $user_id})-[r:FOLLOWS]->(:User {user_id: $target_id})
            DELETE r RETURN count(r) AS removed''', **data.model_dump()).single()
        if not record or record['removed'] == 0:
            raise HTTPException(404, 'Follow relationship not found.')
    return {'message': 'Follow relationship removed.'}


@router.get('/{user_id}/following')
def following(user_id: str):
    get_user(user_id)
    with session() as graph:
        return graph.run('''MATCH (:User {user_id: $user_id})-[:FOLLOWS]->(person:User)
            RETURN person.user_id AS user_id, person.name AS name ORDER BY name''',
            user_id=user_id).data()


@router.get('/{user_id}/recommendations')
def recommendations(user_id: str):
    get_user(user_id)
    with session() as graph:
        return graph.run('''MATCH (me:User {user_id: $user_id})-[:FOLLOWS]->(shared:User)-[:FOLLOWS]->(candidate:User)
            WHERE candidate <> me AND NOT EXISTS { MATCH (me)-[:FOLLOWS]->(candidate) }
            RETURN candidate.user_id AS user_id, candidate.name AS name,
                   count(DISTINCT shared) AS shared_connections
            ORDER BY shared_connections DESC, user_id''', user_id=user_id).data()

````

## app/routes/telemetry.py

````
from datetime import date, datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, AwareDatetime, model_validator
from app.db.cassandra_db import session
from app.routes.devices import get_device

router = APIRouter(prefix='/telemetry', tags=['telemetry'])


class Reading(BaseModel):
    device_id: str = Field(min_length=1, max_length=20)
    reading_date: date
    reading_ts: AwareDatetime
    heart_rate: int = Field(ge=0, le=300)
    steps: int = Field(ge=0, le=2147483647)
    spo2: int = Field(ge=0, le=100)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)

    @model_validator(mode='after')
    def check_timestamp(self):
        self.reading_ts = self.reading_ts.astimezone(timezone.utc)
        if self.reading_ts.date() != self.reading_date:
            raise ValueError('reading_date must equal the UTC date of reading_ts.')
        if self.reading_ts.microsecond % 1000:
            raise ValueError('Cassandra timestamps support millisecond precision.')
        return self


@router.get('/{device_id}')
def get_readings(device_id: str, reading_date: date, limit: int = Query(200, ge=1, le=1000)):
    with session() as connection:
        rows = connection.execute('''SELECT * FROM sensor_readings_by_device_day
            WHERE device_id = %s AND reading_date = %s LIMIT %s''',
            (device_id, reading_date, limit))
        result = []
        for row in rows:
            item = dict(row._asdict())
            item['reading_date'] = str(item['reading_date'])
            item['reading_ts'] = item['reading_ts'].replace(tzinfo=timezone.utc).isoformat()
            result.append(item)
        return result


@router.post('', status_code=201)
def add_reading(data: Reading):
    get_device(data.device_id)
    with session() as connection:
        insert = connection.prepare('''INSERT INTO sensor_readings_by_device_day
            (device_id, reading_date, reading_ts, heart_rate, steps, spo2, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''')
        connection.execute(insert, (data.device_id, data.reading_date, data.reading_ts,
                                   data.heart_rate, data.steps, data.spo2, data.latitude, data.longitude))
    return data.model_dump()


@router.delete('/{device_id}/{reading_date}/{reading_ts}')
def delete_reading(device_id: str, reading_date: date, reading_ts: AwareDatetime):
    ts = reading_ts.astimezone(timezone.utc)
    if ts.date() != reading_date or ts.microsecond % 1000:
        raise HTTPException(422, 'Use the UTC date and exact millisecond timestamp returned by GET.')
    with session() as connection:
        result = connection.execute('''DELETE FROM sensor_readings_by_device_day
            WHERE device_id = %s AND reading_date = %s AND reading_ts = %s IF EXISTS''',
            (device_id, reading_date, ts))
        if not result.one().applied:
            raise HTTPException(404, 'Reading not found.')
    return {'message': 'Reading deleted.'}

````

## app/routes/users.py

````
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from app.db.postgres import cursor, EXISTING_LAYOUT

router = APIRouter(prefix='/users', tags=['users'])
COLUMNS = 'user_id, first_name, last_name, full_name, email, created_at AS joined_at'
if EXISTING_LAYOUT:
    COLUMNS = "user_id, first_name, last_name, concat_ws(' ', first_name, last_name) AS full_name, email, COALESCE(joined_at::timestamp, created_at) AS joined_at"


class UserData(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(default='', max_length=100)
    email: str = Field(max_length=255, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

    @model_validator(mode='after')
    def check_name(self):
        if not self.first_name.strip() or len((self.first_name + ' ' + self.last_name).strip()) > 100:
            raise ValueError('Full name must contain 1–100 characters.')
        return self


class UserCreate(UserData):
    user_id: str = Field(min_length=1, max_length=20, pattern=r'^[A-Za-z0-9_-]+$')


@router.get('')
def list_users():
    with cursor() as cur:
        cur.execute(f'SELECT {COLUMNS} FROM users ORDER BY user_id')
        return cur.fetchall()


@router.get('/{user_id}')
def get_user(user_id: str):
    with cursor() as cur:
        cur.execute(f'SELECT {COLUMNS} FROM users WHERE user_id = %s', (user_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'User not found.')
        return row


@router.post('', status_code=201)
def create_user(data: UserCreate):
    with cursor() as cur:
        if EXISTING_LAYOUT:
            cur.execute(f'''INSERT INTO users (user_id, first_name, last_name, email, joined_at)
                VALUES (%s, %s, %s, %s, CURRENT_DATE) RETURNING {COLUMNS}''',
                (data.user_id, data.first_name, data.last_name, data.email))
            return cur.fetchone()
        cur.execute(f'''INSERT INTO users (user_id, first_name, last_name, email, full_name)
            VALUES (%s, %s, %s, %s, %s) RETURNING {COLUMNS}''',
            (data.user_id, data.first_name, data.last_name, data.email, (data.first_name + ' ' + data.last_name).strip()))
        return cur.fetchone()


@router.put('/{user_id}')
def update_user(user_id: str, data: UserData):
    with cursor() as cur:
        if EXISTING_LAYOUT:
            cur.execute(f'''UPDATE users SET first_name = %s, last_name = %s, email = %s
                WHERE user_id = %s RETURNING {COLUMNS}''',
                (data.first_name, data.last_name, data.email, user_id))
        else:
            cur.execute(f'''UPDATE users SET first_name = %s, last_name = %s, email = %s, full_name = %s
                WHERE user_id = %s RETURNING {COLUMNS}''',
                (data.first_name, data.last_name, data.email, (data.first_name + ' ' + data.last_name).strip(), user_id))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, 'User not found.')
        return row


@router.delete('/{user_id}')
def delete_user(user_id: str):
    with cursor() as cur:
        # Some existing schemas use ON DELETE CASCADE. Keep the app's explicit
        # remove-devices-first behavior without changing the database constraint.
        cur.execute('SELECT user_id FROM users WHERE user_id = %s FOR UPDATE', (user_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, 'User not found.')
        cur.execute('SELECT device_id FROM devices WHERE user_id = %s LIMIT 1', (user_id,))
        if cur.fetchone() is not None:
            raise HTTPException(409, 'Remove this user\'s devices before deleting the user.')
        cur.execute('DELETE FROM users WHERE user_id = %s RETURNING user_id', (user_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, 'User not found.')
        return {'message': 'User deleted.'}


````

## app/templates/index.html

````
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PulseFit · Activity workspace</title>
  <link rel="stylesheet" href="{{ url_for('static', path='style.css') }}">
  <script defer src="{{ url_for('static', path='app.js') }}"></script>
</head>
<body>
<aside class="sidebar">
  <a class="brand" href="/"><span class="brand-icon">⌁</span> PulseFit<span class="brand-dot">.</span></a>
  <p class="nav-label">YOUR WORKSPACE</p>
  <nav aria-label="Dashboard sections">
    {% for id, icon, title, store in [('users','01','Users','PostgreSQL'),('devices','02','Devices','PostgreSQL'),('challenges','03','Challenges','PostgreSQL'),('metadata','04','Device metadata','MongoDB'),('telemetry','05','Telemetry','Cassandra'),('social','06','Social graph','Neo4j'),('leaderboard','07','Leaderboard','Redis')] %}
    <button type="button" class="nav-item {{ 'active' if loop.first else '' }}" data-tab="{{ id }}" aria-current="{{ 'page' if loop.first else 'false' }}"><span>{{ icon }}</span>{{ title }}</button>
    {% endfor %}
  </nav>
  <div class="sidebar-note"><span class="small-dot"></span> DATABASE CASE STUDY<p>One connected experience.<br>Five purpose-built stores.</p><a href="/docs" target="_blank" rel="noopener">Explore API docs ↗</a></div>
</aside>
<main>
  <header class="topbar"><span>Workspace <span class="slash">/</span> <strong id="breadcrumb">Users</strong></span><span class="project-tag">COLLEGE PROJECT <span>v1.0</span></span></header>
  <div class="page-content">
    <div class="page-heading"><div><p class="eyebrow">MOVE TOGETHER. BUILD BETTER.</p><h1>Your fitness, connected.</h1><p class="subtitle">Manage people, devices and activity in one place.</p></div><a class="docs-button" href="/docs" target="_blank" rel="noopener">API reference ↗</a></div>
    <div class="store-grid" aria-label="Database responsibilities">
      {% for label, description in [('PostgreSQL','People & registration'),('MongoDB','Flexible device profiles'),('Cassandra','Time-series readings'),('Neo4j','Social connections'),('Redis','Daily rankings')] %}
      <div class="store-card"><span class="store-number">0{{ loop.index }}</span><strong>{{ label }}</strong><span>{{ description }}</span></div>
      {% endfor %}
    </div>
    <div class="connection-strip"><span class="connection-label">SHARED IDENTITY</span><strong>Jiya <code>U101</code></strong><span class="arrow">→</span><strong>PulseBand X1 <code>PB101</code></strong><span class="connection-caption">The same IDs connect every store.</span></div>
    <div id="notice" role="status" aria-live="polite" hidden></div>

    {% for id, title, singular, description in [('users','Users','user','The people at the heart of PulseFit.'),('devices','Devices','device','Register wearables and connect them to their owners.'),('challenges','Challenges','challenge','Give your community a reason to keep moving.')] %}
    <section id="{{ id }}" class="panel" {{ 'hidden' if not loop.first else '' }} aria-labelledby="{{ id }}-title">
      <div class="section-heading"><div><h2 id="{{ id }}-title">{{ title }}</h2><p>{{ description }}</p></div><span class="badge">PostgreSQL</span></div>
      <div class="workspace-grid"><article class="card"><h3 id="{{ id }}-form-title">Add {{ singular }}</h3>
        <form id="{{ id }}-form" class="record-form" data-resource="{{ id }}">
        <label>{{ singular | capitalize }} ID<input name="{{ singular }}_id" placeholder="{{ {'users':'U105','devices':'PB102','challenges':'CH102'}[id] }}" maxlength="20" pattern="[A-Za-z0-9_-]+" required></label>
        {% if id == 'users' %}
          <label>First name<input name="first_name" placeholder="First name" maxlength="100" required></label>
          <label>Last name <span class="optional">optional</span><input name="last_name" placeholder="Last name" maxlength="100"></label>
          <label>Email<input name="email" type="email" placeholder="name@example.com" maxlength="255" required></label>
        {% elif id == 'devices' %}
          <label>Owner's user ID<input name="user_id" value="U101" maxlength="20" required></label>
          <label>Device type<input name="device_type" value="fitness band" maxlength="50" required></label>
          <label>Brand<input name="brand" value="PulseFit" maxlength="100" required></label>
          <label>Model<input name="model" placeholder="PulseBand X1" maxlength="100" required></label>
        {% else %}
          <label>Challenge name<input name="challenge_name" placeholder="Weekend walking challenge" maxlength="100" required></label>
          <label>Start date<input name="start_date" type="date" required></label>
          <label>End date<input name="end_date" type="date" required></label>
        {% endif %}
          <button class="primary" type="submit">Add {{ singular }}</button><button type="button" class="cancel-edit secondary" hidden>Cancel edit</button>
        </form></article>
        <article class="card list-card"><div class="card-heading"><h3>All {{ id }} <span class="count" id="{{ id }}-count">—</span></h3><button type="button" class="secondary refresh" data-resource="{{ id }}">Refresh ↻</button></div><div id="{{ id }}-table" class="table-wrap"><p class="empty">Loading records…</p></div></article>
      </div>
    </section>
    {% endfor %}

    <section id="metadata" class="panel" hidden aria-labelledby="metadata-title">
      <div class="section-heading"><div><h2 id="metadata-title">Device metadata</h2><p>Flexible profiles for the sensors and settings of each wearable.</p></div><span class="badge">MongoDB</span></div>
      <div class="workspace-grid"><article class="card"><h3>Find a device profile</h3><form id="metadata-find"><label>Device ID<input name="device_id" value="PB101" required></label><button class="primary">Load metadata</button></form><p class="helper">Create a device in PostgreSQL first. Optional fields, such as <code>ecg_enabled</code>, stay in MongoDB.</p></article>
      <article class="card"><h3>Metadata editor</h3><form id="metadata-form"><label>JSON document<textarea id="metadata-json" rows="17" spellcheck="false" required>{
  "device_id": "PB101",
  "model": "PulseBand X1",
  "schema_version": 1,
  "sensors": ["heart_rate", "steps"],
  "settings": {
    "units": "metric",
    "notifications": true
  }
}</textarea></label><div class="button-row"><button class="primary" name="action" value="POST">Create</button><button class="secondary" name="action" value="PUT">Update</button><button class="danger" name="action" value="DELETE">Delete</button></div></form><p class="helper">Update merges fields. Delete removes the entire device profile.</p></article></div>
    </section>

    <section id="telemetry" class="panel" hidden aria-labelledby="telemetry-title">
      <div class="section-heading"><div><h2 id="telemetry-title">Telemetry</h2><p>A timeline of sensor readings, grouped by device and UTC day.</p></div><span class="badge">Cassandra</span></div>
      <div class="workspace-grid"><article class="card"><h3>Add a reading</h3><form id="telemetry-form">
        <label>Device ID<input name="device_id" value="PB101" required></label>
        <label>Timestamp (UTC)<input name="reading_ts" type="datetime-local" step="1" value="{{ telemetry_day }}T10:01:00" required></label>
        <div class="form-pair"><label>Heart rate · bpm<input name="heart_rate" type="number" min="0" max="300" value="80" required></label><label>Steps<input name="steps" type="number" min="0" max="2147483647" value="160" required></label></div>
        <label>SpO₂ · %<input name="spo2" type="number" min="0" max="100" value="98" required></label>
        <div class="form-pair"><label>Latitude<input name="latitude" type="number" step="any" min="-90" max="90" value="12.9718" required></label><label>Longitude<input name="longitude" type="number" step="any" min="-180" max="180" value="80.2208" required></label></div><button class="primary">Save reading</button>
      </form><p class="helper">Saving the same device and timestamp replaces that reading, following Cassandra's upsert behavior.</p></article>
      <article class="card list-card"><h3>Device timeline</h3><form id="telemetry-find" class="inline-form"><label>Device ID<input name="device_id" value="PB101" required></label><label>UTC date<input name="reading_date" type="date" value="{{ telemetry_day }}" required></label><button class="secondary">Load readings</button></form><div id="telemetry-table" class="table-wrap"><p class="empty">Choose a device and day to view readings.</p></div><p class="helper">Shows up to 200 readings, oldest first. The API supports a limit up to 1,000.</p></article></div>
    </section>

    <section id="social" class="panel" hidden aria-labelledby="social-title">
      <div class="section-heading"><div><h2 id="social-title">Social graph</h2><p>Follow people. Discover connections through your community.</p></div><span class="badge">Neo4j</span></div>
      <div class="workspace-grid"><article class="card"><h3>Manage a connection</h3><form id="social-form"><label>User ID<input name="user_id" value="U101" required></label><label>Follow target ID<input name="target_id" value="U102" required></label><div class="button-row"><button class="primary" name="action" value="POST">Follow</button><button class="danger" name="action" value="DELETE">Unfollow</button></div></form><p class="helper">Both IDs must be registered users. A follow creates any missing graph nodes.</p></article>
      <article class="card list-card"><h3>Explore connections</h3><form id="social-find" class="inline-form"><label>User ID<input name="user_id" value="U101" required></label><button class="secondary">Explore</button></form><h4>Following</h4><div id="following-table" class="table-wrap"><p class="empty">Explore a user's connections.</p></div><h4>Recommended for you</h4><div id="recommendations-table" class="table-wrap"><p class="empty">Recommendations appear here.</p></div><p class="helper">Two hops away, excluding yourself and people already followed. Shared connections count distinct mutual follow targets.</p></article></div>
    </section>

    <section id="leaderboard" class="panel" hidden aria-labelledby="leaderboard-title">
      <div class="section-heading"><div><h2 id="leaderboard-title">Leaderboard</h2><p>Every step counts. See how the community stacks up.</p></div><span class="badge">Redis</span></div>
      <div class="workspace-grid"><article class="card"><h3>Update daily steps</h3><form id="leaderboard-form"><label>User ID<input name="user_id" value="U101" required></label><label>Day<input name="day" type="date" value="2026-10-11" required></label><label>Total steps<input name="steps" type="number" min="0" max="2147483647" value="25200" required></label><button class="primary">Update score</button></form><p class="helper">Enter a daily total. Scores are managed explicitly and are not summed from telemetry readings.</p></article>
      <article class="card list-card"><h3>Daily rankings</h3><form id="leaderboard-find" class="inline-form"><label>Day<input name="day" type="date" value="2026-10-11" required></label><button class="secondary">Load rankings</button></form><div id="leaderboard-table" class="table-wrap"><p class="empty">Choose a day to view rankings.</p></div><p class="helper">Ranks start at 1. Equal scores use Redis's reverse lexicographic user ID ordering.</p></article></div>
    </section>
    <footer><span>PulseFit / Polyglot persistence</span><span>PostgreSQL · MongoDB · Cassandra · Neo4j · Redis</span></footer>
  </div>
</main>
</body>
</html>


````

## checks/connections.py

````
"""Read-only local connectivity check; does not print passwords or change data."""
import os
import socket
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
for name, port in [('PostgreSQL', 5432), ('MongoDB', 27017), ('Cassandra', 9042), ('Neo4j', 7687), ('Redis', 6379)]:
    with socket.socket() as connection:
        connection.settimeout(2)
        reachable = connection.connect_ex(('127.0.0.1', port)) == 0
        print(f'{name} default port {port}: {"reachable" if reachable else "not reachable"}', flush=True)

try:
    from pymongo import MongoClient
    with MongoClient(os.environ['MONGO_URI'], serverSelectionTimeoutMS=3000) as client:
        client.admin.command('ping')
        print('MongoDB ping: OK')
        print('MongoDB pulsefit collections:', client['pulsefit'].list_collection_names())
except Exception as error:
    print('MongoDB check:', type(error).__name__)

try:
    from neo4j import GraphDatabase
    with GraphDatabase.driver(os.environ['NEO4J_URI'],
                              auth=(os.environ['NEO4J_USER'], os.environ['NEO4J_PASSWORD']),
                              connection_timeout=3, connection_acquisition_timeout=3) as driver:
        driver.verify_connectivity()
        print('Neo4j authentication: OK')
except Exception as error:
    print('Neo4j check:', type(error).__name__)

try:
    from cassandra.cluster import Cluster
    from cassandra.io.asyncorereactor import AsyncoreConnection
    cluster = Cluster([os.getenv('CASSANDRA_HOST', '127.0.0.1')],
                      connection_class=AsyncoreConnection, connect_timeout=3)
    try:
        session = cluster.connect()
        rows = session.execute("SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s",
                               ('pulsefit',), timeout=5)
        print('Cassandra pulsefit tables:', [row.table_name for row in rows])
    finally:
        cluster.shutdown()
except Exception as error:
    print('Cassandra check:', type(error).__name__)

````

## checks/inspect_postgres.py

````
"""Inspect column names and identifiers without modifying existing data."""
import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
connection = psycopg2.connect(host=os.environ['POSTGRES_HOST'], port=os.environ['POSTGRES_PORT'],
                              dbname=os.environ['POSTGRES_DB'], user=os.environ['POSTGRES_USER'],
                              password=os.environ['POSTGRES_PASSWORD'], connect_timeout=5)
try:
    with connection.cursor() as cur:
        cur.execute('SELECT current_database()')
        print('Connected database:', cur.fetchone()[0])
        cur.execute("SELECT table_schema, table_name, column_name, data_type FROM information_schema.columns WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY table_schema, table_name, ordinal_position")
        for row in cur.fetchall():
            print(row)
        cur.execute("SELECT table_name, column_name, is_nullable, column_default FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('users','devices','challenge','challenges') ORDER BY table_name, ordinal_position")
        print('Defaults and required columns:', cur.fetchall())
        for table in ('users', 'devices', 'challenge', 'challenges'):
            cur.execute('SELECT count(*) FROM ' + table)
            print(table, 'count:', cur.fetchone()[0])
        cur.execute('SELECT user_id, first_name, last_name FROM users ORDER BY user_id')
        print('Registered identities:', cur.fetchall())
        cur.execute('SELECT device_id, user_id, model FROM devices ORDER BY device_id')
        print('Registered devices:', cur.fetchall())
        cur.execute("SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid IN ('users'::regclass,'devices'::regclass)")
        print('Constraints:', cur.fetchall())
finally:
    connection.close()

````

## checks/live_crud.py

````
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

````

## checks/live_read.py

````
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

````

## checks/smoke.py

````
"""Small server-free checks. Run unittest discover from the project root."""
import unittest
from datetime import date
from unittest.mock import patch
import psycopg2
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.routes.telemetry import Reading


class SmokeChecks(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_dashboard_and_static_assets(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        for section in ('users', 'devices', 'challenges', 'metadata', 'telemetry', 'social', 'leaderboard'):
            self.assertIn(f'id="{section}"', response.text)
        self.assertEqual(self.client.get('/static/app.js').status_code, 200)
        self.assertEqual(self.client.get('/static/style.css').status_code, 200)

    def test_all_required_api_operations_exist(self):
        paths = self.client.get('/openapi.json').json()['paths']
        for resource, identifier in [('users', 'user_id'), ('devices', 'device_id'), ('challenges', 'challenge_id')]:
            self.assertTrue({'get', 'post'} <= paths[f'/{resource}'].keys())
            self.assertTrue({'get', 'put', 'delete'} <= paths[f'/{resource}/{{{identifier}}}'].keys())
        self.assertEqual(sum(len([m for m in methods if m in ('get', 'post', 'put', 'delete')])
                             for methods in paths.values()), 29)

    def test_validation_before_database_access(self):
        cases = [
            ('post', '/challenges', {'challenge_id': 'CH9', 'challenge_name': 'Run',
                                    'start_date': '2026-10-12', 'end_date': '2026-10-11'}),
            ('post', '/social/follow', {'user_id': 'U101', 'target_id': 'U101'}),
            ('put', '/leaderboard/U101', {'steps': -1}),
            ('post', '/users', {'user_id': 'U999', 'first_name': ' ', 'email': 'jiya@example.test'}),
            ('post', '/metadata', {'device_id': 'PB101', 'model': 'PulseBand X1',
                                   'sensors': [], 'settings': {'$bad': True}}),
        ]
        for method, path, body in cases:
            with self.subTest(path=path):
                self.assertEqual(self.client.request(method, path, json=body).status_code, 422)
        self.assertEqual(self.client.get('/telemetry/PB101').status_code, 422)

    def test_utc_partition_and_precision(self):
        data = dict(device_id='PB101', reading_date='2026-10-11',
                    reading_ts='2026-10-12T01:00:00+05:30', heart_rate=80, steps=160,
                    spo2=98, latitude=12.9718, longitude=80.2208)
        reading = Reading(**data)
        self.assertEqual(reading.reading_ts.date(), date(2026, 10, 11))
        for timestamp in ('2026-10-11T10:00:00', '2026-10-11T10:00:00.000001Z', '2026-10-12T10:00:00Z'):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValidationError):
                Reading(**{**data, 'reading_ts': timestamp})

    def test_database_errors_become_http_errors(self):
        for error, expected in [(psycopg2.OperationalError(), 503),
                                (psycopg2.errors.UniqueViolation(), 409),
                                (psycopg2.errors.ForeignKeyViolation(), 409)]:
            with patch('app.db.postgres.psycopg2.connect', side_effect=error):
                self.assertEqual(self.client.get('/users').status_code, expected)


if __name__ == '__main__':
    unittest.main()

````

## LOCAL_SETUP.md

````
# Your connected PulseFit installation

Configured and verified October 22, 2026. Passwords are only in the ignored local `.env`, never in the source listing or ZIP.

| Store | Local connection | Result |
|---|---|---|
| PostgreSQL | localhost:5432, database **PulseFit**, user postgres | Existing four users, four devices and three challenges read successfully. |
| MongoDB | localhost:27017, database pulsefit | Existing device_metadata preserved; unique device_id index added. |
| Cassandra | 127.0.0.1:9042, keyspace pulsefit | Existing sensor_readings_by_device_day works; PB101 readings are on 2026-10-21. |
| Neo4j | bolt://localhost:7687, user neo4j | Authentication, follows and recommendations verified; existing graph preserved. |
| Redis | localhost:6379, database 0, Ubuntu WSL | Installed redis-server, tested reads/writes, saved the four original daily sample scores. |

## Start it next time

1. Keep PostgreSQL and MongoDB Windows services running.
2. Start your existing Cassandra container in Docker Desktop. Its port mapping already exposes 9042 correctly; no new Docker setup was added.
3. Start the existing Neo4j instance in Neo4j Desktop.
4. Open a PowerShell terminal and run `wsl -d Ubuntu`. **Leave that Ubuntu shell open while using PulseFit.** Redis is enabled as a systemd service, but this machine stops the WSL distribution after its last interactive process exits. If necessary, run `sudo service redis-server start` inside Ubuntu; `redis-cli ping` should return PONG.
5. In another PowerShell terminal:

```powershell
cd "C:\Users\jiyab\OneDrive\Documents\ChatGPT\PulseFit\pulsefit"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 in your browser, not the HTML file directly. If an older server is already running, restart it after changing `.env`.

## Compatibility choices

`POSTGRES_LAYOUT=existing` uses your actual first_name/last_name, model and joined_at columns. A full_name value is calculated for API/social use without adding a duplicate stored name. New users receive CURRENT_DATE for joined_at. The original ZIP layout is still supported with `POSTGRES_LAYOUT=original` for fresh installations using setup/postgres.sql.

The application uses your existing plural `challenges` table (three rows). The separate singular `challenge` table and PostgreSQL `sensor_reading` table were left untouched. Telemetry APIs use Cassandra, as requested.

`TELEMETRY_DEFAULT_DAY=2026-10-21` selects your existing readings in the dashboard. The leaderboard retains the supplied October 11 sample date. No existing Cassandra readings were overwritten.

Your stores contain some independent records: MongoDB includes PW501 whereas your registered watch IDs include PW201/PW202, and Neo4j has U105–U108 beyond PostgreSQL's U101–U104. These were preserved rather than silently renamed/deleted. PB101/U101 is consistent and works across the intended demonstration. Register additional IDs in PostgreSQL before using them in new metadata, telemetry, follow, or leaderboard writes.

Live CRUD checks used unique temporary IDs and cleaned them up. All existing PostgreSQL users/devices remained unchanged. Redis scores were inserted with NX (only missing members); MongoDB gained the required unique index. Do not rerun the generic seed scripts unless you intend to restore sample values.

````

## README.md

````
# PulseFit

**Local computer setup completed October 22:** see [LOCAL_SETUP.md](LOCAL_SETUP.md) for your connected `PulseFit` database, Redis startup, and verified live checks. Do not run the original PostgreSQL setup script against your existing database; the app now supports its schema through `POSTGRES_LAYOUT=existing` in your local `.env`. The generic setup below remains for a fresh database using the supplied ZIP schema (`POSTGRES_LAYOUT=original`).

A small FastAPI + Jinja2 application demonstrating five database responsibilities through one dashboard. The supplied member implementations are retained in the parent directory. See `REUSE_NOTES.md` for the file-by-file inspection and adaptation decisions.

## Folder structure

```text
pulsefit/
  app/
    __init__.py
    main.py
    db/
      __init__.py
      postgres.py
      mongo.py
      cassandra_db.py
      neo4j_db.py
      redis_db.py
    routes/
      __init__.py
      users.py
      devices.py
      challenges.py
      metadata.py
      telemetry.py
      social.py
      leaderboard.py
    templates/index.html
  static/
    style.css
    app.js
  setup/
    postgres.sql
    sample_documents.json
    cassandra.cql
    neo4j.cypher
    seed.py
  checks/smoke.py
  .env                         # local values; not committed or included in ZIP
  .env.example
  .gitignore
  requirements.txt
  README.md
  REUSE_NOTES.md
  VERIFICATION.md
  COMPLETE_CODE.md              # full source listing for submission
```

## Install Python dependencies

Commands below use Windows PowerShell from the generated project folder. Python 3.11 or newer is required. The local verification environment uses Python 3.14. `psycopg2-binary` provides the requested `psycopg2` import. `pyasyncore` supports the Cassandra driver's explicit reactor on newer Python versions.

```powershell
cd "C:\Users\jiyab\OneDrive\Documents\ChatGPT\PulseFit\pulsefit"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

No activation command is needed. If `.env` does not already exist:

```powershell
Copy-Item .env.example .env
notepad .env
```

Enter your PostgreSQL and Neo4j passwords in `.env`. Blank passwords are placeholders, not working credentials for a typical installation. Existing process environment variables take precedence over `.env`. PostgreSQL also accepts the original `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD` variables when the corresponding `POSTGRES_*` variable is absent.

## Start and set up the databases, in this order

Install the database servers separately first; installing Python drivers does **not** install a server. Use local/class instances. On Windows, the path below uses native PostgreSQL and MongoDB services, Neo4j Desktop, and Cassandra/Redis installed in Ubuntu WSL. It requires no Docker. Server names and installation directories depend on your installed versions. Do not initialize a replacement PostgreSQL data directory if you already have one.

### 1. PostgreSQL — users and registered devices first

In an **Administrator PowerShell** window, discover the installed PostgreSQL service name:

```powershell
Get-Service -Name 'postgresql*'
```

Start the service by the exact name printed (for example, `Start-Service postgresql-x64-17`). If using a manual installation instead of a service, PostgreSQL supports `pg_ctl start -D <your-existing-data-directory>`; see [pg_ctl documentation](https://www.postgresql.org/docs/current/app-pg-ctl.html).

In ordinary PowerShell in the project folder, with PostgreSQL's `bin` directory on PATH:

```powershell
pg_isready -h localhost -p 5432
createdb -h localhost -p 5432 -U postgres pulsefit
psql -h localhost -p 5432 -U postgres -d pulsefit -v ON_ERROR_STOP=1 -f setup/postgres.sql
```

Skip `createdb` if `pulsefit` already exists. These CLI tools prompt for the password and do not read this project's `.env`. The SQL script is an additive migration plus samples. It preserves the original `full_name`, `created_at`, and `device_name` columns. It backfills first/last names and adds device type, brand, and challenges. Existing IDs are not overwritten. If an unrelated existing email conflicts with a sample, the transaction stops rather than silently changing your records.

### 2. MongoDB — metadata after device registration

For an installation registered as the standard Windows service, use Administrator PowerShell:

```powershell
Start-Service MongoDB
```

Then ordinary PowerShell in the project folder:

```powershell
.\.venv\Scripts\python.exe setup/seed.py mongo
```

The script reads the supplied JSON unchanged, creates a unique index on `device_id`, and uses the original `update_one(..., $set, upsert=True)` setup pattern. Run it before using metadata POST. Existing duplicate device IDs must be resolved before the unique index can be built. See [MongoDB Windows service documentation](https://www.mongodb.com/docs/manual/administration/run-mongodb-windows/).

### 3. Cassandra — telemetry schema and samples

Install Cassandra and its required Java runtime in Ubuntu WSL using the [Apache installation instructions](https://cassandra.apache.org/doc/stable/cassandra/installing/installing.html). For a package installation, start it and wait for readiness in a WSL terminal:

```bash
sudo service cassandra start
nodetool status
```

Wait for `UN` (Up/Normal). For a tarball installation, run `bin/cassandra -f` from that installation directory in a separate terminal instead. Then, in WSL:

```bash
cd '/mnt/c/Users/jiyab/OneDrive/Documents/ChatGPT/PulseFit/pulsefit'
cqlsh 127.0.0.1 9042 -f setup/cassandra.cql
```

The table exactly retains `PRIMARY KEY ((device_id, reading_date), reading_ts)` and ascending timestamp order. The sample measurements are copied from the original script and dated `2026-10-11` for repeatable presentation. Local Windows-to-WSL localhost forwarding must make port 9042 accessible; otherwise set `CASSANDRA_HOST` to your reachable class/local server address and configure that server's native transport appropriately.

### 4. Neo4j — nodes and follows

In Neo4j Desktop, create or select a local database, set its password, and click **Start**. Use the matching URI/password in `.env`. Then in the project PowerShell window:

```powershell
.\.venv\Scripts\python.exe setup/seed.py neo4j
```

This executes `setup/neo4j.cypher`: a unique user ID constraint, the four original nodes, and the four original follows. You can also run the statements in Neo4j Browser for a graph screenshot. Jiya follows Rahul and Priya, who each follow Aman; Jiya's recommendation is therefore Aman with **2** shared connections.

### 5. Redis — daily leaderboard

For Redis installed in Ubuntu WSL, run:

```bash
sudo service redis-server start
redis-cli ping
```

Expect `PONG`. Microsoft documents a [WSL database installation path](https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-database). Then ordinary PowerShell in the project folder:

```powershell
.\.venv\Scripts\python.exe setup/seed.py redis
```

This uses `ZADD` with the supplied initial totals: U101=25200, U102=24700, U103=23100, U104=18900. The key is `pulsefit:leaderboard:steps:2026-10-11`. For a direct CLI equivalent in WSL:

```bash
redis-cli ZADD pulsefit:leaderboard:steps:2026-10-11 25200 U101 24700 U102 23100 U103 18900 U104
redis-cli ZREVRANGE pulsefit:leaderboard:steps:2026-10-11 0 -1 WITHSCORES
```

Database engines can run independently. This setup order makes the common identifiers available before dependent records are demonstrated. Re-running MongoDB, Cassandra, Neo4j, or Redis samples restores the supplied sample fields/measurements/relationships/scores; avoid reseeding after editing data you want to keep.

## Run the application

From `pulsefit/`, after setting up the stores:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open [the dashboard](http://127.0.0.1:8000) or [interactive API documentation](http://127.0.0.1:8000/docs). Stop with Ctrl+C. The dashboard itself starts without database connections; each operation opens the relevant connection and reports a 503 if the service or schema is unavailable. No demo data is fabricated in the frontend.

## Endpoint reference

All bodies are JSON. IDs remain fixed on PUT. `joined_at` and `registered_at` are database-generated, read-only timestamps. FastAPI's `/docs` includes all request schemas. `404` means not found, `409` means a duplicate or PostgreSQL foreign-key conflict, `422` means invalid input, and `503` means a database operation failed.

| Method | Path | Behavior |
|---|---|---|
| GET | `/users` | List users ordered by user ID. |
| GET | `/users/{user_id}` | Read one user. |
| POST | `/users` | Create user: user_id, first_name, optional last_name, email. |
| PUT | `/users/{user_id}` | Replace editable name/email fields; update legacy full_name too. |
| DELETE | `/users/{user_id}` | Delete user; blocked while PostgreSQL devices reference it. |
| GET | `/devices` | List registered devices. |
| GET | `/devices/{device_id}` | Read one device. |
| POST | `/devices` | Create device: device_id, user_id, device_type, brand, model. |
| PUT | `/devices/{device_id}` | Replace user_id, device_type, brand and model. |
| DELETE | `/devices/{device_id}` | Delete registration. Other stores are separate (see below). |
| GET | `/challenges` | List challenges. |
| GET | `/challenges/{challenge_id}` | Read one challenge. |
| POST | `/challenges` | Create challenge: challenge_id, challenge_name, start_date, end_date. |
| PUT | `/challenges/{challenge_id}` | Replace name and dates. End cannot precede start. |
| DELETE | `/challenges/{challenge_id}` | Delete challenge. |
| GET | `/metadata/{device_id}` | Read the document without MongoDB's internal _id. |
| POST | `/metadata` | Create document for a registered device; duplicate ID returns 409. |
| PUT | `/metadata/{device_id}` | Merge supplied fields using $set; omitted extra fields survive. Body ID must match URL; missing document returns 404. |
| DELETE | `/metadata/{device_id}` | Delete one device profile. |
| GET | `/telemetry/{device_id}?reading_date=2026-10-11` | Read one device/day partition; optional limit=200 (maximum 1000). |
| POST | `/telemetry` | Insert/upsert one reading by its complete primary key. |
| DELETE | `/telemetry/{device_id}/{reading_date}/{reading_ts}` | Delete the exact reading; conditional delete returns 404 when absent. URL-encode the timestamp. |
| POST | `/social/follow` | Body: user_id, target_id. Verify PostgreSQL users; MERGE graph nodes and the follow relationship. Repeating is safe. |
| DELETE | `/social/follow` | Same JSON body. Remove the directed relationship or return 404. |
| GET | `/social/{user_id}/following` | Return user IDs and graph names for followed people. |
| GET | `/social/{user_id}/recommendations` | Two-hop candidates excluding self and direct follows; return shared_connections. |
| GET | `/leaderboard?day=2026-10-11` | All members ranked by descending score. |
| GET | `/leaderboard/{user_id}?day=2026-10-11` | One user's rank, user_id, steps; 404 if absent. |
| PUT | `/leaderboard/{user_id}?day=2026-10-11` | Body: steps (nonnegative integer). ZADD creates/replaces the registered user's total. |

Leaderboard day defaults to the original `2026-10-11`. Ranks are 1-based. Equal scores follow Redis's reverse lexicographic member order; ties do not share a rank.

Metadata bodies require `device_id`, `model`, `sensors`, `settings`; `schema_version` defaults to 1. Additional fields are accepted, including the original watch's `ecg_enabled`. `_id`, dotted keys, and dollar-prefixed keys are rejected.

Telemetry example:

```json
{
  "device_id": "PB101", "reading_date": "2026-10-11",
  "reading_ts": "2026-10-11T10:01:00Z",
  "heart_rate": 80, "steps": 160, "spo2": 98,
  "latitude": 12.9718, "longitude": 80.2208
}
```

Timestamps require an explicit offset. The partition date must match the timestamp's **UTC** date. Precision cannot exceed milliseconds. GET returns UTC timestamps usable in DELETE. In the dashboard, the timestamp field is explicitly interpreted as UTC.

## Consistency choices and limits

- PostgreSQL owns user/device registration. Metadata, telemetry and leaderboard writes check PostgreSQL first; follow checks both users. These checks are application-level and are not distributed transactions.
- PostgreSQL enforces the real device-to-user foreign key. Names retain the original full_name column; first_name and last_name are added for editing, created_at is exposed as joined_at, and device_name is exposed as model.
- The original SQL/schema and demonstrations still work. After inserting users through an old standalone script, rerun the additive SQL migration to backfill newly added name fields. Use the integrated app for subsequent edits so name fields remain aligned.
- Neo4j stores names as graph properties. Follow refreshes the two participants' names from PostgreSQL. Editing a PostgreSQL name alone does not update graph copies. There are no background synchronization jobs.
- Deletions are local to a store. Device/user deletion does not cascade into MongoDB, Cassandra, Neo4j, or Redis. Clean up related records first when demonstrating deletions, or retain the shared samples. Independent retention is visible and deliberate; this project does not claim cross-database atomicity. Redis has no delete endpoint because the requested scope only needs read/update.
- Original telemetry steps are sample sensor values, not a verified daily accumulator. Redis scores are explicitly entered daily totals; summing the samples would be misleading.
- Challenges demonstrate CRUD only; participation tracking was not requested. Cassandra has no artificial update endpoint, pagination framework, or ALLOW FILTERING scan.

## Small checks

The optional checks validate routing, templates, timestamps, input boundaries, and database-error mapping without requiring servers. `httpx` is only a check dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install httpx
.\.venv\Scripts\python.exe -m unittest discover -s checks -p smoke.py -v
```

See `VERIFICATION.md` for what was actually verified and a live demonstration checklist.

## Presentation explanation

“PulseFit uses polyglot persistence: each database handles a kind of data it fits well. PostgreSQL stores users, devices and challenges with keys and constraints. MongoDB keeps flexible metadata because different wearable models have different sensors. Cassandra stores time-series readings in device/day partitions. Neo4j represents follows as relationships and finds recommendations with two hops. Redis uses a sorted set to rank daily step totals.

The identifiers connect these subsystems: U101 is Jiya, and PB101 is Jiya's PulseBand X1. Its registration is in PostgreSQL, its sensors/settings are in MongoDB, and its readings are in Cassandra. Jiya's social connections are in Neo4j, and her daily score is in Redis. FastAPI exposes the queries through routers, while one Jinja2 page uses JavaScript fetch to display and edit records. We preserve the member implementations and add only the web layer, missing CRUD, and input/error handling.”

Suggested demonstration: show Jiya → PB101 → metadata → readings on October 11 → Jiya's two follows → Aman recommended with two shared connections → update U103 to 26000 steps and show the new rank. Use a new ID for CRUD deletion examples.

## Implementation references

The main source is the supplied member code. The dashboard follows FastAPI's documented [Jinja2 templating interface](https://fastapi.tiangolo.com/reference/templating/). The project uses no React, authentication, Docker, Kafka, queues, background jobs, ORM, repository/service layers, or UI frameworks.

````

## requirements.txt

````
fastapi>=0.115,<1
uvicorn>=0.30,<1
jinja2>=3.1,<4
python-dotenv>=1,<2
psycopg2-binary>=2.9,<3
pymongo>=4.6,<5
cassandra-driver>=3.29,<4
neo4j>=5.18,<7
redis>=5,<7
pyasyncore>=1,<2; python_version >= '3.12'

````

## REUSE_NOTES.md

````
# Inspection and reuse audit

All **18 files** in the supplied extracted archive `PulseFit_All_Members_Code (1)/PulseFit_All_Members/` were read before implementation. The initial progress message's count of 20 was a counting error; the inventory below is exhaustive. Original files were left unchanged.

| Original file | Database | Reused/adapted |
|---|---|---|
| README.md | All five | Shared user/device IDs; module responsibilities; truthful execution evidence. |
| requirements-all.txt | All five | Retained the five driver families and version bounds. Added only web dependencies and portable asyncore support. |
| person1_telemetry/README.md | Cassandra | Require both device_id and reading_date for reads. |
| person1_telemetry/requirements.txt | Cassandra | cassandra-driver dependency. |
| person1_telemetry/schema.cql | Cassandra | Same keyspace, table, columns, partition/clustering keys, and ASC order. |
| person1_telemetry/telemetry_demo.py | Cassandra | Cluster([HOST]), pulsefit session, prepared INSERT, partition SELECT, same three measurements. Fixed sample date replaces moving now for repeatability. |
| person2_users_devices/README.md | PostgreSQL + MongoDB | SQL owns registration; MongoDB stores flexible per-model fields; application joins by device ID. |
| person2_users_devices/requirements.txt | PostgreSQL + MongoDB | psycopg2-binary and pymongo. |
| person2_users_devices/sample_documents.json | MongoDB | Copied byte-for-byte to setup/sample_documents.json. |
| person2_users_devices/schema.sql | PostgreSQL | Original users/devices tables, lengths, unique email, FK, timestamp defaults retained. Additive columns and challenges added. |
| person2_users_devices/users_devices_demo.py | PostgreSQL + MongoDB | psycopg2 connection, parameterized SQL and conflict-safe seed INSERT; legacy PG* environment fallback; MongoClient timeout; pulsefit.device_metadata and $set update/upsert. |
| person3_social_graph/README.md | Neo4j | Four users, directed follows, graph presentation and recommendation walkthrough. |
| person3_social_graph/requirements.txt | Neo4j | neo4j driver. |
| person3_social_graph/social_demo.py | Neo4j | GraphDatabase.driver, session.run, MERGE by user_id, following and two-hop query. |
| person3_social_graph/social_graph.cypher | Neo4j | Same four edges and exclusion rules. Counts distinct intermediates as shared_connections; adds unique user ID constraint. |
| person4_leaderboard/README.md | Redis | Sorted sets, descending ranks, explicit daily totals, CLI inspection. |
| person4_leaderboard/requirements.txt | Redis | redis driver. |
| person4_leaderboard/leaderboard_demo.py | Redis | Redis.from_url(decode_responses=True), original date/key and initial scores, ZADD, ZREVRANGE, ZREVRANK, ZSCORE and 1-based ranks. U103's 26000 demonstration update is performed interactively instead of during seeding. |

## Necessary changes

- Original `full_name` and `created_at` remain. New first/last columns support unambiguous edits, with a one-time best-effort split for preexisting full names. API writes keep full_name aligned. API joined_at aliases created_at.
- Original device_name remains the stored model. New device_type and brand are additive. The supplied watch metadata had no SQL watch registration; PW501 is now registered to U102 so both sample documents pass the integration's foreign-reference check. This ownership was added, not claimed to be in the original script.
- Add challenges because the original package has no challenge implementation.
- Extend existing queries with missing CRUD, parameterized path inputs, validation and HTTP errors. Per-request context managers guarantee cleanup and transactions without a service/repository layer.
- Social POST verifies SQL users and MERGEs their nodes, so newly registered users can participate without a separate node API. Recommendations retain original logic with distinct shared-user counting.
- Redis groups the update/rank or rank/score operations in a small native pipeline to keep each result coherent.
- Preserve arbitrary metadata fields and $set semantics. Add a unique device_id index to make POST duplicate behavior reliable.
- Retain Cassandra's native upsert behavior and require the complete primary key for deletes. UTC validation avoids wrong-day partitions and lost timestamp precision.
- Samples are setup data, never an in-memory replacement for a failed database. No automatic migration or reseeding runs when the app starts.

The five original scripts were independent demonstrations. This project shares the identifiers and validates references on writes, but deliberately avoids distributed transactions or automatic cross-store cascades. See the README for the resulting lifecycle limits.

````

## setup/cassandra.cql

````
-- Original partitioned table, unchanged.
CREATE KEYSPACE IF NOT EXISTS pulsefit
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
USE pulsefit;
CREATE TABLE IF NOT EXISTS sensor_readings_by_device_day (
    device_id text,
    reading_date date,
    reading_ts timestamp,
    heart_rate int,
    steps int,
    spo2 int,
    latitude double,
    longitude double,
    PRIMARY KEY ((device_id, reading_date), reading_ts)
) WITH CLUSTERING ORDER BY (reading_ts ASC);
-- The original three readings, anchored to a reproducible demonstration date.
INSERT INTO sensor_readings_by_device_day
(device_id, reading_date, reading_ts, heart_rate, steps, spo2, latitude, longitude)
VALUES ('PB101', '2026-10-11', '2026-10-11T09:58:00Z', 78, 120, 98, 12.9716, 80.2206);
INSERT INTO sensor_readings_by_device_day
(device_id, reading_date, reading_ts, heart_rate, steps, spo2, latitude, longitude)
VALUES ('PB101', '2026-10-11', '2026-10-11T09:59:00Z', 82, 145, 97, 12.9717, 80.2207);
INSERT INTO sensor_readings_by_device_day
(device_id, reading_date, reading_ts, heart_rate, steps, spo2, latitude, longitude)
VALUES ('PB101', '2026-10-11', '2026-10-11T10:00:00Z', 80, 160, 98, 12.9718, 80.2208);

````

## setup/connect_existing.py

````
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

````

## setup/neo4j.cypher

````
CREATE CONSTRAINT pulsefit_user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE;
MERGE (u:User {user_id:'U101'}) SET u.name='Jiya';
MERGE (u:User {user_id:'U102'}) SET u.name='Rahul';
MERGE (u:User {user_id:'U103'}) SET u.name='Priya';
MERGE (u:User {user_id:'U104'}) SET u.name='Aman';
MATCH (a:User {user_id:'U101'}), (b:User {user_id:'U102'}) MERGE (a)-[:FOLLOWS]->(b);
MATCH (a:User {user_id:'U101'}), (b:User {user_id:'U103'}) MERGE (a)-[:FOLLOWS]->(b);
MATCH (a:User {user_id:'U102'}), (b:User {user_id:'U104'}) MERGE (a)-[:FOLLOWS]->(b);
MATCH (a:User {user_id:'U103'}), (b:User {user_id:'U104'}) MERGE (a)-[:FOLLOWS]->(b);

````

## setup/postgres.sql

````
-- Connect to pulsefit first. Preserve the supplied table and column names.
BEGIN;
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(20) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL REFERENCES users(user_id),
    device_name VARCHAR(100) NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Additive migration: no DROP, rename, or replacement of existing records.
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);
UPDATE users SET first_name = split_part(full_name, ' ', 1),
    last_name = CASE WHEN strpos(full_name, ' ') > 0
        THEN substr(full_name, strpos(full_name, ' ') + 1) ELSE '' END
WHERE first_name IS NULL;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_type VARCHAR(50) NOT NULL DEFAULT 'wearable';
ALTER TABLE devices ADD COLUMN IF NOT EXISTS brand VARCHAR(100) NOT NULL DEFAULT 'PulseFit';
CREATE TABLE IF NOT EXISTS challenges (
    challenge_id VARCHAR(20) PRIMARY KEY,
    challenge_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL CHECK (end_date >= start_date)
);
INSERT INTO users (user_id, full_name, first_name, last_name, email) VALUES
('U101', 'Jiya', 'Jiya', '', 'jiya@example.test'),
('U102', 'Rahul', 'Rahul', '', 'rahul@example.test'),
('U103', 'Priya', 'Priya', '', 'priya@example.test'),
('U104', 'Aman', 'Aman', '', 'aman@example.test')
ON CONFLICT (user_id) DO NOTHING;
INSERT INTO devices (device_id, user_id, device_name, device_type, brand) VALUES
('PB101', 'U101', 'PulseBand X1', 'fitness band', 'PulseFit'),
('PW501', 'U102', 'PulseWatch Pro', 'smartwatch', 'PulseFit')
ON CONFLICT (device_id) DO NOTHING;
INSERT INTO challenges VALUES ('CH101', 'October Step Challenge', '2026-10-01', '2026-10-31')
ON CONFLICT (challenge_id) DO NOTHING;
COMMIT;

````

## setup/sample_documents.json

````
[
  {
    "device_id": "PB101",
    "model": "PulseBand X1",
    "schema_version": 1,
    "sensors": ["heart_rate", "steps"],
    "settings": {"units": "metric", "notifications": true}
  },
  {
    "device_id": "PW501",
    "model": "PulseWatch Pro",
    "schema_version": 2,
    "sensors": ["heart_rate", "steps", "spo2", "ecg", "skin_temperature"],
    "settings": {"units": "metric", "notifications": true},
    "ecg_enabled": true
  }
]

````

## setup/seed.py

````
"""Run from project root: python setup/seed.py mongo|neo4j|redis.

Reads the same .env as the app. Database errors stop setup visibly.
"""
import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')


def mongo():
    from pymongo import MongoClient
    with MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'),
                     serverSelectionTimeoutMS=5000) as client:
        collection = client['pulsefit']['device_metadata']
        collection.create_index('device_id', unique=True)
        for doc in json.loads((ROOT / 'setup' / 'sample_documents.json').read_text()):
            collection.update_one({'device_id': doc['device_id']}, {'$set': doc}, upsert=True)
    print('MongoDB metadata and unique device_id index ready.')


def neo4j():
    from neo4j import GraphDatabase
    with GraphDatabase.driver(os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
                              auth=(os.getenv('NEO4J_USER', 'neo4j'),
                                    os.getenv('NEO4J_PASSWORD', ''))) as driver:
        with driver.session() as session:
            for query in (ROOT / 'setup' / 'neo4j.cypher').read_text().split(';'):
                if query.strip():
                    session.run(query).consume()
    print('Neo4j users and original four follows ready.')


def redis():
    from redis import Redis
    with Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
                        decode_responses=True) as client:
        client.zadd('pulsefit:leaderboard:steps:2026-10-11',
                    {'U101': 25200, 'U102': 24700, 'U103': 23100, 'U104': 18900})
    print('Redis leaderboard for 2026-10-11 ready.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('database', choices=['mongo', 'neo4j', 'redis'])
    args = parser.parse_args()
    {'mongo': mongo, 'neo4j': neo4j, 'redis': redis}[args.database]()

````

## static/app.js

````
'use strict';

const $ = (selector) => document.querySelector(selector);
const encode = encodeURIComponent;
const recordConfig = {
  users: {id: 'user_id', singular: 'user', columns: ['user_id', 'first_name', 'last_name', 'email', 'joined_at']},
  devices: {id: 'device_id', singular: 'device', columns: ['device_id', 'user_id', 'device_type', 'brand', 'model', 'registered_at']},
  challenges: {id: 'challenge_id', singular: 'challenge', columns: ['challenge_id', 'challenge_name', 'start_date', 'end_date']}
};

function notify(message, error = false) {
  const notice = $('#notice');
  notice.textContent = message;
  notice.className = error ? 'error' : '';
  notice.hidden = false;
}

async function api(path, method = 'GET', body) {
  let response;
  try {
    response = await fetch(path, {method, headers: {'Content-Type': 'application/json'},
      ...(body === undefined ? {} : {body: JSON.stringify(body)})});
  } catch {
    throw new Error('Cannot reach PulseFit. Check that the FastAPI server is running.');
  }
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => `${item.loc.join('.')}: ${item.msg}`).join('; ')
      : data.detail || `Request failed (${response.status}).`;
    throw new Error(detail);
  }
  return data;
}

function showTableMessage(target, message, error = false) {
  const p = document.createElement('p');
  p.className = `empty${error ? ' error-state' : ''}`;
  p.textContent = message;
  $(target).replaceChildren(p);
}

// Render database values using textContent, never HTML interpolation.
function table(target, rows, columns, actions = []) {
  if (!rows.length) {
    showTableMessage(target, 'No records found. Add a record or run the sample setup.');
    return;
  }
  const element = document.createElement('table');
  const head = element.createTHead().insertRow();
  for (const column of [...columns, ...(actions.length ? ['actions'] : [])]) {
    const th = document.createElement('th');
    th.scope = 'col';
    th.textContent = column.replaceAll('_', ' ');
    head.append(th);
  }
  const body = element.createTBody();
  for (const row of rows) {
    const tr = body.insertRow();
    for (const column of columns) {
      const value = row[column];
      tr.insertCell().textContent = value == null ? '—' : String(value);
    }
    if (actions.length) {
      const td = tr.insertCell();
      for (const action of actions) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = action.label === 'Delete' ? 'danger' : 'secondary';
        button.textContent = action.label;
        button.addEventListener('click', () => run(button, () => action.handler(row)));
        td.append(button);
      }
    }
  }
  $(target).replaceChildren(element);
}

async function run(button, task) {
  if (button) button.disabled = true;
  try { await task(); }
  catch (error) { notify(error.message, true); }
  finally { if (button) button.disabled = false; }
}

function bindForm(selector, task) {
  $(selector).addEventListener('submit', (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const action = event.submitter?.value;
    run(event.submitter, () => task(data, action));
  });
}

function resetEditor(resource) {
  const config = recordConfig[resource];
  const form = $(`#${resource}-form`);
  form.reset();
  delete form.dataset.editId;
  form.elements[config.id].readOnly = false;
  form.querySelector('.primary').textContent = `Add ${config.singular}`;
  form.querySelector('.cancel-edit').hidden = true;
  $(`#${resource}-form-title`).textContent = `Add ${config.singular}`;
}

function editRecord(resource, row) {
  const config = recordConfig[resource];
  const form = $(`#${resource}-form`);
  for (const input of form.querySelectorAll('input')) input.value = row[input.name] ?? '';
  form.dataset.editId = row[config.id];
  form.elements[config.id].readOnly = true;
  form.querySelector('.primary').textContent = 'Save changes';
  form.querySelector('.cancel-edit').hidden = false;
  $(`#${resource}-form-title`).textContent = `Edit ${config.singular}`;
  form.querySelector('input:not([readonly])').focus();
}

async function loadRecords(resource) {
  const config = recordConfig[resource];
  try {
    const rows = await api(`/${resource}`);
    $(`#${resource}-count`).textContent = rows.length;
    table(`#${resource}-table`, rows, config.columns, [
      {label: 'Edit', handler: (row) => editRecord(resource, row)},
      {label: 'Delete', handler: async (row) => {
        if (!confirm(`Delete ${row[config.id]} from ${resource}? Related data in other stores is not automatically deleted.`)) return;
        await api(`/${resource}/${encode(row[config.id])}`, 'DELETE');
        if ($(`#${resource}-form`).dataset.editId === row[config.id]) resetEditor(resource);
        notify('Record deleted.');
        await loadRecords(resource);
      }}
    ]);
  } catch (error) {
    $(`#${resource}-count`).textContent = '—';
    showTableMessage(`#${resource}-table`, error.message, true);
    throw error;
  }
}

for (const [resource, config] of Object.entries(recordConfig)) {
  bindForm(`#${resource}-form`, async (data) => {
    const editId = $(`#${resource}-form`).dataset.editId;
    if (editId) delete data[config.id];
    await api(`/${resource}${editId ? '/' + encode(editId) : ''}`, editId ? 'PUT' : 'POST', data);
    resetEditor(resource);
    notify(editId ? 'Changes saved.' : `${config.singular[0].toUpperCase() + config.singular.slice(1)} created.`);
    await loadRecords(resource);
  });
  $(`#${resource}-form .cancel-edit`).addEventListener('click', () => resetEditor(resource));
}

document.querySelectorAll('.refresh').forEach((button) => button.addEventListener('click', () =>
  run(button, () => loadRecords(button.dataset.resource))));

document.querySelectorAll('[data-tab]').forEach((button) => button.addEventListener('click', () => {
  const tab = button.dataset.tab;
  document.querySelectorAll('.panel').forEach((panel) => panel.hidden = panel.id !== tab);
  document.querySelectorAll('[data-tab]').forEach((item) => {
    item.classList.toggle('active', item === button);
    item.setAttribute('aria-current', item === button ? 'page' : 'false');
  });
  $('#breadcrumb').textContent = button.textContent.trim().replace(/^\d+/, '').trim();
  $('#notice').hidden = true;
  if (recordConfig[tab]) run(null, () => loadRecords(tab));
}));

bindForm('#metadata-find', async ({device_id}) => {
  const doc = await api(`/metadata/${encode(device_id)}`);
  $('#metadata-json').value = JSON.stringify(doc, null, 2);
  notify('Metadata loaded.');
});
bindForm('#metadata-form', async (_, method) => {
  let doc;
  try { doc = JSON.parse($('#metadata-json').value); }
  catch { throw new Error('Enter valid JSON in the metadata editor.'); }
  if (!doc || typeof doc.device_id !== 'string' || !doc.device_id.trim()) throw new Error('Include a device_id in the document.');
  if (method === 'DELETE' && !confirm(`Delete metadata for ${doc.device_id}?`)) return;
  const result = await api(`/metadata${method === 'POST' ? '' : '/' + encode(doc.device_id)}`,
    method, method === 'DELETE' ? undefined : doc);
  if (method !== 'DELETE') $('#metadata-json').value = JSON.stringify(result, null, 2);
  notify(method === 'DELETE' ? 'Metadata deleted.' : 'Metadata saved.');
});

async function loadTelemetry(data) {
  try {
    const rows = await api(`/telemetry/${encode(data.device_id)}?reading_date=${encode(data.reading_date)}`);
    table('#telemetry-table', rows, ['reading_ts', 'heart_rate', 'steps', 'spo2', 'latitude', 'longitude'], [
      {label: 'Delete', handler: async (row) => {
        if (!confirm(`Delete reading at ${row.reading_ts}?`)) return;
        await api(`/telemetry/${encode(row.device_id)}/${encode(row.reading_date)}/${encode(row.reading_ts)}`, 'DELETE');
        notify('Reading deleted.');
        await loadTelemetry(data);
      }}
    ]);
  } catch (error) { showTableMessage('#telemetry-table', error.message, true); throw error; }
}
bindForm('#telemetry-find', loadTelemetry);
bindForm('#telemetry-form', async (data) => {
  data.reading_ts = new Date(data.reading_ts + 'Z').toISOString();
  data.reading_date = data.reading_ts.slice(0, 10);
  for (const field of ['heart_rate', 'steps', 'spo2', 'latitude', 'longitude']) data[field] = Number(data[field]);
  await api('/telemetry', 'POST', data);
  $('#telemetry-find').elements.device_id.value = data.device_id;
  $('#telemetry-find').elements.reading_date.value = data.reading_date;
  notify('Reading saved.');
  await loadTelemetry(data);
});

async function loadSocial(user_id) {
  // AllSettled permits one independent query to report its result if the other fails.
  const results = await Promise.allSettled(['following', 'recommendations'].map(async (kind) => {
    try {
      const rows = await api(`/social/${encode(user_id)}/${kind}`);
      table(`#${kind}-table`, rows, ['user_id', 'name', ...(kind === 'recommendations' ? ['shared_connections'] : [])]);
    } catch (error) { showTableMessage(`#${kind}-table`, error.message, true); throw error; }
  }));
  const failure = results.find((result) => result.status === 'rejected');
  if (failure) throw failure.reason;
}
bindForm('#social-find', ({user_id}) => loadSocial(user_id));
bindForm('#social-form', async (data, method) => {
  await api('/social/follow', method, data);
  $('#social-find').elements.user_id.value = data.user_id;
  notify(method === 'POST' ? 'Follow relationship saved.' : 'Follow relationship removed.');
  await loadSocial(data.user_id);
});

async function loadLeaderboard({day}) {
  try {
    table('#leaderboard-table', await api(`/leaderboard?day=${encode(day)}`), ['rank', 'user_id', 'steps']);
  } catch (error) { showTableMessage('#leaderboard-table', error.message, true); throw error; }
}
bindForm('#leaderboard-find', loadLeaderboard);
bindForm('#leaderboard-form', async ({user_id, steps, day}) => {
  await api(`/leaderboard/${encode(user_id)}?day=${encode(day)}`, 'PUT', {steps: Number(steps)});
  $('#leaderboard-find').elements.day.value = day;
  notify('Daily score updated.');
  await loadLeaderboard({day});
});

run(null, () => loadRecords('users'));

````

## static/style.css

````
:root {
  --green:#18775a;
  --dark:#122f27;
  --ink:#243a32;
  --muted:#76847d;
  --line:#e1e7e1;
  --bg:#f5f7f3;
  --white:#fff;
  --red:#a43f37;
  font-family:Inter,'Segoe UI',Arial,sans-serif;
  color:var(--ink);
  background:var(--bg);
  font-size:14px;
}
* {
  box-sizing:border-box;
}
body {
  margin:0;
  display:flex;
  min-height:100vh;
}
button,input,textarea {
  font:inherit;
}
button,a {
  touch-action:manipulation;
}
button {
  cursor:pointer;
}
a {
  color:var(--green);
}
[hidden] {
  display:none!important;
}
.sidebar {
  width:236px;
  background:#fff;
  border-right:1px solid var(--line);
  padding:34px 22px;
  position:fixed;
  inset:0 auto 0 0;
  display:flex;
  flex-direction:column;
}
.brand {
  text-decoration:none;
  font-size:29px;
  font-weight:750;
  letter-spacing:-1.4px;
  display:flex;
  align-items:center;
  color:var(--dark);
  margin-bottom:56px;
}
.brand-icon {
  background:var(--green);
  color:#fff;
  border-radius:10px;
  font-size:35px;
  width:38px;
  height:38px;
  display:grid;
  place-items:center;
  margin-right:10px;
  line-height:1;
}
.brand-dot {
  color:#70a87b;
}
.nav-label {
  font-size:10px;
  font-weight:700;
  color:#8b978f;
  letter-spacing:1.6px;
  margin:0 12px 19px;
}
.nav-item {
  display:flex;
  align-items:center;
  width:100%;
  text-align:left;
  padding:14px 12px;
  margin:4px 0;
  background:transparent;
  border:0;
  border-radius:7px;
  color:#6c7972;
  font-weight:550;
  gap:14px;
}
.nav-item>span {
  font-size:10px;
  opacity:.65;
}
.nav-item.active {
  background:#eaf3ed;
  color:var(--green);
}
.nav-item:hover {
  background:#f0f5f0;
}
.sidebar-note {
  margin-top:auto;
  padding:24px 10px 0;
  border-top:1px solid var(--line);
  font-size:9px;
  font-weight:700;
  letter-spacing:.8px;
  color:var(--green);
}
.sidebar-note p {
  color:var(--muted);
  font-size:12px;
  font-weight:400;
  letter-spacing:0;
  line-height:1.7;
}
.sidebar-note a {
  font-size:11px;
  letter-spacing:0;
  text-decoration:none;
}
.small-dot {
  display:inline-block;
  background:#87ae7e;
  width:6px;
  height:6px;
  border-radius:50%;
  margin-right:5px;
}
main {
  margin-left:236px;
  width:calc(100% - 236px);
}
.topbar {
  height:76px;
  padding:0 42px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  background:#fff;
  border-bottom:1px solid var(--line);
  font-size:12px;
  color:var(--muted);
}
.topbar strong {
  font-weight:500;
  color:var(--ink);
}
.slash {
  margin:0 16px;
  color:#bbc3bc;
}
.project-tag {
  font-size:9px;
  letter-spacing:1.5px;
}
.project-tag span {
  margin-left:13px;
  background:#f2f5ee;
  padding:5px 8px;
  letter-spacing:0;
}
.page-content {
  max-width:1540px;
  margin:auto;
  padding:42px;
}
.page-heading {
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:30px;
}
.eyebrow {
  font-size:9px;
  letter-spacing:1.8px;
  font-weight:700;
  color:var(--green);
  margin:0 0 12px;
}
h1 {
  font-weight:600;
  letter-spacing:-1.4px;
  font-size:34px;
  margin:0 0 11px;
}
.subtitle {
  color:var(--muted);
  font-size:13px;
  margin:0;
}
.docs-button {
  border:1px solid #ced8cd;
  padding:11px 15px;
  border-radius:6px;
  color:var(--ink);
  text-decoration:none;
  font-size:11px;
  background:var(--white);
}
.store-grid {
  display:grid;
  grid-template-columns:repeat(5,1fr);
  gap:12px;
  margin-bottom:20px;
}
.store-card {
  background:#fff;
  border:1px solid var(--line);
  border-radius:9px;
  padding:17px;
  display:flex;
  flex-direction:column;
  gap:7px;
}
.store-number {
  font-size:10px;
  color:#a0afa0;
  margin-bottom:8px;
}
.store-card strong {
  font-size:13px;
  font-weight:600;
}
.store-card>span:last-child {
  font-size:10px;
  color:var(--muted);
}
.connection-strip {
  display:flex;
  align-items:center;
  gap:16px;
  background:#edf2e8;
  border:1px solid #dfe7d6;
  padding:17px 20px;
  border-radius:7px;
  margin-bottom:34px;
  font-size:11px;
}
.connection-label {
  font-size:8px;
  letter-spacing:1.3px;
  color:#73836b;
  margin-right:8px;
}
.connection-strip strong {
  font-weight:550;
}
code {
  font-family:Consolas,monospace;
  font-size:11px;
}
.connection-strip code {
  margin-left:7px;
  font-size:9px;
  color:#648169;
  background:#e0ead9;
  padding:3px 5px;
  border-radius:3px;
}
.arrow {
  color:#92a28b;
}
.connection-caption {
  margin-left:auto;
  color:#7f8d77;
  font-size:10px;
}
.section-heading {
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:23px;
}
h2 {
  font-size:23px;
  letter-spacing:-.6px;
  margin:0 0 7px;
  font-weight:600;
}
.section-heading p {
  font-size:12px;
  color:var(--muted);
  margin:0;
}
.badge {
  border:1px solid #d7e3d7;
  color:#5a785f;
  background:#edf4eb;
  border-radius:20px;
  font-size:10px;
  padding:6px 12px;
}
.workspace-grid {
  display:grid;
  grid-template-columns:280px minmax(0,1fr);
  gap:22px;
  align-items:start;
}
.card {
  background:white;
  border:1px solid var(--line);
  border-radius:9px;
  padding:24px;
  min-width:0;
}
.list-card {
  min-height:360px;
}
h3 {
  margin:0 0 22px;
  font-weight:600;
  font-size:14px;
}
h4 {
  font-size:12px;
  font-weight:600;
  margin:25px 0 12px;
}
.card-heading {
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:22px;
}
.card-heading h3 {
  margin:0;
}
.count {
  color:#788b76;
  background:#eff4eb;
  font-size:10px;
  padding:3px 7px;
  border-radius:4px;
  margin-left:5px;
}
form {
  display:flex;
  flex-direction:column;
  gap:16px;
}
label {
  font-size:11px;
  font-weight:550;
  display:flex;
  flex-direction:column;
  gap:7px;
  color:#506358;
}
input,textarea {
  width:100%;
  border:1px solid #dce3dc;
  border-radius:5px;
  padding:10px 11px;
  background:#fdfefd;
  color:var(--ink);
  outline:none;
  font-size:12px;
}
input:focus,textarea:focus {
  border-color:var(--green);
  box-shadow:0 0 0 2px #e9f2e9;
}
input:read-only {
  background:#f0f3ed;
  color:#7a887b;
}
textarea {
  resize:vertical;
  font-family:Consolas,monospace;
  line-height:1.65;
}
.optional {
  display:inline;
  color:#9aa69e;
  font-size:10px;
  font-weight:400;
}
button {
  border-radius:5px;
  padding:10px 13px;
  border:1px solid transparent;
  font-size:11px;
  font-weight:600;
}
.primary {
  background:var(--green);
  color:white;
}
.primary:hover {
  background:#105d45;
}
.secondary {
  background:#fff;
  color:#5d7163;
  border-color:var(--line);
}
.secondary:hover {
  background:#f2f6f0;
}
.danger {
  background:#fff;
  color:var(--red);
  border-color:#ecd8d4;
}
.danger:hover {
  background:#fcf0ee;
}
button:disabled {
  opacity:.5;
  cursor:wait;
}
.button-row {
  display:flex;
  gap:9px;
  flex-wrap:wrap;
}
.helper {
  font-size:11px;
  color:var(--muted);
  line-height:1.7;
  margin:19px 0 0;
}
.form-pair {
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:12px;
}
.inline-form {
  flex-direction:row;
  align-items:end;
  margin-bottom:24px;
  flex-wrap:wrap;
  gap:12px;
}
.inline-form label {
  flex:1;
  min-width:110px;
}
.table-wrap {
  overflow-x:auto;
}
.table-wrap table {
  width:100%;
  border-collapse:collapse;
  text-align:left;
  white-space:nowrap;
  font-size:11px;
}
th {
  color:#8a978e;
  font-size:9px;
  letter-spacing:.7px;
  font-weight:600;
  padding:13px 11px;
  background:#f7f9f5;
  border-top:1px solid #edf0e9;
  border-bottom:1px solid #edf0e9;
  text-transform:uppercase;
}
td {
  padding:17px 11px;
  border-bottom:1px solid #edf0e9;
  color:#596d60;
}
td:first-child {
  font-family:Consolas,monospace;
  color:var(--green);
  font-size:11px;
}
td button {
  padding:5px 8px;
  font-size:10px;
  margin-right:5px;
}
.empty {
  padding:42px 16px;
  text-align:center;
  font-size:12px;
  color:#87958a;
  line-height:1.8;
  white-space:normal;
}
.error-state {
  color:var(--red);
}
#notice {
  padding:13px 18px;
  border-radius:6px;
  font-size:12px;
  margin:0 0 22px;
  background:#e6f3e8;
  border:1px solid #bdd8c0;
}
#notice.error {
  background:#fff0ed;
  color:var(--red);
  border-color:#eec9c0;
}
footer {
  border-top:1px solid var(--line);
  margin-top:38px;
  padding-top:20px;
  display:flex;
  justify-content:space-between;
  font-size:9px;
  color:#9aa69a;
}
button:focus-visible,a:focus-visible {
  outline:2px solid var(--green);
  outline-offset:3px;
}
@media(min-width:1500px) {
  .workspace-grid {
    grid-template-columns:310px minmax(0,1fr);
  }
}
@media(max-width:1150px) {
  .sidebar {
    width:205px;
    padding:30px 16px;
  }
  main {
    margin-left:205px;
    width:calc(100% - 205px);
  }
  .page-content {
    padding:28px;
  }
  .topbar {
    padding:0 28px;
  }
  .connection-caption {
    display:none;
  }
  .workspace-grid {
    grid-template-columns:245px minmax(0,1fr);
  }
  .store-card {
    padding:12px;
  }
  .card {
    padding:18px;
  }
  .store-card>span:last-child {
    line-height:1.5;
  }
}
@media(max-width:850px) {
  body {
    display:block;
  }
  .sidebar {
    position:static;
    width:100%;
    padding:16px 20px;
  }
  .brand {
    margin-bottom:15px;
    font-size:25px;
  }
  .brand-icon {
    width:32px;
    height:32px;
  }
  .nav-label,.sidebar-note {
    display:none;
  }
  nav {
    display:flex;
    overflow-x:auto;
    gap:6px;
  }
  .nav-item {
    width:auto;
    white-space:nowrap;
    padding:10px;
    font-size:11px;
  }
  .nav-item>span {
    display:none;
  }
  main {
    margin:0;
    width:100%;
  }
  .topbar {
    height:55px;
  }
  .store-grid {
    gap:8px;
  }
  .store-card>span:last-child {
    display:none;
  }
  .store-card strong {
    font-size:11px;
  }
  .workspace-grid {
    grid-template-columns:250px minmax(0,1fr);
  }
  h1 {
    font-size:29px;
  }
  .connection-strip {
    flex-wrap:wrap;
    gap:10px;
  }
  .connection-label {
    width:100%;
  }
  .docs-button {
    display:none;
  }
}
@media(max-width:600px) {
  .page-content {
    padding:25px 16px;
  }
  .topbar {
    padding:0 18px;
  }
  .project-tag {
    display:none;
  }
  .store-grid {
    grid-template-columns:repeat(3,1fr);
  }
  .store-number {
    margin-bottom:0;
  }
  .store-card {
    gap:6px;
  }
  .workspace-grid {
    grid-template-columns:1fr;
  }
  .card {
    padding:20px;
  }
  .connection-strip {
    padding:15px;
    font-size:10px;
  }
  .connection-strip code {
    margin-left:3px;
  }
  .section-heading p {
    max-width:260px;
    line-height:1.6;
  }
  footer {
    flex-direction:column;
    gap:12px;
  }
  .inline-form button {
    align-self:end;
  }
}

````

## VERIFICATION.md

````
# Verification

## Live verification completed October 22, 2026

All five real databases connected successfully. API reads returned four PostgreSQL users, four devices, three challenges, the existing PB101 MongoDB document, and existing Neo4j relationships/recommendations. Cassandra's existing PB101 partition is dated October 21, 2026. Redis was installed in Ubuntu WSL, its connection verified, and four missing sample scores initialized without overwriting scores.

`checks/live_crud.py` passed real create/read/update/delete operations across the five stores using unique temporary IDs; temporary records were cleaned up. MongoDB duplicate creation returned 409. The existing PostgreSQL FK uses ON DELETE CASCADE, so the router now explicitly rejects user deletion while devices exist. PostgreSQL counts after cleanup remained four users, four devices, and three rows in each existing challenge table. No original schema migration or wholesale reseeding was run. The October 21 limitations below are historical and are superseded by this live verification.

## Completed on October 21, 2026

- Inspected all 18 original files before building; originals remain unchanged.
- Installed requirements successfully in the project's local virtual environment on Python 3.14.3. Driver imports work, including Cassandra with its explicit AsyncoreConnection.
- Python compilation and JavaScript syntax checks passed.
- FastAPI generated its OpenAPI schema: 16 API paths and all 29 requested HTTP operations.
- Five optional smoke checks passed: dashboard/static files, complete API operation count, validation before database access, timezone/date and millisecond rules, and PostgreSQL error-to-HTTP mapping.
- Started Uvicorn successfully and loaded the real dashboard in the in-app browser. Reviewed the responsive layout at the sidebar width, tab switching, the metadata editor, and telemetry inputs. The PostgreSQL-offline error is clearly displayed rather than replaced by fake records.
- The test environment emitted an upstream Starlette warning that its httpx-based TestClient is deprecated; the five checks still passed. This is not an application runtime error.

## Not verified against running databases

Local ports 5432 (PostgreSQL), 27017 (MongoDB), 9042 (Cassandra), 7687 (Neo4j), and 6379 (Redis) were all unreachable during verification. No database server was installed or started, no credentials were inferred, and setup scripts were not run against a live store. Live SQL/CQL/Cypher execution and successful CRUD remain unverified. The mock error checks are not evidence of live database success.

## Live acceptance checklist

After following README setup steps, use the dashboard and `/docs`:

1. Confirm U101 is Jiya, PB101 is PulseBand X1 owned by U101, and PW501 is registered to U102. Confirm the four users and one challenge appear.
2. Create U199 with a unique email; read it via GET; edit its name/email. Create PB199 owned by U199; edit its model/type/brand. Deleting U199 while PB199 exists must return 409. Delete PB199 then U199. Duplicate IDs/emails must return 409; unknown IDs must return 404.
3. Create, view, edit and delete CH199. Verify an end date before the start date returns 422.
4. Load PB101 metadata. Confirm sensors and settings match the source. Add a custom field through Update and read it back. Use a disposable registered device to check POST duplicate handling and delete its metadata before deleting its registration.
5. Query PB101 on 2026-10-11; expect the three original sensor values in timestamp order. Add a new reading at 10:01 UTC, read it, and delete exactly that row. Confirm the three original readings remain. Missing date and naive/sub-millisecond timestamps must return 422.
6. Explore U101: following U102 and U103, recommendation U104 with shared_connections=2. Follow U104 and confirm it disappears from recommendations. Unfollow U104 and confirm it reappears. Self-follow must return 422. New registered users should be able to follow without a separate graph-node setup.
7. Load the 2026-10-11 leaderboard; expect U101 first with 25200. Update U103 to 26000, verify rank 1 in both GET endpoints, then restore 23100. Try a new date and confirm it has an independent key. Negative scores must return 422.
8. Stop one database intentionally and confirm the relevant section reports 503; the page should still render. Restart it and retry. Other stores' reads should continue except social reads, which intentionally verify the source user in PostgreSQL.

Use temporary IDs for deletion checks; do not delete the shared presentation samples. The original files and source listing explain the intended queries, but successful execution should only be claimed after this live checklist passes.

````
