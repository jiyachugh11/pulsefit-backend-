# Person 1 — Sensor Telemetry (Cassandra)

## What this demonstrates
- A time-series table partitioned by `(device_id, reading_date)`.
- Timestamp ordering within each device/day partition.
- Insert sample readings and retrieve readings for a device/date.
- A simple aggregate over the sample records.

## Setup
1. Install/run Apache Cassandra locally, or use a class-approved Cassandra instance.
2. Install the Python dependency from this folder: `python -m pip install -r requirements.txt`.
3. Run the schema: `cqlsh -f schema.cql`.
4. Run: `python telemetry_demo.py`.

The demo uses `PB101`. Cassandra queries should include both partition-key fields (`device_id` and `reading_date`) to avoid scanning the whole table. For a time-range query, add `AND reading_ts >= ... AND reading_ts <= ...` while retaining those partition-key filters.

## Screenshot ideas
Capture `schema.cql`, then a successful terminal output after running `telemetry_demo.py`. If Cassandra is not installed, a code/schema screenshot is still a code artifact, not proof of execution.
