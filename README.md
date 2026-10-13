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
