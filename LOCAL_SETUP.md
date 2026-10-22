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
