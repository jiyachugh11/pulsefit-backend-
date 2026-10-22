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
