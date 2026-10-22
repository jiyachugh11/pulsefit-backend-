"""Small Cassandra telemetry example. Run schema.cql in cqlsh first."""
from datetime import date, datetime, timedelta, timezone
import os
from cassandra.cluster import Cluster

HOST = os.getenv("CASSANDRA_HOST", "127.0.0.1")
KEYSPACE = "pulsefit"
DEVICE_ID = "PB101"


def main():
    cluster = Cluster([HOST])
    session = cluster.connect(KEYSPACE)
    try:
        insert = session.prepare("""
            INSERT INTO sensor_readings_by_device_day
            (device_id, reading_date, reading_ts, heart_rate, steps, spo2, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        today = now.date()
        sample_rows = [
            (now - timedelta(minutes=2), 78, 120, 98, 12.9716, 80.2206),
            (now - timedelta(minutes=1), 82, 145, 97, 12.9717, 80.2207),
            (now, 80, 160, 98, 12.9718, 80.2208),
        ]
        for ts, hr, steps, spo2, lat, lon in sample_rows:
            session.execute(insert, (DEVICE_ID, today, ts, hr, steps, spo2, lat, lon))
        print(f"Inserted {len(sample_rows)} sample readings for {DEVICE_ID} on {today}.")

        print("\nReadings for one device and date:")
        rows = session.execute("""
            SELECT device_id, reading_ts, heart_rate, steps, spo2
            FROM sensor_readings_by_device_day
            WHERE device_id = %s AND reading_date = %s
        """, (DEVICE_ID, today))
        total_steps = 0
        count = 0
        for row in rows:
            print(row)
            total_steps += row.steps or 0
            count += 1
        print(f"\nDaily sample aggregate: {count} readings; sum of sample step values = {total_steps}.")
        print("Note: this is a toy aggregate over sample rows, not a production daily-step calculation.")
    finally:
        cluster.shutdown()


if __name__ == "__main__":
    main()
