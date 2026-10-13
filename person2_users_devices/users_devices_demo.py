"""PostgreSQL user/device records + MongoDB flexible device metadata."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient

PG_HOST = os.getenv("PGHOST", "localhost")
PG_PORT = int(os.getenv("PGPORT", "5432"))
PG_DB = os.getenv("PGDATABASE", "pulsefit")
PG_USER = os.getenv("PGUSER", "postgres")
PG_PASSWORD = os.getenv("PGPASSWORD", "change_me")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")


def main():
    # PostgreSQL stores structured account and registration information.
    pg = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB,
                          user=PG_USER, password=PG_PASSWORD)
    mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        pg.autocommit = True
        with pg.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(20) PRIMARY KEY,
                    full_name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id VARCHAR(20) PRIMARY KEY,
                    user_id VARCHAR(20) NOT NULL REFERENCES users(user_id),
                    device_name VARCHAR(100) NOT NULL,
                    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                INSERT INTO users (user_id, full_name, email)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """, ("U101", "Jiya", "jiya@example.test"))
            cur.execute("""
                INSERT INTO devices (device_id, user_id, device_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (device_id) DO NOTHING
            """, ("PB101", "U101", "PulseBand X1"))
            cur.execute("SELECT user_id, full_name, email FROM users WHERE user_id = %s", ("U101",))
            print("PostgreSQL user:", cur.fetchone())
            cur.execute("SELECT device_id, user_id, device_name FROM devices WHERE device_id = %s", ("PB101",))
            print("PostgreSQL device:", cur.fetchone())

        # MongoDB stores optional fields that differ by device model.
        db = mongo["pulsefit"]
        profiles = db["device_metadata"]
        profiles.update_one(
            {"device_id": "PB101"},
            {"$set": {"device_id": "PB101", "model": "PulseBand X1",
                       "schema_version": 1, "sensors": ["heart_rate", "steps"],
                       "settings": {"units": "metric", "notifications": True}}},
            upsert=True,
        )
        profiles.update_one(
            {"device_id": "PW501"},
            {"$set": {"device_id": "PW501", "model": "PulseWatch Pro",
                       "schema_version": 2,
                       "sensors": ["heart_rate", "steps", "spo2", "ecg", "skin_temperature"],
                       "settings": {"units": "metric", "notifications": True},
                       "ecg_enabled": True}},
            upsert=True,
        )
        print("\nMongoDB devices with ECG:")
        for doc in profiles.find({"sensors": "ecg"}, {"_id": 0}):
            print(doc)
    finally:
        pg.close()
        mongo.close()


if __name__ == "__main__":
    main()
