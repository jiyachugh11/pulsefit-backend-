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
