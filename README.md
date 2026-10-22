<<<<<<< HEAD
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
=======
# PulseFit — Code Package for All Four Members

This is an educational starter package for the four independent modules in the PulseFit case study. The modules share example IDs, but they do **not** need to connect to one another for individual screenshots.

## Modules

1. `person1_telemetry/` — Cassandra time-series sensor readings
2. `person2_users_devices/` — PostgreSQL accounts/device registration + MongoDB flexible device metadata
3. `person3_social_graph/` — Neo4j follows, friends-of-friends, mutual connections, recommendations
4. `person4_leaderboard/` — Redis sorted-set leaderboard

## Important

- These are small local demonstrations, not a simulation of PulseFit's production scale (400,000 writes/second).
- Each database service must be installed and running before its Python script can connect. You do **not** need to run all four at once.
- If your submission only needs design/code screenshots, you can show the code and schema. Do not claim a query ran successfully unless you actually ran it.
- Change default passwords in environment variables; never share your real passwords in screenshots.

## Python setup (run separately for the module you are working on)

Open a terminal in the relevant folder, then:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Use the module-specific README for database setup and run commands.

## Shared sample IDs

- Users: `U101` (Jiya), `U102` (Rahul), `U103` (Priya), `U104` (Aman)
- Devices: `PB101` (PulseBand X1), `PW501` (PulseWatch Pro)

## Suggested screenshot evidence

- Person 1: Cassandra table schema, inserted sample rows, and query output for one device/date.
- Person 2: PostgreSQL `users`/`devices` tables and MongoDB device metadata document.
- Person 3: Neo4j graph visualization and results for following/recommendation queries.
- Person 4: Redis sorted-set members/scores and output for top 3/rank.
>>>>>>> origin/main
